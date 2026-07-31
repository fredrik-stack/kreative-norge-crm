"""Isolated phase 3B.1 image-processing prototype.

Nothing in this package is imported by the Django application. The package exists
only to make the prototype tests and evidence generation reproducible.
"""

from .core import (
    MAX_FILE_BYTES,
    MAX_PIXELS,
    PROCESSING_VERSION,
    VARIANTS,
    ImageLabError,
    SourceRejected,
    UpscaleRequired,
)

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_PIXELS",
    "PROCESSING_VERSION",
    "VARIANTS",
    "ImageLabError",
    "SourceRejected",
    "UpscaleRequired",
]
