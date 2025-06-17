import time
from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING, Mapping

import requests
from pydantic import BaseModel, Field

from wexample_helpers.classes.mixin.has_env_keys import HasEnvKeys
from wexample_helpers.classes.mixin.has_snake_short_class_name_class_mixin import HasSnakeShortClassNameClassMixin
from wexample_helpers.classes.mixin.has_two_steps_init import HasTwoStepInit
from wexample_helpers.const.types import StringsList
from wexample_helpers.errors.gateway_error import GatewayError
from wexample_helpers.helpers.cli import cli_make_clickable_path
from wexample_helpers_api.common.http_request_payload import HttpRequestPayload
from wexample_helpers_api.enums.http import HttpMethod, ContentType, Header
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
        return "GatewayService"

    def get_base_url(self) -> Optional[str]:
        return self.base_url

    def connect(self) -> bool:
        self.connected = True
        return True

    def check_connexion(self) -> bool:
        return self.connected

    def check_status_code(self, expected_status_codes: Union[int, List[int]] = 200) -> bool:
        return self.make_request(
            endpoint="",
            expected_status_codes=expected_status_codes,
            quiet=True
        ) is not None

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
        message = f"HTTP {response.status_code}"
        try:
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message", data.get("error", message))
        except (ValueError, AttributeError):
            if response.text:
                message = response.text
        return message

    def _create_request_details(
            self,
            request_context: HttpRequestPayload,
            status_code: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create request details dictionary for logging."""
        details: Dict[str, Any] = {
            "URL": request_context.url,
            "Method": request_context.method,
        }
        if request_context.call_origin:
            details["Call Origin"] = cli_make_clickable_path(request_context.call_origin)
        if request_context.data:
            if isinstance(request_context.data, bytes):
                details["Data"] = f"<Binary data: {len(request_context.data)} bytes>"
            else:
                details["Data"] = request_context.data
        if request_context.query_params:
            details["Query Parameters"] = request_context.query_params
        if status_code is not None:
            details["Status"] = status_code
        return details

    def format_response_content(self, response: Optional[requests.Response]) -> str:
        """Extract and format response content for logging."""
        if response is None:
            return "Null response"
        
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response.text

    def _get_header_value(
            self,
            headers: Optional[Mapping[str, str]],
            name: Header,
    ) -> Optional[str]:
        """
        Case-insensitive lookup of a header followed by normalisation:
        - keep only the part before the first ';'
        - trim whitespace
        - convert to lower-case
        """
        if not headers:
            return None
        raw = next(
            (v for k, v in headers.items() if k.lower() == name.value.lower()),
            None,
        )
        if raw is None:
            return None

        return raw.split(";", 1)[0].strip().lower() or None

    def make_request(
            self,
            endpoint: str,
            method: HttpMethod = HttpMethod.GET,
            data: Optional[Union[Dict[str, Any], bytes]] = None,
            query_params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            files: Optional[Union[Dict[str, Any], List[tuple]]] = None,
            call_origin: Optional[str] = None,
            expected_status_codes: Optional[Union[int, List[int]]] = None,
            fatal_if_unexpected: bool = False,
            quiet: bool = False,
            stream: bool = False,
            timeout: Optional[int] = None
    ) -> Optional[requests.Response]:
        payload = HttpRequestPayload.from_endpoint(
            base_url=self.get_base_url(),
            endpoint=endpoint,
            method=method,
            data=data,
            query_params=query_params,
            headers={**self.default_headers, **(headers or {})},
            call_origin=call_origin,
            expected_status_codes=expected_status_codes,
        )

        if not self.connected:
            self.connect()

        self._handle_rate_limiting()

        # Determine how to send the data based on Content-Type header
        content_type = self._get_header_value(payload.headers, Header.CONTENT_TYPE)

        if files:
            content_type = ContentType.MULTIPART.value
            payload.headers.pop(Header.CONTENT_TYPE.value, None)

        if payload.data is not None:
            if isinstance(payload.data, bytes):
                self.io.log(f"Sending binary payload ({len(payload.data)} bytes)")
            else:
                self.io.log(f"Sending {type(payload.data).__name__} payload")

        request_kwargs: Dict[str, Any] = {
            "method": payload.method.value,
            "url": payload.url,
            "params": payload.query_params,
            "headers": payload.headers,
            "timeout": timeout or self.timeout,
            "stream": stream,
        }

        if files:
            request_kwargs["data"] = data or {}
            request_kwargs["files"] = files
        elif content_type in (ContentType.FORM_URLENCODED.value, ContentType.OCTET_STREAM.value):
            request_kwargs["data"] = data
        else:
            request_kwargs["json"] = data

        try:
            response = requests.request(**request_kwargs)
        except requests.exceptions.RequestException as exc:
            return self.handle_api_response(
                response=None,
                request_context=payload,
                exception=GatewayError(f"Request failed: {exc}"),
                fatal_on_error=fatal_if_unexpected,
                quiet=quiet,
            )

        expected = {expected_status_codes} if isinstance(expected_status_codes, int) else set(
            expected_status_codes or {200})
        exception = None
        if response.status_code not in expected:
            exception = GatewayError(self._extract_error_message(response))

        return self.handle_api_response(
            response=response,
            request_context=payload,
            exception=exception,
            fatal_on_error=fatal_if_unexpected,
            quiet=quiet,
        )

    def handle_api_response(
            self,
            response: Optional[requests.Response],
            request_context: HttpRequestPayload,
            exception: Optional[Exception] = None,
            fatal_on_error: bool = False,
            quiet: Optional[bool] = None,
    ) -> Optional[requests.Response]:
        is_quiet = self.quiet if quiet is None else quiet

        if response is None:
            if not is_quiet:
                self.io.properties(
                    self._create_request_details(request_context),
                    title="Request Details"
                )
            if exception:
                self.io.error(str(exception), exception=exception, fatal=fatal_on_error)
            return None

        if not is_quiet:
            self.io.debug(f"{request_context.method} {request_context.url} -> {response.status_code}")

        if response.status_code in request_context.expected_status_codes:
            return response

        # Combine request details with response content
        details = {
            **self._create_request_details(request_context, response.status_code),
            "Response Content": self.format_response_content(response),
        }

        if not is_quiet:
            self.io.properties(details, title="Request Details")

        self.io.error(
            message=str(exception) if exception else self._extract_error_message(response),
            exception=exception,
            fatal=fatal_on_error,
        )
        return response
