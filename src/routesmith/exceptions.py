"""Custom exceptions for routesmith."""


class RoutesmithError(Exception):
    """Base exception for routesmith."""


class HostDetectionError(RoutesmithError):
    """Raised when host detection fails critically."""


class ModelSwitchError(RoutesmithError):
    """Raised when a model switch attempt fails."""


class PlannerError(RoutesmithError):
    """Raised when the planner cannot decompose a prompt."""


class PolicyError(RoutesmithError):
    """Raised when policy resolution fails."""


class ExecutionError(RoutesmithError):
    """Raised when task execution fails."""


class ConfigurationError(RoutesmithError):
    """Raised when configuration is invalid."""


class InstallError(RoutesmithError):
    """Raised when an install operation fails."""


class ProviderError(RoutesmithError):
    """Raised when a provider operation fails."""
