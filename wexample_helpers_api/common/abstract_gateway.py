import requests
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from wexample_helpers.const.types import StringsList
from wexample_helpers.classes.mixin.has_snake_short_class_name_class_mixin import HasSnakeShortClassNameClassMixin
from wexample_helpers.classes.mixin.has_env_keys import HasEnvKeys
from wexample_helpers.errors.gateway_error import GatewayError
from wexample_helpers.errors.gateway_connexion_error import GatewayConnectionError
from wexample_prompt.mixins.with_required_io_manager import WithRequiredIoManager
from wexample_helpers_api.enums.http import HttpMethod


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
        from wexample_helpers_api.common.http_request_payload import HttpRequestPayload

        payload = HttpRequestPayload.from_endpoint(
            self.base_url,
            endpoint,
            method,
            data,
            query_params,
            {**self.default_headers, **(headers or {})}
        )

        if not self.connected:
            self.io.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayConnectionError("Attempted request while not connected"),
            )

        self._handle_rate_limiting()

        try:
            return self.io.handle_api_response(
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
            self.io.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayError(f"Request failed: {str(e)}"),
            )
