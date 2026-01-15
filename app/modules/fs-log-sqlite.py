#!/usr/bin/env python3
"""
fs-log-sqlite.py - Virtual filesystem navigator for Docker layer logs stored in sqlite

Database: app/data/lsng.db Prod
Filters flat filesystem logs to show only the contents of a specific directory,
simulating the experience of navigating with cd and ls -la.

By default shows merged view of all layers (overlay filesystem).

Usage:
    ./fs-log-sqlite.py "<owner/repository:tag>" "<path>"
    ./fs-log-sqlite.py "<owner/repository:tag>" <layer_index> "<path>" --single-layer
    ./fs-log-sqlite.py --search <pattern> [<owner/repository:tag>] [<layer_index>]

Example:
    ./fs-log-sqlite.py "alpine/git:v2.52.0" "/"
    ./fs-log-sqlite.py alpine/git:v2.52.0 0 "/" --single-layer
    ./fs-log-sqlite.py --search shadow
    ./fs-log-sqlite.py --search shadow alpine/git:v2.52.0
    ./fs-log-sqlite.py --search shadow alpine/git:v2.52.0 0
"""

import sys
import re
import sqlite3
import argparse
import os


def get_db_path() -> str:
    """
    Get the database path, checking multiple locations in order:
    1. app/data/lsng.db (relative to current working directory)
    2. ignore/fs-log-sqlite.db (dev database)
    3. /app/data/lsng.db (production/Docker path)
    
    Returns the first path that exists, or defaults to app/data/lsng.db
    """
    possible_paths = [
        os.path.join("app", "data", "lsng.db"),
        os.path.join("ignore", "fs-log-sqlite.db"),
        "/app/data/lsng.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Default to the production path if none exist
    return possible_paths[0]


def parse_image_ref(image_ref: str) -> tuple[str, str, str]:
    """
    Parse image reference into owner, repo, and tag.
    
    Examples:
        "alpine/git:v2.52.0" -> ("alpine", "git", "v2.52.0")
        "ubuntu:24.04" -> ("", "ubuntu", "24.04")
        "myowner/myrepo:latest" -> ("myowner", "myrepo", "latest")
    
    Returns:
        Tuple of (owner, repo, tag)
    """
    # Split by colon to separate tag
    if ':' in image_ref:
        repo_part, tag = image_ref.rsplit(':', 1)
    else:
        repo_part = image_ref
        tag = "latest"
    
    # Split repo_part by slash to separate owner and repo
    if '/' in repo_part:
        owner, repo = repo_part.split('/', 1)
    else:
        owner = ""
        repo = repo_part
    
    return owner, repo, tag


def format_size(size_bytes: int) -> str:
    """
    Format size in bytes to human-readable format.
    
    Examples:
        0 -> "0.0 B"
        1024 -> "1.0 KB"
        1048576 -> "1.0 MB"
    """
    if size_bytes < 1024:
        return f"{float(size_bytes):.1f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def db_row_to_entry(row: dict) -> dict:
    """
    Convert a database row to the entry dict format expected by other functions.
    
    Database columns: name, size, mode, uid, gid, mtime, linkname, is_dir, is_symlink
    
    Returns dict with: permissions, uid, gid, size, date, time, path, link_target
    """
    # Split mtime into date and time
    # mtime format: "2025-12-16 23:03"
    mtime = row['mtime'] or "1970-01-01 00:00"
    date, time = mtime.split(' ', 1)
    
    # Add trailing slash for directories
    path = row['name']
    if row['is_dir'] and not path.endswith('/'):
        path += '/'
    
    return {
        'permissions': row['mode'] or '----------',
        'uid': row['uid'] or 0,
        'gid': row['gid'] or 0,
        'size': format_size(row['size'] or 0),
        'date': date,
        'time': time,
        'path': path,
        'link_target': row['linkname'] if row['linkname'] else None,
    }


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


def search_by_name(pattern: str, owner: str = None, repo: str = None, tag: str = None, layer_index: int = None) -> list:
    """
    Search for files/directories by name pattern.
    
    Args:
        pattern: Filename or directory name pattern to search for (supports SQL LIKE patterns)
        owner: Optional owner filter
        repo: Optional repo filter
        tag: Optional tag filter
        layer_index: Optional layer_index filter
    
    Returns:
        List of matching entries
    """
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error: Cannot connect to database '{db_path}': {e}")
        sys.exit(1)
    
    # Build query with optional filters
    query = """
        SELECT owner, repo, tag, layer_index, name, size, mode, uid, gid, mtime, linkname, is_dir, is_symlink
        FROM layer_entries
        WHERE name LIKE ?
    """
    params = [f'%{pattern}%']
    
    if owner is not None:
        query += " AND owner = ?"
        params.append(owner)
    if repo is not None:
        query += " AND repo = ?"
        params.append(repo)
    if tag is not None:
        query += " AND tag = ?"
        params.append(tag)
    if layer_index is not None:
        query += " AND layer_index = ?"
        params.append(layer_index)
    
    query += " ORDER BY owner, repo, tag, layer_index, name"
    
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error: Database query failed: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()
    
    # Convert to entry dicts with image info
    entries = []
    for row in rows:
        entry = db_row_to_entry(dict(row))
        entry['owner'] = row['owner']
        entry['repo'] = row['repo']
        entry['tag'] = row['tag']
        entry['layer_index'] = row['layer_index']
        entries.append(entry)
    
    return entries


def format_search_entry(entry: dict) -> str:
    """
    Format a search result entry with image information.
    """
    image_info = f"{entry['owner']}/{entry['repo']}:{entry['tag']} layer {entry['layer_index']}"
    name = get_entry_name(entry['path'])
    
    # Format with link target if present
    if entry['link_target']:
        name = f"{name} -> {entry['link_target']}"
    
    # Format: permissions size date time name [image_info]
    return f"{entry['permissions']:10}  {entry['size']:>10}  {entry['date']} {entry['time']}  {name:50} [{image_info}]"


def get_merged_layers(owner: str, repo: str, tag: str, target_path: str) -> list:
    """
    Get merged view of all layers for a tag, with higher layers overriding lower ones.
    
    Returns:
        List of entries with 'overridden' flag set for files shadowed by higher layers
    """
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error: Cannot connect to database '{db_path}': {e}")
        sys.exit(1)
    
    # Query all layers for this image
    query = """
        SELECT name, size, mode, uid, gid, mtime, linkname, is_dir, is_symlink, layer_index
        FROM layer_entries
        WHERE owner = ? AND repo = ? AND tag = ?
        ORDER BY layer_index ASC, name
    """
    
    try:
        cursor.execute(query, (owner, repo, tag))
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error: Database query failed: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()
    
    if not rows:
        return []
    
    # Group entries by path, keeping track of which layer they're from
    path_layers = {}  # path -> [(layer_index, entry), ...]
    
    for row in rows:
        entry = db_row_to_entry(dict(row))
        entry['layer_index'] = row['layer_index']
        path = entry['path']
        
        if path not in path_layers:
            path_layers[path] = []
        path_layers[path].append((row['layer_index'], entry))
    
    # For each path, mark all but the highest layer as overridden
    merged_entries = []
    for path, layer_entries in path_layers.items():
        # Sort by layer_index descending (highest layer first)
        layer_entries.sort(key=lambda x: x[0], reverse=True)
        
        for idx, (layer_idx, entry) in enumerate(layer_entries):
            # First entry (highest layer) is active, rest are overridden
            entry['overridden'] = (idx > 0)
            entry['layer_index'] = layer_idx
            merged_entries.append(entry)
    
    # Filter to direct children of target path
    children = get_direct_children(merged_entries, target_path)
    
    # Group by path to keep overridden entries together
    path_groups = {}
    for child in children:
        path = child['path']
        if path not in path_groups:
            path_groups[path] = []
        path_groups[path].append(child)
    
    # Sort each group by layer_index (highest first)
    result = []
    for path in sorted(path_groups.keys()):
        group = path_groups[path]
        group.sort(key=lambda x: x['layer_index'], reverse=True)
        result.extend(group)
    
    return result


def format_merged_entry(entry: dict) -> str:
    """
    Format an entry for merged layer view.
    Shows layer number and marks overridden entries.
    
    Args:
        entry: Entry dict with 'overridden' and 'layer_index' keys
    """
    name = get_entry_name(entry['path'])
    
    # Format with link target if present
    if entry['link_target']:
        name = f"{name} -> {entry['link_target']}"
    
    layer_info = f"L{entry['layer_index']}"
    
    # Format: permissions size date time name [layer]
    base_format = f"{entry['permissions']:10}  {entry['size']:>10}  {entry['date']} {entry['time']}  {name:50} [{layer_info}]"
    
    # Add (overridden) marker for shadowed entries
    if entry['overridden']:
        return f"{base_format} (overridden)"
    
    return base_format


def main():
    parser = argparse.ArgumentParser(
        description='Virtual filesystem navigator for Docker layer logs stored in sqlite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s alpine/git:v2.52.0 "/"
  %(prog)s alpine/git:v2.52.0 "/etc"
  %(prog)s alpine/git:v2.52.0 0 "/" --single-layer
  %(prog)s --search shadow
  %(prog)s --search shadow alpine/git:v2.52.0
  %(prog)s --search shadow alpine/git:v2.52.0 0
        """
    )
    
    parser.add_argument('--search', '-s', metavar='PATTERN', 
                       help='Search for files/directories matching pattern (supports SQL LIKE patterns)')
    parser.add_argument('--single-layer', action='store_true',
                       help='Show single layer instead of merged view (requires layer_index)')
    parser.add_argument('image_ref', nargs='?', 
                       help='Image reference: owner/repository:tag')
    parser.add_argument('layer_or_path', nargs='?',
                       help='Layer index number or path')
    parser.add_argument('path', nargs='?',
                       help='Directory path to list (e.g., "/" or "/etc")')
    
    args = parser.parse_args()
    
    # Search mode
    if args.search:
        owner = None
        repo = None
        tag = None
        layer_index = None
        
        # Parse optional image_ref and layer_index if provided
        if args.image_ref:
            owner, repo, tag = parse_image_ref(args.image_ref)
            if args.layer_or_path is not None:
                try:
                    layer_index = int(args.layer_or_path)
                except ValueError:
                    pass  # Not a layer index, ignore
        
        entries = search_by_name(args.search, owner, repo, tag, layer_index)
        
        if not entries:
            search_info = args.search
            if args.image_ref:
                search_info += f" in {args.image_ref}"
                if layer_index is not None:
                    search_info += f" layer {layer_index}"
            print(f"No entries found matching: {search_info}")
            sys.exit(0)
        
        # Print formatted output
        for entry in entries:
            print(format_search_entry(entry))
        return
    
    # Single layer mode (requires explicit flag and layer index)
    if args.single_layer:
        if not args.image_ref or args.layer_or_path is None or not args.path:
            print("Error: --single-layer requires image_ref, layer_index, and path")
            parser.print_help()
            sys.exit(1)
        
        image_ref = args.image_ref
        try:
            layer_index = int(args.layer_or_path)
        except ValueError:
            print(f"Error: layer_index must be an integer, got '{args.layer_or_path}'")
            sys.exit(1)
        target_path = args.path
        
        # Parse image reference
        owner, repo, tag = parse_image_ref(image_ref)
        
        # Connect to SQLite database
        db_path = get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        except sqlite3.Error as e:
            print(f"Error: Cannot connect to database '{db_path}': {e}")
            sys.exit(1)
        
        # Query layer entries
        query = """
            SELECT name, size, mode, uid, gid, mtime, linkname, is_dir, is_symlink
            FROM layer_entries
            WHERE owner = ? AND repo = ? AND tag = ? AND layer_index = ?
        """
        
        try:
            cursor.execute(query, (owner, repo, tag, layer_index))
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error: Database query failed: {e}")
            conn.close()
            sys.exit(1)
        
        if not rows:
            print(f"No entries found for {image_ref} layer {layer_index}")
            conn.close()
            sys.exit(0)
        
        # Convert database rows to entry dicts
        entries = [db_row_to_entry(dict(row)) for row in rows]
        
        conn.close()
        
        # Filter to direct children of target path
        children = get_direct_children(entries, target_path)
        
        if not children:
            print(f"No entries found for path: {target_path}")
            sys.exit(0)
        
        # Print formatted output
        for entry in children:
            print(format_entry(entry))
        return
    
    # Default: Merged layer mode
    if not args.image_ref:
        parser.print_help()
        sys.exit(1)
    
    # Determine target path for merged mode
    if args.path:
        # Three args: image layer path - path is the actual path
        target_path = args.path
    elif args.layer_or_path:
        # Two args: image path_or_layer
        # If it looks like a path (starts with / or is /), use it as path
        if args.layer_or_path.startswith('/') or args.layer_or_path == '/':
            target_path = args.layer_or_path
        else:
            # Treat as path anyway for merged mode
            target_path = args.layer_or_path
    else:
        # One arg: just image, default to root
        target_path = "/"
    
    image_ref = args.image_ref
    owner, repo, tag = parse_image_ref(image_ref)
    
    entries = get_merged_layers(owner, repo, tag, target_path)
    
    if not entries:
        print(f"No entries found for {image_ref} at path: {target_path}")
        sys.exit(0)
    
    # Print formatted output
    for entry in entries:
        print(format_merged_entry(entry))


if __name__ == "__main__":
    main()
