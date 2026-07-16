"""Expose the duplicate resolution and removal pipelines at the package level."""

from .pipeline import resolve, remove

__all__ = ["resolve", "remove"]
