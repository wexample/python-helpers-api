from typing import Optional, Dict, Any, List, Union, TypeVar, Generic

from pydantic import BaseModel

from wexample_helpers_api.enums.http import HttpMethod


class HttpRequestPayload(BaseModel):
    url: str
    method: HttpMethod = HttpMethod.GET
    data: Optional[Union[Dict[str, Any], bytes]] = None
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
            base_url: Optional[str],
            endpoint: str,
            method: HttpMethod = HttpMethod.GET,
            data: Optional[Union[Dict[str, Any], bytes]] = None,
            query_params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            call_origin: Optional[str] = None,
            expected_status_codes: Optional[Union[int, List[int]]] = None
    ) -> "HttpRequestPayload":
        if base_url:
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        else:
            url = endpoint

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
