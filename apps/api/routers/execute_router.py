"""
/execute, /execute/stream, /execute/workflow routes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db, scoped_client_id
from apps.api.services import log_message
from apps.api import workflow_store
from fastapi import HTTPException
from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.core.models import (
    ExecuteRequest,
    ExecuteResponse,
    Provenance,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStepResult,
)
from marketplace.core.validate import validate_output
from marketplace.settings import EXECUTOR_TIMEOUT
from marketplace.storage.models import AppListing
from marketplace.storage.runs import Run
from marketplace.storage.users import UsageRecord, User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["execute"])


@router.post("/execute", response_model=ExecuteResponse)
async def execute(
    req: ExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
) -> ExecuteResponse:
    t0 = perf_counter()
    now = datetime.now(timezone.utc).isoformat()
    scoped_id = scoped_client_id(req.client_id, current_user)

    app_ids_to_try = [req.app_id] + list(req.fallback_app_ids or [])
    last_errors: list[str] = []
    require_citations = True

    def _log_run(app_id: str, ok: bool, payload, errors: list, req_cit: bool) -> int:
        latency_ms = int((perf_counter() - t0) * 1000)
        run = Run(
            app_id=app_id,
            task=req.task,
            client_id=scoped_id,
            require_citations=req_cit,
            ok=ok,
            output_json=json.dumps(payload) if payload is not None else None,
            validation_errors_json=json.dumps(errors),
            latency_ms=latency_ms,
            created_at=now,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id

    for attempt_app_id in app_ids_to_try:
        app_row = db.get(AppListing, attempt_app_id)
        if not app_row:
            last_errors = [f"Unknown app_id: {attempt_app_id}"]
            continue

        require_citations = bool(req.require_citations and app_row.citations_supported)

        if app_row.executor_type != "http_api":
            last_errors = ["Unsupported executor_type"]
            continue

        if not app_row.executor_url:
            last_errors = ["Missing executor_url"]
            continue

        final_inputs = req.inputs.copy() if req.inputs else {}
        logger.info("Execute %s: inputs=%s, task='%s'", attempt_app_id, final_inputs, req.task)

        if not final_inputs and req.task:
            try:
                from marketplace.core.llm import extract_parameters_from_task
                meta = json.loads(app_row.extra_metadata or "{}")
                input_schema = meta.get("input_schema")
                extracted = extract_parameters_from_task(
                    req.task, attempt_app_id, app_row.executor_url, input_schema=input_schema,
                )
                if extracted:
                    final_inputs.update(extracted)
            except Exception as e:
                logger.warning("Parameter extraction failed for %s: %s", attempt_app_id, e, exc_info=True)

        meta = json.loads(app_row.extra_metadata or "{}")
        http_method = meta.get("http_method", "GET")

        try:
            from marketplace.core.executor import execute_http
            payload = await execute_http(
                app_row.executor_url, method=http_method, params=final_inputs, timeout=EXECUTOR_TIMEOUT,
            )
        except Exception as e:
            last_errors = [f"Execution failed: {e}"]
            logger.warning("Provider %s failed: %s; trying next fallback", attempt_app_id, e)
            continue

        val_errors = validate_output(payload, require_citations=require_citations)
        if val_errors:
            run_id = _log_run(attempt_app_id, False, payload, val_errors, require_citations)
            return ExecuteResponse(
                app_id=attempt_app_id, ok=False, output=payload,
                provenance=None, validation_errors=val_errors, run_id=run_id,
            )

        prov = Provenance(
            sources=payload.get("citations", []) if isinstance(payload, dict) else [],
            retrieved_at=payload.get("retrieved_at", "") if isinstance(payload, dict) else "",
            notes=[],
        )
        run_id = _log_run(attempt_app_id, True, payload, [], require_citations)

        if current_user.id > 0:
            usage = UsageRecord(
                user_id=current_user.id, endpoint="/execute", method="POST",
                cost_usd=app_row.cost_est_usd,
            )
            db.add(usage)
            db.commit()

        if scoped_id and isinstance(payload, dict):
            log_message(db, scoped_id, "provider", json.dumps(payload, ensure_ascii=True))
        return ExecuteResponse(
            app_id=attempt_app_id, ok=True, output=payload,
            provenance=prov, validation_errors=[], run_id=run_id,
        )

    run_id = _log_run(req.app_id, False, None, last_errors, require_citations)
    if current_user.id > 0:
        usage = UsageRecord(
            user_id=current_user.id, endpoint="/execute", method="POST", cost_usd=0.0,
        )
        db.add(usage)
        db.commit()
    return ExecuteResponse(
        app_id=req.app_id, ok=False, validation_errors=last_errors, run_id=run_id,
    )


@router.post("/execute/stream")
async def execute_stream(
    req: ExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
):
    async def event_stream():
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        yield sse("started", {"app_id": req.app_id, "task": req.task})

        app_row = db.get(AppListing, req.app_id)
        if not app_row:
            yield sse("error", {"error": f"Unknown app_id: {req.app_id}"})
            return

        final_inputs = req.inputs.copy() if req.inputs else {}

        if not final_inputs and req.task:
            yield sse("extracting_params", {"app_id": req.app_id})
            try:
                from marketplace.core.llm import extract_parameters_from_task
                meta = json.loads(app_row.extra_metadata or "{}")
                extracted = extract_parameters_from_task(
                    req.task, req.app_id, app_row.executor_url,
                    input_schema=meta.get("input_schema"),
                )
                if extracted:
                    final_inputs.update(extracted)
                    yield sse("params_extracted", {"params": extracted})
            except Exception as e:
                yield sse("warning", {"message": f"Parameter extraction failed: {e}"})

        yield sse("executing", {"app_id": req.app_id, "inputs": final_inputs})

        try:
            from marketplace.core.executor import execute_http
            meta = json.loads(app_row.extra_metadata or "{}")
            payload = await execute_http(
                app_row.executor_url,
                method=meta.get("http_method", "GET"),
                params=final_inputs,
                timeout=EXECUTOR_TIMEOUT,
            )
            yield sse("result", {"app_id": req.app_id, "ok": True, "output": payload})
        except Exception as e:
            yield sse("error", {"app_id": req.app_id, "error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/execute/workflow", response_model=WorkflowResponse)
async def execute_workflow(
    req: WorkflowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
) -> WorkflowResponse:
    """
    Execute a multi-step workflow. Each step can reference prior step outputs
    via {step_key.field} placeholders in its inputs dict values.
    """

    def _resolve_inputs(inputs: dict, step_outputs: dict) -> dict:
        resolved = {}
        for k, v in inputs.items():
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                ref = v[1:-1]
                parts = ref.split(".", 1)
                step_key = parts[0]
                field = parts[1] if len(parts) > 1 else None
                src = step_outputs.get(step_key, {})
                resolved[k] = src.get(field, v) if field else src
            else:
                resolved[k] = v
        return resolved

    step_outputs: dict = {}
    results: list[WorkflowStepResult] = []

    for i, step in enumerate(req.steps):
        step_key = step.output_key or f"step_{i}"
        final_inputs = _resolve_inputs(step.inputs, step_outputs)

        app_row = db.get(AppListing, step.app_id)
        if not app_row:
            results.append(WorkflowStepResult(
                step=i, app_id=step.app_id, ok=False, error=f"Unknown app_id: {step.app_id}",
            ))
            return WorkflowResponse(ok=False, steps=results)

        if not app_row.executor_url:
            results.append(WorkflowStepResult(
                step=i, app_id=step.app_id, ok=False, error="Missing executor_url",
            ))
            return WorkflowResponse(ok=False, steps=results)

        if not final_inputs and step.task:
            try:
                from marketplace.core.llm import extract_parameters_from_task
                meta = json.loads(app_row.extra_metadata or "{}")
                extracted = extract_parameters_from_task(
                    step.task, step.app_id, app_row.executor_url,
                    input_schema=meta.get("input_schema"),
                )
                if extracted:
                    final_inputs.update(extracted)
            except Exception:
                pass

        try:
            from marketplace.core.executor import execute_http
            meta = json.loads(app_row.extra_metadata or "{}")
            payload = await execute_http(
                app_row.executor_url,
                method=meta.get("http_method", "GET"),
                params=final_inputs,
                timeout=EXECUTOR_TIMEOUT,
            )
            out = payload if isinstance(payload, dict) else {"result": payload}
            step_outputs[step_key] = out
            results.append(WorkflowStepResult(step=i, app_id=step.app_id, ok=True, output=out))
        except Exception as e:
            results.append(WorkflowStepResult(step=i, app_id=step.app_id, ok=False, error=str(e)))
            return WorkflowResponse(ok=False, steps=results)

    last_key = req.steps[-1].output_key or f"step_{len(req.steps) - 1}"
    return WorkflowResponse(ok=True, steps=results, final_output=step_outputs.get(last_key))


# ---- Durable workflow launch + status polling -------------------------------


async def _run_workflow_background(workflow_id: str, req_dict: dict) -> None:
    """Execute a workflow in the background and persist status in workflow_store."""
    import asyncio

    from apps.api.dependencies import get_db as _get_db

    workflow_store.update(workflow_id, {"status": "running"})

    req = WorkflowRequest(**req_dict)
    db = next(_get_db())
    try:
        # Reuse the synchronous workflow handler by calling its loop directly.
        # We can't call the FastAPI route function (it expects Depends-resolved
        # args); instead replicate the small loop here against the same code path.
        step_outputs: dict = {}
        results: list[WorkflowStepResult] = []
        ok = True

        for i, step in enumerate(req.steps):
            step_key = step.output_key or f"step_{i}"
            workflow_store.update(workflow_id, {"current_step": i, "current_app_id": step.app_id})
            app_row = db.get(AppListing, step.app_id)
            if not app_row or not app_row.executor_url:
                err = "Unknown app_id" if not app_row else "Missing executor_url"
                results.append(WorkflowStepResult(step=i, app_id=step.app_id, ok=False, error=err))
                ok = False
                break

            final_inputs = step.inputs.copy() if step.inputs else {}
            try:
                from marketplace.core.executor import execute_http
                meta = json.loads(app_row.extra_metadata or "{}")
                payload = await execute_http(
                    app_row.executor_url,
                    method=meta.get("http_method", "GET"),
                    params=final_inputs,
                    timeout=EXECUTOR_TIMEOUT,
                )
                out = payload if isinstance(payload, dict) else {"result": payload}
                step_outputs[step_key] = out
                results.append(WorkflowStepResult(step=i, app_id=step.app_id, ok=True, output=out))
            except Exception as e:
                results.append(WorkflowStepResult(step=i, app_id=step.app_id, ok=False, error=str(e)))
                ok = False
                break

        last_key = req.steps[-1].output_key or f"step_{len(req.steps) - 1}"
        workflow_store.update(
            workflow_id,
            {
                "status": "completed" if ok else "failed",
                "ok": ok,
                "steps": [r.model_dump() for r in results],
                "final_output": step_outputs.get(last_key) if ok else None,
                "current_step": None,
                "current_app_id": None,
            },
        )
    except asyncio.CancelledError:  # pragma: no cover - shutdown path
        workflow_store.update(workflow_id, {"status": "cancelled"})
        raise
    except Exception as e:
        workflow_store.update(workflow_id, {"status": "failed", "error": str(e)})
    finally:
        db.close()


@router.post("/execute/workflow/async", status_code=202)
async def launch_workflow_async(
    req: WorkflowRequest,
    current_user: User = Depends(check_user_rate_limit),
):
    """Launch a workflow in the background. Returns a workflow_id for polling."""
    import asyncio

    workflow_id = workflow_store.new_workflow_id()
    workflow_store.create(workflow_id, {
        "id": workflow_id,
        "status": "queued",
        "step_count": len(req.steps),
        "current_step": None,
        "current_app_id": None,
        "owner_id": current_user.id if current_user else None,
    })

    # Schedule on the running event loop so it survives the request lifetime.
    asyncio.create_task(_run_workflow_background(workflow_id, req.model_dump()))
    return {"workflow_id": workflow_id, "status": "queued"}


@router.get("/workflows/{workflow_id}")
def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(check_user_rate_limit),
):
    state = workflow_store.get(workflow_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Workflow not found or expired")
    return state
