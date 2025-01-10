import pytest
from unittest.mock import patch, MagicMock
from requests import Response

from wexample_helpers_api.demo.demo_simple_gateway import DemoSimpleGateway
from wexample_helpers.errors.gateway_connexion_error import GatewayConnectionError
from wexample_prompt.io_manager import IoManager


@pytest.fixture
def io_manager():
    return IoManager()


@pytest.fixture
def gateway(io_manager):
    return DemoSimpleGateway(
        base_url="https://api.example.com",
        io_manager=io_manager
    )


def create_mock_response(status_code=200, json_data=None):
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    return mock_response


def test_get_expected_env_keys(gateway):
    assert gateway.get_expected_env_keys() == ["DEMO_API_KEY"]


def test_check_connection(gateway):
    assert gateway.check_connection() is True


@patch('requests.request')
def test_get_user_info(mock_request, gateway):
    # Arrange
    expected_data = {"id": 1, "name": "Test User"}
    mock_request.return_value = create_mock_response(json_data=expected_data)
    gateway.connected = True

    # Act
    result = gateway.get_user_info()

    # Assert
    assert result == expected_data
    mock_request.assert_called_once_with(
        method="GET",
        url="https://api.example.com/user",
        json=None,
        params=None,
        headers={},
        timeout=30
    )


@patch('requests.request')
def test_create_item(mock_request, gateway):
    # Arrange
    item_data = {"name": "Test Item"}
    expected_response = {"id": 1, **item_data}
    mock_request.return_value = create_mock_response(json_data=expected_response)
    gateway.connected = True

    # Act
    result = gateway.create_item(item_data)

    # Assert
    assert result == expected_response
    mock_request.assert_called_once_with(
        method="POST",
        url="https://api.example.com/items",
        json=item_data,
        params=None,
        headers={},
        timeout=30
    )


@patch('requests.request')
def test_update_item(mock_request, gateway):
    # Arrange
    item_id = "123"
    item_data = {"name": "Updated Item"}
    expected_response = {"id": item_id, **item_data}
    mock_request.return_value = create_mock_response(json_data=expected_response)
    gateway.connected = True

    # Act
    result = gateway.update_item(item_id, item_data)

    # Assert
    assert result == expected_response
    mock_request.assert_called_once_with(
        method="PUT",
        url=f"https://api.example.com/items/{item_id}",
        json=item_data,
        params=None,
        headers={},
        timeout=30
    )


@patch('requests.request')
def test_delete_item(mock_request, gateway):
    # Arrange
    item_id = "123"
    mock_request.return_value = create_mock_response()
    gateway.connected = True

    # Act
    gateway.delete_item(item_id)

    # Assert
    mock_request.assert_called_once_with(
        method="DELETE",
        url=f"https://api.example.com/items/{item_id}",
        json=None,
        params=None,
        headers={},
        timeout=30
    )


def test_not_connected_error(gateway):
    # Arrange
    gateway.connected = False

    # Act & Assert
    with pytest.raises(GatewayConnectionError):
        gateway.get_user_info()