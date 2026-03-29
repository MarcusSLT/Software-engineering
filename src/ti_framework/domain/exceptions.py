"""Domain and application-level exceptions for the TI framework."""


class ScrapperError(Exception):
    """Base exception for the data collection subsystem."""


class SourceValidationError(ScrapperError):
    """Raised when a source declaration is invalid."""


class SnapshotValidationError(ScrapperError):
    """Raised when a snapshot is invalid."""


class FetchError(ScrapperError):
    """Raised when fetching data from a source fails."""


class SnapshotStorageError(ScrapperError):
    """Raised when a snapshot cannot be persisted or restored."""


class SnapshotNotFoundError(SnapshotStorageError):
    """Raised when a snapshot handle points to a missing object."""


class PreprocessingError(ScrapperError):
    """Raised when preprocessing of a snapshot fails."""


class ParsingError(ScrapperError):
    """Raised when parsing of source material fails."""


class DifferError(ScrapperError):
    """Raised when diffing of parsed source material fails."""


class StixBundleError(ScrapperError):
    """Raised when STIX bundle construction fails."""


class BundleStorageError(ScrapperError):
    """Raised when a STIX bundle cannot be persisted."""
