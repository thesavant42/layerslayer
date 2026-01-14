#!/usr/bin/env python3
"""
fs_faker.py - Virtual filesystem navigator for Docker layer logs

Filters flat filesystem logs to show only the contents of a specific directory,
simulating the experience of navigating with cd and ls -la.

Usage:
    ./fs_faker.py <logfile> <path>

Example:
    ./fs_faker.py layer-0.txt "/"
    ./fs_faker.py layer-0.txt "/etc"
    ./fs_faker.py layer-0.txt "/etc/apk"
"""

import sys
import re


def parse_line(line: str) -> dict | None:
    """
    Parse a single line from the filesystem log.
    
    Example input:
        '  drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  bin/'
        '  lrwxrwxrwx     0    0     0.0 B  2025-12-16 23:03  bin/arch -> /bin/busybox'
        '  -rw-r--r--     0    0     7.0 B  2025-12-16 23:02  etc/alpine-release'
    
    Returns dict with: permissions, uid, gid, size, date, time, path, link_target
    or None if line cannot be parsed.
    """
    line = line.strip()
    if not line:
        return None
    
    # Pattern matches: permissions uid gid size unit date time path [-> target]
    # Example: drwxr-xr-x     0    0     0.0 B  2025-12-16 23:03  bin/
    pattern = r'^([drwxlst-]{10})\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(B|KB|MB|GB)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.+)$'
    
    match = re.match(pattern, line)
    if not match:
        return None
    
    permissions, uid, gid, size_num, size_unit, date, time, path_part = match.groups()
    
    # Handle symlinks: path -> target
    link_target = None
    path = path_part
    if ' -> ' in path_part:
        path, link_target = path_part.split(' -> ', 1)
    
    return {
        'permissions': permissions,
        'uid': int(uid),
        'gid': int(gid),
        'size': f"{size_num} {size_unit}",
        'date': date,
        'time': time,
        'path': path,
        'link_target': link_target,
        'raw_line': line
    }


def normalize_path(path: str) -> str:
    """
    Normalize a path for comparison.
    
    - Remove leading/trailing slashes
    - Handle root "/" as empty string
    
    Examples:
        "/" -> ""
        "/etc" -> "etc"
        "/etc/" -> "etc"
        "/etc/apk" -> "etc/apk"
    """
    path = path.strip('/')
    return path


def get_parent_path(entry_path: str) -> str:
    """
    Get the parent directory of a path.
    
    Examples:
        "bin/" -> ""  (parent is root)
        "etc/apk/" -> "etc"
        "etc/apk/arch" -> "etc/apk"
    """
    # Remove trailing slash if directory
    clean_path = entry_path.rstrip('/')
    
    if '/' not in clean_path:
        return ""  # Parent is root
    
    return clean_path.rsplit('/', 1)[0]


def get_entry_name(entry_path: str) -> str:
    """
    Get just the name portion of a path (for display).
    
    Examples:
        "bin/" -> "bin/"
        "etc/apk/" -> "apk/"
        "etc/apk/arch" -> "arch"
    """
    clean_path = entry_path.rstrip('/')
    is_dir = entry_path.endswith('/')
    
    if '/' not in clean_path:
        name = clean_path
    else:
        name = clean_path.rsplit('/', 1)[1]
    
    return name + ('/' if is_dir else '')


def get_direct_children(entries: list, target_path: str) -> list:
    """
    Filter entries to show only direct children of target_path.
    
    Args:
        entries: List of parsed entry dicts
        target_path: Target directory path (e.g., "/" or "/etc")
    
    Returns:
        List of entries that are direct children of target_path
    """
    target_normalized = normalize_path(target_path)
    children = []
    
    for entry in entries:
        entry_path = entry['path']
        parent = get_parent_path(entry_path)
        
        if parent == target_normalized:
            children.append(entry)
    
    return children


def format_entry(entry: dict) -> str:
    """
    Format an entry for display (ls -la style).
    
    Uses the original line format from the log file.
    """
    name = get_entry_name(entry['path'])
    
    # Format with link target if present
    if entry['link_target']:
        name = f"{name} -> {entry['link_target']}"
    
    # Format: permissions size date time name
    return f"{entry['permissions']:10}  {entry['size']:>10}  {entry['date']} {entry['time']}  {name}"


def main():
    if len(sys.argv) != 3:
        print("Usage: fs_faker.py <logfile> <path>")
        print("Example: ./fs_faker.py layer-0.txt \"/\"")
        sys.exit(1)
    
    logfile = sys.argv[1]
    target_path = sys.argv[2]
    
    # Read and parse log file
    entries = []
    try:
        with open(logfile, 'r') as f:
            for line in f:
                parsed = parse_line(line)
                if parsed:
                    entries.append(parsed)
    except FileNotFoundError:
        print(f"Error: File '{logfile}' not found")
        sys.exit(1)
    
    # Filter to direct children of target path
    children = get_direct_children(entries, target_path)
    
    if not children:
        print(f"No entries found for path: {target_path}")
        sys.exit(0)
    
    # Print formatted output
    for entry in children:
        print(format_entry(entry))


if __name__ == "__main__":
    main()
