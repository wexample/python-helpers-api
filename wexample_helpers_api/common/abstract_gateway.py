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
        self.io_manager.info(f"Attempting connection to {self.base_url}")
        if self.check_connection():
            self.connected = True
            self.io_manager.success(f"Successfully connected to {self.base_url}")
            return True

        self.io_manager.error(f"Failed to connect to {self.base_url}")
        raise GatewayConnectionError("Failed to connect to the API")

    def check_connection(self) -> bool:
        try:
            return self._check_url(self.base_url)
        except Exception as e:
            self.io_manager.error(f"Connection check failed: {str(e)}")
            return False

    def get_expected_env_keys(self) -> StringsList:
        return []

    def _check_url(self, url: str) -> bool:
        try:
            self.io_manager.debug(f"Checking URL: {url}")
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self.default_headers
            )
            status = response.status_code == 200
            
            # Use the new api_response method
            error_response = self.io_manager.api_response(response)
            if error_response:
                return False
                
            return status
        except requests.exceptions.RequestException as e:
            self.io_manager.error(f"URL check failed with exception: {str(e)}")
            return False

    def _handle_rate_limiting(self):
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        if not self.connected:
            self.io_manager.error(f"Attempted request while not connected")
            raise GatewayConnectionError("Gateway is not connected")

        self._handle_rate_limiting()

        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        request_headers = {**self.default_headers, **(headers or {})}

        try:
            self.io_manager.debug(f"Making {method} request to {full_url}")
            if data:
                self.io_manager.debug(f"Request data: {data}")
            if params:
                self.io_manager.debug(f"Request params: {params}")
                
            response = requests.request(
                method=method,
                url=full_url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            
            # Use the new api_response method to handle errors
            error_response = self.io_manager.api_response(response, context={
                "method": method,
                "endpoint": endpoint,
                "data": data,
                "params": params
            })
            
            if error_response:
                raise GatewayError(f"Request failed with status {response.status_code}")
                
            self.io_manager.debug(f"Request successful with status {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            self.io_manager.error(f"Request failed with exception: {str(e)}")
            raise GatewayError(f"Request failed: {str(e)}")
