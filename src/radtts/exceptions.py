"""Custom exceptions for clearer failure handling."""


class RADTTSError(Exception):
    """Base error class."""


class ValidationError(RADTTSError):
    """Input validation error."""


class StageTimeoutError(RADTTSError):
    """A stage exceeded its timeout."""


class StageRetryExceededError(RADTTSError):
    """A stage failed after all retries."""


class JobCancelledError(RADTTSError):
    """A user cancelled the active job."""


class DependencyMissingError(RADTTSError):
    """Optional runtime dependency is missing."""
