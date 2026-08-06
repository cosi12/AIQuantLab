"""Domain exceptions for data ingestion and processing."""


class DataContractError(ValueError):
    """Raised when input cannot satisfy the canonical OHLCV contract."""


class DatasetIntegrityError(RuntimeError):
    """Raised when a persisted dataset fails an integrity check."""

