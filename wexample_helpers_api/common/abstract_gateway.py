import requests
import time
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from wexample_helpers.const.types import StringsList
from wexample_helpers.classes.mixin.has_snake_short_class_name_class_mixin import HasSnakeShortClassNameClassMixin
from wexample_helpers.classes.mixin.has_env_keys import HasEnvKeys
from wexample_helpers.errors.gateway_error import GatewayError
from wexample_helpers.errors.gateway_connexion_error import GatewayConnectionError
from wexample_prompt.mixins.with_required_io_manager import WithRequiredIoManager
from wexample_helpers_api.enums.http import HttpMethod
from wexample_helpers_api.common.http_request_payload import HttpRequestPayload
from wexample_prompt.responses.properties_prompt_response import PropertiesPromptResponse


class AbstractGateway(HasSnakeShortClassNameClassMixin, WithRequiredIoManager, HasEnvKeys, BaseModel):
    # Base configuration
    base_url: str = Field(..., description="Base API URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # State
    connected: bool = Field(default=False, description="Connection state")
    last_request_time: Optional[float] = Field(default=None, description="Timestamp of last request")
    rate_limit_delay: float = Field(default=1.0, description="Minimum delay between requests in seconds")

    # Default request configuration
    default_headers: Dict[str, str] = Field(default=None, description="Default headers for requests")

    def model_post_init(self, *args, **kwargs):
        super().model_post_init(*args, **kwargs)
        if self.default_headers is None:
            self.default_headers = {}

    @classmethod
    def get_class_name_suffix(cls) -> Optional[str]:
        return 'GatewayService'

    def connect(self) -> bool:
        self.connected = True
        return True

    def check_connection(self) -> requests.Response:
        return self.make_request(
            endpoint=self.base_url
        )

    def get_expected_env_keys(self) -> StringsList:
        return []

    def _handle_rate_limiting(self):
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def make_request(
        self,
        endpoint: str,
        method: str = HttpMethod.GET,
        data: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        payload = HttpRequestPayload.from_endpoint(
            self.base_url,
            endpoint,
            method,
            data,
            query_params,
            {**self.default_headers, **(headers or {})}
        )

        if not self.connected:
            return self.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayConnectionError("Attempted request while not connected"),
            )

        self._handle_rate_limiting()

        try:
            return self.handle_api_response(
                response=requests.request(
                    method=payload.method,
                    url=payload.url,
                    json=payload.data,
                    params=payload.query_params,
                    headers=payload.headers,
                    timeout=self.timeout
                ),
                request_context=payload
            )

        except requests.exceptions.RequestException as e:
            return self.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayError(f"Request failed: {str(e)}"),
            )

    def handle_api_response(
        self,
        response: Optional[requests.Response],
        request_context: HttpRequestPayload,
        exception: Optional[Exception] = None,
    ) -> Union[requests.Response, None]:
        # Format request details for logging
        request_details = {
            "URL": request_context.url,
            "Method": request_context.method
        }
        if request_context.data:
            request_details["Data"] = request_context.data
        if request_context.query_params:
            request_details["Query Parameters"] = request_context.query_params

        # Handle only when response is set to None.
        if response is None:
            self.io.print_response(PropertiesPromptResponse.create(
                request_details,
                title="Request Details"
            ))

            if exception:
                self.io.error(f"Request failed: {str(exception)}", exception=exception)
            return None

        # Log request details at debug level
        self.io.debug(
            f"{request_context.method} {request_context.url} "
            f"-> Status: {response.status_code}"
        )

        # Handle response based on status code
        if 200 <= response.status_code < 300:
            return response
        
        # Handle error response
        error_msg = f"HTTP {response.status_code}"
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error_msg = error_data.get("message", error_data.get("error", error_msg))
        except (ValueError, AttributeError):
            if response.text:
                error_msg = response.text

        # Add response status to request details
        request_details["Status"] = response.status_code

        self.io.print_response(PropertiesPromptResponse.create(
            request_details,
            title="Request Details"
        ))

        self.io.error(error_msg)
        return None
