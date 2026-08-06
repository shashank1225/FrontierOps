class ServiceNowError(Exception):
    """Base error for recoverable ServiceNow integration failures."""


class ServiceNowConfigurationError(ServiceNowError):
    """Raised when ServiceNow is enabled without valid credentials."""


class ServiceNowRequestError(ServiceNowError):
    """Raised when the ServiceNow Table API cannot create an incident."""


class ServiceNowResponseError(ServiceNowError):
    """Raised when ServiceNow returns an invalid response payload."""
