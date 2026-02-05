import requests
from marketplace.settings import OLLAMA_URL, OLLAMA_TIMEOUT


class OllamaConnectionError(RuntimeError):
    """Raised when Ollama is unreachable."""


def ollama_generate(
    model: str,
    prompt: str,
    options: dict | None = None,
    response_format: str | None = None,
    timeout: int | None = None,
) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    if response_format:
        payload["format"] = response_format
    try:
        r = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout if timeout is not None else OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
    except requests.ConnectionError:
        raise OllamaConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running: https://ollama.ai"
        )
    except requests.Timeout:
        raise OllamaConnectionError(
            f"Ollama request timed out after {OLLAMA_TIMEOUT}s. "
            "The model may still be loading — try again."
        )
    data = r.json()
    return data.get("response", "").strip()
