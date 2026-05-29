class ExternalAccessBlockedError(RuntimeError):
    """Raised when an operation attempts to access a real external website in safe mode."""


class ConfigurationError(RuntimeError):
    """Raised when runtime configuration is invalid or incomplete."""
