from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from wexample_helpers_api.enums.http import HttpMethod

class HttpRequestPayload(BaseModel):
    url: str
    method: str = HttpMethod.GET
    data: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None

    @classmethod
    def from_url(cls, url: str) -> "HttpRequestPayload":
        return cls(url=url)

    @classmethod
    def from_endpoint(
        cls,
        base_url: str,
        endpoint: str,
        method: str = HttpMethod.GET,
        data: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> "HttpRequestPayload":
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return cls(
            url=url,
            method=method,
            data=data,
            query_params=query_params,
            headers=headers
        )