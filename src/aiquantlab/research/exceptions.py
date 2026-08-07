"""Domain exceptions for research experiments."""


class ResearchContractError(ValueError):
    """Raised when an experiment input violates a research contract."""


class RegistryConflictError(RuntimeError):
    """Raised when a registry identity is reused with different content."""


class RegistryStateError(RuntimeError):
    """Raised when a registry lifecycle transition is invalid."""

