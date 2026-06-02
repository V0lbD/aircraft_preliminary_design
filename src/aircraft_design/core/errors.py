from __future__ import annotations


class AircraftDesignError(Exception):
    """Base exception for aircraft preliminary design application."""


class InputValidationError(AircraftDesignError):
    """Raised when input data is invalid."""


class FileFormatError(AircraftDesignError):
    """Raised when input or output file has invalid format."""


class BlockCalculationError(AircraftDesignError):
    """Raised when a calculation block fails."""


class ConfigurationError(AircraftDesignError):
    """Raised when application configuration is invalid."""