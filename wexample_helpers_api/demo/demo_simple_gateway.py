from typing import Dict, Any, Optional

from wexample_helpers_api.common.abstract_gateway import AbstractGateway
from wexample_helpers.const.types import StringsList


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
            method="GET",
            endpoint="/user",
        )
        return response.json()

    def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Demo method to create an item."""
        response = self.make_request(
            method="POST",
            endpoint="/items",
            data=item_data
        )
        return response.json()

    def update_item(self, item_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Demo method to update an item."""
        response = self.make_request(
            method="PUT",
            endpoint=f"/items/{item_id}",
            data=item_data
        )
        return response.json()

    def delete_item(self, item_id: str) -> None:
        """Demo method to delete an item."""
        self.make_request(
            method="DELETE",
            endpoint=f"/items/{item_id}"
        )
