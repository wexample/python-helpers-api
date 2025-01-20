from wexample_helpers.errors.gateway_error import GatewayError


class GatewayAuthenticationError(GatewayError):
    """Raised when authentication to the API fails."""
    pass