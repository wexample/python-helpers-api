from typing import Optional, Dict, Any, List, Union

from pydantic import BaseModel

from wexample_helpers_api.enums.http import HttpMethod


class HttpRequestPayload(BaseModel):
    url: str
    method: HttpMethod = HttpMethod.GET
    data: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    call_origin: Optional[str] = None
    expected_status_codes: List[int] = [200]

    @classmethod
    def from_url(cls, url: str, call_origin: Optional[str] = None) -> "HttpRequestPayload":
        return cls(url=url, call_origin=call_origin)

    @classmethod
    def from_endpoint(
        cls,
        base_url: str,
        endpoint: str,
        method: HttpMethod = HttpMethod.GET,
        data: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        call_origin: Optional[str] = None,
        expected_status_codes: Optional[Union[int, List[int]]] = None
    ) -> "HttpRequestPayload":
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        if isinstance(expected_status_codes, int):
            expected_status_codes = [expected_status_codes]
        elif expected_status_codes is None:
            expected_status_codes = [200]

        return cls(
            url=url,
            method=method,
            data=data,
            query_params=query_params,
            headers=headers,
            call_origin=call_origin,
            expected_status_codes=expected_status_codes
        )
