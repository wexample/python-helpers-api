from typing import Dict, Any, Optional

from wexample_helpers_api.common.abstract_gateway import AbstractGateway
from wexample_helpers.const.types import StringsList
from wexample_helpers_api.enums.http import HttpMethod


class DemoSimpleGateway(AbstractGateway):
    """A simple implementation of AbstractGateway for demonstration purposes."""
    
    def get_expected_env_keys(self) -> StringsList:
        return ["DEMO_API_KEY"]

    def check_connection(self) -> bool:
        # Always return True for demo purposes
        return True

    def get_user_info(self) -> Dict[str, Any]:
        """Demo method to get user information."""
        response = self.make_request(
            method=HttpMethod.GET,
            endpoint="/user",
            call_origin=__file__
        )
        return response.json()

    def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Demo method to create an item."""
        response = self.make_request(
            method=HttpMethod.POST,
            endpoint="/items",
            data=item_data,
            call_origin=__file__
        )
        return response.json()

    def update_item(self, item_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Demo method to update an item."""
        response = self.make_request(
            method=HttpMethod.PUT,
            endpoint=f"/items/{item_id}",
            data=item_data,
            call_origin=__file__
        )
        return response.json()

    def delete_item(self, item_id: str) -> None:
        """Demo method to delete an item."""
        self.make_request(
            method=HttpMethod.DELETE,
            endpoint=f"/items/{item_id}",
            call_origin=__file__
        )
