"""
Main client for Axiomeer API
"""

import os
import requests
from typing import List, Dict, Any, Optional
from axiomeer.models import ShopResult, ExecutionResult, AppListing
from axiomeer.exceptions import (
    AxiomeerError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ExecutionError,
    ValidationError,
)


class AgentMarketplace:
    """
    Main client for interacting with the Axiomeer AI Agent Marketplace.

    Usage:
        >>> marketplace = AgentMarketplace(api_key="axm_xxx")
        >>> result = marketplace.shop("I need to send SMS")
        >>> execution = result.execute(marketplace, to="+1234567890", message="Hello!")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the Axiomeer client.

        Args:
            api_key: Axiomeer API key (or set AXIOMEER_API_KEY env var)
            base_url: Base URL for API (or set AXIOMEER_BASE_URL env var)
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key or os.getenv("AXIOMEER_API_KEY")
        self.base_url = (base_url or os.getenv("AXIOMEER_BASE_URL") or "http://localhost:8000").rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise AxiomeerError(
                "API key required. Pass api_key parameter or set AXIOMEER_API_KEY environment variable."
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions"""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key. Please check your credentials.")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(retry_after=retry_after)
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {response.json().get('detail', 'Unknown')}")
        elif response.status_code == 422:
            raise ValidationError(f"Validation error: {response.json().get('detail', 'Invalid request')}")
        else:
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = response.text or "Unknown error"
            raise AxiomeerError(f"API error ({response.status_code}): {error_detail}")

    def shop(
        self,
        task: str,
        required_capabilities: Optional[List[str]] = None,
        excluded_providers: Optional[List[str]] = None,
        max_cost_usd: Optional[float] = None
    ) -> ShopResult:
        """
        Shop for a tool/API/dataset that can handle your task.

        Args:
            task: Natural language description of what you need
            required_capabilities: List of required capabilities (e.g., ["sms", "international"])
            excluded_providers: List of provider IDs to exclude
            max_cost_usd: Maximum cost per request in USD

        Returns:
            ShopResult with selected tool and alternatives

        Example:
            >>> result = marketplace.shop("I need to send SMS messages")
            >>> print(result.selected_app.name)
            "Twilio SMS API"
        """
        url = f"{self.base_url}/shop"
        payload = {
            "task": task,
            "required_capabilities": required_capabilities or [],
            "excluded_providers": excluded_providers or [],
        }
        if max_cost_usd is not None:
            payload["max_cost_usd"] = max_cost_usd

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            data = self._handle_response(response)

            # Parse response from actual API format
            recommendations = data.get("recommendations", [])

            if not recommendations:
                raise NotFoundError("No tools found matching your criteria")

            # First recommendation is the selected app
            selected = recommendations[0]
            app = AppListing(
                app_id=selected.get("app_id", ""),
                name=selected.get("name", ""),
                description=selected.get("name", ""),  # API doesn't return description in recommendations
                provider="",  # API doesn't return provider in recommendations
                capabilities=[],  # API doesn't return capabilities in recommendations
                trust_card=None,
                category=None,
                uptime=None,
            )

            # Remaining recommendations are alternatives
            alternatives = []
            for alt in recommendations[1:6]:  # Top 5 alternatives
                alternatives.append(AppListing(
                    app_id=alt.get("app_id", ""),
                    name=alt.get("name", ""),
                    description=alt.get("name", ""),
                    provider="",
                    capabilities=[],
                ))

            # Get reasoning and confidence from selected recommendation
            reasoning = selected.get("rationale", "")
            confidence = selected.get("score", 0.0)

            return ShopResult(
                selected_app=app,
                reasoning=reasoning,
                confidence=confidence,
                alternatives=alternatives,
            )
        except requests.exceptions.Timeout:
            raise AxiomeerError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise AxiomeerError(f"Could not connect to Axiomeer API at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise AxiomeerError(f"Request failed: {str(e)}")

    def execute(
        self,
        app_id: str,
        params: Optional[Dict[str, Any]] = None,
        task: str = ""
    ) -> ExecutionResult:
        """
        Execute a tool with given parameters.

        Args:
            app_id: Application/tool ID to execute
            params: Tool-specific parameters
            task: Task description (optional)

        Returns:
            ExecutionResult with execution outcome

        Example:
            >>> result = marketplace.execute(
            ...     app_id="twilio-sms",
            ...     params={"to": "+1234567890", "message": "Hello!"}
            ... )
            >>> print(result.result)
        """
        url = f"{self.base_url}/execute"
        payload = {
            "app_id": app_id,
            "task": task or f"Execute {app_id}",
            "inputs": params or {},
            "require_citations": False,  # Don't require citations from all tools
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            data = self._handle_response(response)

            # Parse actual API response format
            success = data.get("ok", False)
            output = data.get("output", {})
            validation_errors = data.get("validation_errors", [])

            # Extract error message if present
            error_msg = None
            if not success:
                if validation_errors:
                    error_msg = "; ".join(validation_errors)
                else:
                    error_msg = "Execution failed"

            # If execution failed, raise an error
            if not success and error_msg:
                raise ExecutionError(f"Tool execution failed: {error_msg}", details=data)

            return ExecutionResult(
                success=success,
                result=output,
                app_id=app_id,
                execution_time_ms=None,  # API doesn't return this
                cost_usd=None,  # API doesn't return this
                error=error_msg,
            )
        except requests.exceptions.Timeout:
            raise AxiomeerError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise AxiomeerError(f"Could not connect to Axiomeer API at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise AxiomeerError(f"Request failed: {str(e)}")

    def list_apps(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[AppListing]:
        """
        List available applications in the marketplace.

        Args:
            category: Filter by category (e.g., "communication", "weather", "data")
            search: Search query
            limit: Maximum number of results

        Returns:
            List of AppListing objects

        Example:
            >>> apps = marketplace.list_apps(category="weather")
            >>> for app in apps:
            ...     print(f"{app.name}: {app.description}")
        """
        url = f"{self.base_url}/apps"
        params = {"limit": limit}
        if category:
            params["category"] = category
        if search:
            params["search"] = search

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            data = self._handle_response(response)

            # Handle both list and dict responses
            if isinstance(data, list):
                items = data
            else:
                items = data.get("apps", [])

            apps = []
            for item in items:
                apps.append(AppListing(
                    app_id=item.get("id", item.get("app_id", "")),
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    provider=item.get("provider", ""),
                    capabilities=item.get("capabilities", []),
                    trust_card=item.get("trust_card"),
                    category=item.get("category"),
                    uptime=item.get("uptime"),
                ))
            return apps
        except requests.exceptions.Timeout:
            raise AxiomeerError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise AxiomeerError(f"Could not connect to Axiomeer API at {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise AxiomeerError(f"Request failed: {str(e)}")

    def health(self) -> Dict[str, Any]:
        """
        Check API health status.

        Returns:
            Health check response with status and metrics
        """
        url = f"{self.base_url}/health"
        try:
            response = requests.get(url, timeout=self.timeout)
            return response.json()
        except requests.exceptions.RequestException as e:
            raise AxiomeerError(f"Health check failed: {str(e)}")
