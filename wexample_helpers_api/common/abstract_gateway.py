from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING

import requests
import time
from pydantic import BaseModel, Field

from wexample_helpers.classes.mixin.has_env_keys import HasEnvKeys
from wexample_helpers.classes.mixin.has_snake_short_class_name_class_mixin import HasSnakeShortClassNameClassMixin
from wexample_helpers.classes.mixin.has_two_steps_init import HasTwoStepInit
from wexample_helpers.const.types import StringsList
from wexample_helpers.errors.gateway_error import GatewayError
from wexample_helpers.helpers.cli import cli_make_clickable_path
from wexample_helpers_api.common.http_request_payload import HttpRequestPayload
from wexample_helpers_api.enums.http import HttpMethod
from wexample_prompt.mixins.with_required_io_manager import WithRequiredIoManager

if TYPE_CHECKING:
    pass


class AbstractGateway(
    HasSnakeShortClassNameClassMixin,
    WithRequiredIoManager,
    HasEnvKeys,
    HasTwoStepInit,
    BaseModel
):
    # Base configuration
    base_url: Optional[str] = Field(default=None, description="Base API URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    quiet: bool = Field(default=False, description="If True, only show errors and warnings")

    # State
    connected: bool = Field(default=False, description="Connection state")
    last_request_time: Optional[float] = Field(default=None, description="Timestamp of last request")
    rate_limit_delay: float = Field(default=1.0, description="Minimum delay between requests in seconds")

    # Default request configuration
    default_headers: Dict[str, str] = Field(default=None, description="Default headers for requests")

    def __init__(self, io_manager: "Any", **kwargs):
        BaseModel.__init__(self, **kwargs)
        HasEnvKeys.__init__(self)
        WithRequiredIoManager.__init__(self, io=io_manager)

    def setup(self) -> "AbstractGateway":
        self._validate_env_keys()

        if self.default_headers is None:
            self.default_headers = {}

        return self

    @classmethod
    def get_class_name_suffix(cls) -> Optional[str]:
        return 'GatewayService'

    def get_base_url(self) -> Optional[str]:
        return self.base_url

    def connect(self) -> bool:
        self.connected = True
        return True

    def check_connexion(self) -> bool:
        return self.connected

    def check_status_code(self, expected_status_codes: Union[int, List[int]] = 200) -> bool:
        # 421 is the default code from the root api.
        return self.make_request(
            endpoint='',
            expected_status_codes=expected_status_codes,
            quiet=True
        ).status_code in ([expected_status_codes] if isinstance(expected_status_codes, int) else expected_status_codes)

    def get_expected_env_keys(self) -> StringsList:
        return []

    def _handle_rate_limiting(self):
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract error message from response."""
        error_msg = f"HTTP {response.status_code}"
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error_msg = error_data.get("message", error_data.get("error", error_msg))
        except (ValueError, AttributeError):
            if response.text:
                error_msg = response.text
        return error_msg

    def _create_request_details(self, request_context: HttpRequestPayload, status_code: Optional[int] = None) -> Dict[
        str, Any]:
        """Create request details dictionary for logging."""
        details = {
            "URL": request_context.url,
            "Method": request_context.method
        }
        if request_context.call_origin:
            details["Call Origin"] = cli_make_clickable_path(request_context.call_origin)
        if request_context.data:
            details["Data"] = request_context.data
        if request_context.query_params:
            details["Query Parameters"] = request_context.query_params
        if status_code is not None:
            details["Status"] = status_code
        return details

    def _get_response_content(self, response: requests.Response) -> Dict[str, Any]:
        """Extract and format response content for logging."""
        try:
            return {"Response Content": response.json()}
        except (ValueError, AttributeError):
            if response.text:
                return {"Response Content": response.text}
            return {"Response Content": "No content"}

    def make_request(
            self,
            endpoint: str,
            method: HttpMethod = HttpMethod.GET,
            data: Optional[Dict[str, Any]] = None,
            query_params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            call_origin: Optional[str] = None,
            expected_status_codes: Optional[Union[int, List[int]]] = None,
            fatal_if_unexpected: bool = False,
            quiet: Optional[bool] = None
    ) -> requests.Response:
        payload = HttpRequestPayload.from_endpoint(
            self.get_base_url(),
            endpoint,
            method,
            data,
            query_params,
            {**self.default_headers, **(headers or {})},
            call_origin=call_origin,
            expected_status_codes=expected_status_codes
        )

        if not self.connected:
            self.connect()

        self._handle_rate_limiting()

        try:
            response = requests.request(
                method=payload.method.value,
                url=payload.url,
                json=payload.data,
                params=payload.query_params,
                headers=payload.headers,
                timeout=self.timeout
            )

            exception = None
            if response.status_code not in payload.expected_status_codes:
                exception = GatewayError(self._extract_error_message(response))

            return self.handle_api_response(
                response=response,
                request_context=payload,
                exception=exception,
                fatal_on_error=fatal_if_unexpected,
                quiet=quiet
            )

        except requests.exceptions.RequestException as e:
            return self.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayError(f"Request failed: {str(e)}"),
                fatal_on_error=fatal_if_unexpected,
                quiet=quiet
            )

    def handle_api_response(
            self,
            response: Optional[requests.Response],
            request_context: HttpRequestPayload,
            exception: Optional[Exception] = None,
            fatal_on_error: bool = False,
            quiet: Optional[bool] = None
    ) -> Union[requests.Response, None]:
        # Use request-specific quiet setting if provided, otherwise use class setting
        is_quiet = self.quiet if quiet is None else quiet

        if response is None:
            if not is_quiet:
                self.io.properties(
                    self._create_request_details(request_context),
                    title="Request Details"
                )
            if exception:
                self.io.error(
                    f"Request failed: {str(exception)}",
                    exception=exception,
                    fatal=fatal_on_error
                )
            return None

        if not is_quiet:
            self.io.debug(
                f"{request_context.method} {request_context.url} "
                f"-> Status: {response.status_code}"
            )

        if response.status_code in request_context.expected_status_codes:
            return response

        # Combine request details with response content
        request_details = {
            **self._create_request_details(request_context, response.status_code),
            **self._get_response_content(response)
        }

        if not is_quiet:
            self.io.properties(
                request_details,
                title="Request Details"
            )

        self.io.error(
            message=str(exception) if exception else self._extract_error_message(response),
            exception=exception,
            fatal=fatal_on_error
        )

        return None
