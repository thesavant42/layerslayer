# tar_parser.py
# Manual tar header parser for streaming layer peek
#
# Parses 512-byte tar headers from decompressed data to extract file entries
# without needing the full tar file.

### DO NOT CHANGE THIS FILE!!! NO TOUCHING!


from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TarEntry:
    """A single tar archive entry (file or directory)."""
    name: str
    size: int
    typeflag: str
    is_dir: bool
    # Extended fields for ls -la display
    mode: str           # Unix permissions string (e.g., "drwxr-xr-x")
    uid: int            # User ID
    gid: int            # Group ID
    mtime: str          # Modification time formatted as "YYYY-MM-DD HH:MM"
    linkname: str       # Symlink target (empty if not a symlink)
    is_symlink: bool    # True if this is a symbolic link
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "size": self.size,
            "typeflag": self.typeflag,
            "is_dir": self.is_dir,
            "mode": self.mode,
            "uid": self.uid,
            "gid": self.gid,
            "mtime": self.mtime,
            "linkname": self.linkname,
            "is_symlink": self.is_symlink,
        }


def _mode_to_string(mode_int: int, typeflag: str) -> str:
    """
    Convert octal mode to ls-style permission string.
    
    Examples:
        0o755, typeflag='5' -> 'drwxr-xr-x'
        0o644, typeflag='0' -> '-rw-r--r--'
        0o777, typeflag='2' -> 'lrwxrwxrwx'
    
    Args:
        mode_int: Octal permission bits (e.g., 0o755)
        typeflag: Tar typeflag character
    
    Returns:
        10-character permission string like 'drwxr-xr-x'
    """
    # Type prefix based on typeflag
    type_char = {
        '0': '-',       # Regular file
        '\x00': '-',    # Regular file (null byte)
        '5': 'd',       # Directory
        '2': 'l',       # Symbolic link
        '1': 'h',       # Hard link (show as regular file)
        '3': 'c',       # Character device
        '4': 'b',       # Block device
        '6': 'p',       # FIFO/pipe
        '7': '-',       # Contiguous file (treat as regular)
    }.get(typeflag, '-')
    
    # Permission bits for owner, group, other
    perms = ''
    for shift in [6, 3, 0]:  # owner, group, other
        bits = (mode_int >> shift) & 0o7
        perms += 'r' if bits & 4 else '-'
        perms += 'w' if bits & 2 else '-'
        perms += 'x' if bits & 1 else '-'
    
    return type_char + perms


def _parse_octal(data: bytes, default: int = 0) -> int:
    """Parse octal bytes to integer, handling edge cases."""
    try:
        stripped = data.rstrip(b'\x00').strip()
        if not stripped:
            return default
        return int(stripped, 8)
    except (ValueError, TypeError):
        return default


def _format_mtime(unix_timestamp: int) -> str:
    """Format Unix timestamp to 'YYYY-MM-DD HH:MM' string."""
    try:
        if unix_timestamp <= 0:
            return "----.--.-- --:--"
        dt = datetime.fromtimestamp(unix_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return "----.--.-- --:--"


def parse_tar_header(data: bytes, offset: int = 0) -> tuple[Optional[TarEntry], int]:
    """
    Parse a 512-byte tar header at the given offset.
    
    Returns (entry, next_offset) or (None, -1) if invalid.
    
    Tar header structure (POSIX ustar):
    - 0-99: filename (100 bytes, null-terminated)
    - 100-107: mode (8 bytes octal)
    - 108-115: uid (8 bytes octal)
    - 116-123: gid (8 bytes octal)
    - 124-135: size (12 bytes octal)
    - 136-147: mtime (12 bytes octal)
    - 148-155: checksum (8 bytes)
    - 156: typeflag (1 byte)
    - 157-256: linkname (100 bytes)
    - 257-262: magic "ustar\\0" or "ustar " (6 bytes)
    - 263-264: version
    - 265-296: uname (32 bytes)
    - 297-328: gname (32 bytes)
    - 329-336: devmajor
    - 337-344: devminor
    - 345-500: prefix (155 bytes, for long filenames)
    """
    if offset + 512 > len(data):
        return None, -1
    
    header = data[offset:offset + 512]
    
    # Check for null block (end of archive)
    if header == b'\x00' * 512:
        return None, -1
    
    # Check magic at offset 257 ("ustar") - both GNU and POSIX formats
    magic = header[257:262]
    if magic != b'ustar' and magic[:5] != b'ustar':
        # Might be old format, still try to parse
        pass
    
    # Parse filename (first 100 bytes, null-terminated)
    name_bytes = header[0:100]
    name = name_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
    
    # Check for extended prefix (ustar format, offset 345-500)
    prefix_bytes = header[345:500].rstrip(b'\x00')
    if prefix_bytes:
        prefix = prefix_bytes.decode('utf-8', errors='replace')
        name = f"{prefix}/{name}"
    
    # Parse mode (8 bytes octal at offset 100)
    mode_int = _parse_octal(header[100:108], 0)
    
    # Parse uid (8 bytes octal at offset 108)
    uid = _parse_octal(header[108:116], 0)
    
    # Parse gid (8 bytes octal at offset 116)
    gid = _parse_octal(header[116:124], 0)
    
    # Parse size (12 bytes octal at offset 124)
    size = _parse_octal(header[124:136], 0)
    
    # Parse mtime (12 bytes octal at offset 136)
    mtime_unix = _parse_octal(header[136:148], 0)
    mtime_str = _format_mtime(mtime_unix)
    
    # Parse typeflag (1 byte at offset 156)
    typeflag = chr(header[156]) if header[156] else '0'
    
    # Parse linkname (100 bytes at offset 157, for symlinks)
    linkname_bytes = header[157:257]
    linkname = linkname_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
    
    # Determine entry type
    is_dir = (typeflag == '5' or name.endswith('/'))
    is_symlink = (typeflag == '2')
    
    # Generate permission string
    mode_str = _mode_to_string(mode_int, typeflag)
    
    # Calculate next header offset (header + content + padding to 512 boundary)
    content_blocks = (size + 511) // 512  # Round up to 512-byte blocks
    next_offset = offset + 512 + (content_blocks * 512)
    
    entry = TarEntry(
        name=name,
        size=size,
        typeflag=typeflag,
        is_dir=is_dir,
        mode=mode_str,
        uid=uid,
        gid=gid,
        mtime=mtime_str,
        linkname=linkname,
        is_symlink=is_symlink,
    )
    
    return entry, next_offset
