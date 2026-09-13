from __future__ import annotations


class RepositoryUnavailableError(RuntimeError):
    """Raised when the API cannot use its database dependency."""


class ResourceNotFoundError(LookupError):
    """Raised when a requested domain resource does not exist."""