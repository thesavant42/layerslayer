from dataclasses import dataclass
from typing import Optional
from tar_parser import TarEntry

# =============================================================================
# Data Classes for Streaming Peek Results
# =============================================================================

@dataclass
class LayerPeekResult:
    """Result of peeking into a layer blob."""
    digest: str
    partial: bool
    bytes_downloaded: int
    bytes_decompressed: int
    entries_found: int
    entries: list[TarEntry]
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "digest": self.digest,
            "partial": self.partial,
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_decompressed": self.bytes_decompressed,
            "entries_found": self.entries_found,
            "entries": [e.to_dict() for e in self.entries],
            "error": self.error,
        }
