"""Domain exceptions for causal feature materialization."""


class FeatureContractError(ValueError):
    """Raised when feature input or output violates a declared contract."""


class FeatureRegistryError(RuntimeError):
    """Raised when a feature is missing or conflicts with a registered definition."""


class FeatureIntegrityError(RuntimeError):
    """Raised when materialized feature artifacts fail integrity verification."""

