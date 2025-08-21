"""Tests for HttpRequestPayload class."""

import unittest

from wexample_helpers_api.common.http_request_payload import HttpRequestPayload
from wexample_helpers_api.enums.http import HttpMethod


class TestHttpRequestPayload(unittest.TestCase):
    """Test cases for HttpRequestPayload class."""

    def test_from_url(self) -> None:
        """Test creating HttpRequestPayload from URL."""
        url = "https://api.example.com/endpoint"
        payload = HttpRequestPayload.from_url(url)

        self.assertEqual(payload.url, url)
        self.assertEqual(payload.method, HttpMethod.GET)
        self.assertIsNone(payload.data)
        self.assertIsNone(payload.query_params)
        self.assertIsNone(payload.headers)

    def test_from_endpoint_basic(self) -> None:
        """Test creating HttpRequestPayload from endpoint with basic parameters."""
        base_url = "https://api.example.com"
        endpoint = "/users"
        payload = HttpRequestPayload.from_endpoint(base_url, endpoint)

        self.assertEqual(payload.url, "https://api.example.com/users")
        self.assertEqual(payload.method, HttpMethod.GET)
        self.assertIsNone(payload.data)
        self.assertIsNone(payload.query_params)
        self.assertIsNone(payload.headers)

    def test_from_endpoint_with_trailing_slash(self) -> None:
        """Test creating HttpRequestPayload with trailing slash in base_url."""
        base_url = "https://api.example.com/"
        endpoint = "/users"
        payload = HttpRequestPayload.from_endpoint(base_url, endpoint)

        self.assertEqual(payload.url, "https://api.example.com/users")

    def test_from_endpoint_without_leading_slash(self) -> None:
        """Test creating HttpRequestPayload without leading slash in endpoint."""
        base_url = "https://api.example.com"
        endpoint = "users"
        payload = HttpRequestPayload.from_endpoint(base_url, endpoint)

        self.assertEqual(payload.url, "https://api.example.com/users")

    def test_from_endpoint_with_all_parameters(self) -> None:
        """Test creating HttpRequestPayload with all optional parameters."""
        base_url = "https://api.example.com"
        endpoint = "/users"
        method = HttpMethod.POST
        data = {"name": "John", "age": 30}
        query_params = {"filter": "active"}
        headers = {"Authorization": "Bearer token"}

        payload = HttpRequestPayload.from_endpoint(
            base_url=base_url,
            endpoint=endpoint,
            method=method,
            data=data,
            query_params=query_params,
            headers=headers,
        )

        self.assertEqual(payload.url, "https://api.example.com/users")
        self.assertEqual(payload.method, HttpMethod.POST)
        self.assertEqual(payload.data, data)
        self.assertEqual(payload.query_params, query_params)
        self.assertEqual(payload.headers, headers)

    def test_direct_instantiation(self) -> None:
        """Test direct instantiation of HttpRequestPayload."""
        url = "https://api.example.com/endpoint"
        method = HttpMethod.PUT
        data = {"status": "active"}
        query_params = {"version": "2"}
        headers = {"Content-Type": "application/json"}

        payload = HttpRequestPayload(
            url=url,
            method=method,
            data=data,
            query_params=query_params,
            headers=headers,
        )

        self.assertEqual(payload.url, url)
        self.assertEqual(payload.method, method)
        self.assertEqual(payload.data, data)
        self.assertEqual(payload.query_params, query_params)
        self.assertEqual(payload.headers, headers)
