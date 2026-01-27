"""
FS Simulator Widget.

Exports the FSSimulator widget and parsing utilities for filesystem browsing.
"""

from .fs_simulator import FSSimulator, parse_fslog_line

__all__ = ["FSSimulator", "parse_fslog_line"]
