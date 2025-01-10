import requests
import time
import logging
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
        logging.info(f"[{self.__class__.__name__}] Attempting connection to {self.base_url}")
        if self.check_connection():
            self.connected = True
            logging.info(f"[{self.__class__.__name__}] Successfully connected to {self.base_url}")
            return True

        logging.error(f"[{self.__class__.__name__}] Failed to connect to {self.base_url}")
        raise GatewayConnectionError("Failed to connect to the API")

    def check_connection(self) -> bool:
        try:
            return self._check_url(self.base_url)
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Connection check failed: {str(e)}")
            return False

    def get_expected_env_keys(self) -> StringsList:
        return []

    def _check_url(self, url: str) -> bool:
        try:
            logging.debug(f"[{self.__class__.__name__}] Checking URL: {url}")
            response = requests.get(
                url,
                timeout=self.timeout,
                headers=self.default_headers
            )
            status = response.status_code == 200
            if not status:
                logging.warning(f"[{self.__class__.__name__}] URL check failed with status code {response.status_code}: {response.text}")
            return status
        except requests.exceptions.RequestException as e:
            logging.error(f"[{self.__class__.__name__}] URL check failed with exception: {str(e)}")
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
            logging.error(f"[{self.__class__.__name__}] Attempted request while not connected")
            raise GatewayConnectionError("Gateway is not connected")

        self._handle_rate_limiting()

        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        request_headers = {**self.default_headers, **(headers or {})}

        try:
            logging.debug(f"[{self.__class__.__name__}] Making {method} request to {full_url}")
            if data:
                logging.debug(f"[{self.__class__.__name__}] Request data: {data}")
            if params:
                logging.debug(f"[{self.__class__.__name__}] Request params: {params}")
                
            response = requests.request(
                method=method,
                url=full_url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                logging.error(f"[{self.__class__.__name__}] Request failed with status {response.status_code}: {response.text}")
            else:
                logging.debug(f"[{self.__class__.__name__}] Request successful with status {response.status_code}")
                
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"[{self.__class__.__name__}] Request failed with exception: {str(e)}")
            raise GatewayError(f"Request failed: {str(e)}")
