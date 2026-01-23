# storage.py - Layer data persistence to JSON and SQLite
#
# Stores layer peek results for later analysis, reporting, and navigation.
# See plans/layer-storage-plan.md for design details.

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

from app.modules.finders.layerPeekResult import LayerPeekResult
from app.modules.finders.tar_parser import TarEntry
from app.modules.formatters import parse_image_ref


# =============================================================================
# Database Configuration
# =============================================================================

DEFAULT_DB_PATH = "app/data/lsng.db"
DEFAULT_JSON_DIR = "app/loot"


# =============================================================================
# Database Initialization
# =============================================================================

def init_database(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Initialize SQLite database with schema for layer storage.
    
    Creates the database file and tables if they don't exist.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        sqlite3.Connection to the database
    """
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    
    cursor = conn.cursor()
    
    # Create layer_entries table - stores each filesystem entry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layer_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            layer_digest TEXT NOT NULL,
            image_ref TEXT,
            owner TEXT,
            repo TEXT,
            tag TEXT,
            layer_index INTEGER,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            -- Entry fields from TarEntry
            name TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            typeflag TEXT,
            is_dir BOOLEAN DEFAULT 0,
            mode TEXT,
            uid INTEGER DEFAULT 0,
            gid INTEGER DEFAULT 0,
            mtime TEXT,
            linkname TEXT,
            is_symlink BOOLEAN DEFAULT 0,
            
            UNIQUE(layer_digest, name)
        )
    """)
    
    # Create layer_metadata table - stores summary per layer
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layer_metadata (
            layer_digest TEXT PRIMARY KEY,
            image_ref TEXT,
            owner TEXT,
            repo TEXT,
            tag TEXT,
            layer_index INTEGER,
            layer_size INTEGER,
            entries_count INTEGER,
            bytes_downloaded INTEGER,
            bytes_decompressed INTEGER,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            json_filename TEXT
        )
    """)
    
    # Create image_configs table - stores cached image configuration JSON
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_configs (
            config_digest TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            repo TEXT NOT NULL,
            tag TEXT NOT NULL,
            arch TEXT DEFAULT 'amd64',
            config_json TEXT NOT NULL,
            layer_count INTEGER NOT NULL,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner, repo, tag, arch)
        )
    """)
    
    # Create image_layers table - tracks layer peek status per config
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_layers (
            config_digest TEXT NOT NULL,
            layer_index INTEGER NOT NULL,
            layer_digest TEXT NOT NULL,
            layer_size INTEGER DEFAULT 0,
            peeked BOOLEAN DEFAULT 0,
            peeked_at DATETIME,
            entries_count INTEGER DEFAULT 0,
            FOREIGN KEY (config_digest) REFERENCES image_configs(config_digest),
            PRIMARY KEY (config_digest, layer_index)
        )
    """)
    
    # Create indexes for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_layer_digest 
        ON layer_entries(layer_digest)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entry_name 
        ON layer_entries(name)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_image_ref 
        ON layer_entries(image_ref)
    """)
    
    conn.commit()
    return conn


# =============================================================================
# Cache Detection
# =============================================================================

def check_layer_exists(conn: sqlite3.Connection, digest: str) -> bool:
    """
    Check if a layer digest already exists in the database.
    
    Args:
        conn: SQLite connection
        digest: Layer digest (sha256:...)
        
    Returns:
        True if layer exists, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM layer_metadata WHERE layer_digest = ?",
        (digest,)
    )
    return cursor.fetchone() is not None


def get_layer_info(conn: sqlite3.Connection, digest: str) -> Optional[dict]:
    """
    Get existing layer metadata from database.
    
    Args:
        conn: SQLite connection
        digest: Layer digest (sha256:...)
        
    Returns:
        Dict with layer metadata, or None if not found
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM layer_metadata WHERE layer_digest = ?",
        (digest,)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


def prompt_overwrite(digest: str, conn: sqlite3.Connection, force: bool = False) -> bool:
    """
    Prompt user to confirm overwriting existing layer data.
    
    Shows existing data info and asks for confirmation.
    
    Args:
        digest: Layer digest (sha256:...)
        conn: SQLite connection for fetching existing info
        force: If True, automatically overwrite without prompting
        
    Returns:
        True if user wants to overwrite, False to skip
    """
    info = get_layer_info(conn, digest)
    if not info:
        return True  # No existing data, proceed
    
    short_digest = digest[:19] + "..." if len(digest) > 22 else digest
    
    print(f"\n  Layer {short_digest} already exists in database.")
    print(f"    - Scraped: {info.get('scraped_at', 'unknown')}")
    print(f"    - Entries: {info.get('entries_count', 0):,} files")
    print(f"    - Image: {info.get('image_ref', 'unknown')}")
    print()
    
    if force:
        print("  --force enabled: overwriting automatically")
        return True
    
    response = input("  Overwrite existing data? [y/N]: ").strip().lower()
    return response in ('y', 'yes')


def delete_layer_data(conn: sqlite3.Connection, digest: str) -> None:
    """
    Delete existing layer data before overwriting.
    
    Args:
        conn: SQLite connection
        digest: Layer digest to delete
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM layer_entries WHERE layer_digest = ?", (digest,))
    cursor.execute("DELETE FROM layer_metadata WHERE layer_digest = ?", (digest,))
    conn.commit()


# =============================================================================
# SQLite Storage
# =============================================================================

def save_layer_sqlite(
    conn: sqlite3.Connection,
    result: LayerPeekResult,
    image_ref: str,
    layer_index: int,
    layer_size: int = 0,
    json_filename: Optional[str] = None,
) -> None:
    """
    Save layer peek result to SQLite database.
    
    Args:
        conn: SQLite connection
        result: LayerPeekResult from peek operation
        image_ref: Image reference (e.g., "nginx:latest")
        layer_index: Zero-based layer number
        layer_size: Compressed layer size in bytes
        json_filename: Optional reference to JSON file
    """
    owner, repo, tag = parse_image_ref(image_ref)
    scraped_at = datetime.now().isoformat()
    
    cursor = conn.cursor()
    
    # Insert or replace layer metadata
    cursor.execute("""
        INSERT OR REPLACE INTO layer_metadata (
            layer_digest, image_ref, owner, repo, tag, layer_index,
            layer_size, entries_count, bytes_downloaded, bytes_decompressed,
            scraped_at, json_filename
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.digest,
        image_ref,
        owner,
        repo,
        tag,
        layer_index,
        layer_size,
        result.entries_found,
        result.bytes_downloaded,
        result.bytes_decompressed,
        scraped_at,
        json_filename,
    ))
    
    # Insert all entries
    for entry in result.entries:
        cursor.execute("""
            INSERT OR REPLACE INTO layer_entries (
                layer_digest, image_ref, owner, repo, tag, layer_index,
                scraped_at, name, size, typeflag, is_dir, mode,
                uid, gid, mtime, linkname, is_symlink
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.digest,
            image_ref,
            owner,
            repo,
            tag,
            layer_index,
            scraped_at,
            entry.name,
            entry.size,
            entry.typeflag,
            entry.is_dir,
            entry.mode,
            entry.uid,
            entry.gid,
            entry.mtime,
            entry.linkname,
            entry.is_symlink,
        ))
    
    conn.commit()


# =============================================================================
# JSON Storage
# =============================================================================

def generate_json_filename(
    image_ref: str,
    layer_index: int,
) -> str:
    """
    Generate JSON filename per TASK.md naming convention.
    
    Format: owner-repo-tag-fslyr-NN-MMDDYYYY.json
    
    Args:
        image_ref: Image reference (e.g., "nginx:latest")
        layer_index: Zero-based layer number
        
    Returns:
        Filename string (without directory)
    """
    owner, repo, tag = parse_image_ref(image_ref)
    
    # Sanitize for filesystem (replace problematic chars)
    owner = owner.replace("/", "-").replace(":", "-")
    repo = repo.replace("/", "-").replace(":", "-")
    tag = tag.replace("/", "-").replace(":", "-")
    
    # Format layer number (zero-padded to 2 digits)
    layer_num = f"{layer_index + 1:02d}"
    
    # Format date as MMDDYYYY
    date_str = datetime.now().strftime("%m%d%Y")
    
    return f"{owner}-{repo}-{tag}-fslyr-{layer_num}-{date_str}.json"


def save_layer_json(
    result: LayerPeekResult,
    image_ref: str,
    layer_index: int,
    layer_size: int = 0,
    output_dir: str = DEFAULT_JSON_DIR,
) -> str:
    """
    Save layer peek result to JSON file.
    
    Args:
        result: LayerPeekResult from peek operation
        image_ref: Image reference (e.g., "nginx:latest")
        layer_index: Zero-based layer number
        layer_size: Compressed layer size in bytes
        output_dir: Directory for JSON files
        
    Returns:
        Full path to saved JSON file
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    owner, repo, tag = parse_image_ref(image_ref)
    filename = generate_json_filename(image_ref, layer_index)
    filepath = os.path.join(output_dir, filename)
    
    # Build JSON structure
    data = {
        "metadata": {
            "layer_digest": result.digest,
            "image_ref": image_ref,
            "owner": owner,
            "repo": repo,
            "tag": tag,
            "layer_index": layer_index,
            "layer_size": layer_size,
            "scraped_at": datetime.now().isoformat(),
        },
        "stats": {
            "entries_count": result.entries_found,
            "bytes_downloaded": result.bytes_downloaded,
            "bytes_decompressed": result.bytes_decompressed,
            "partial": result.partial,
            "error": result.error,
        },
        "entries": [entry.to_dict() for entry in result.entries],
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    return filepath


# =============================================================================
# Combined Save Operation
# =============================================================================

def save_layer_result(
    result: LayerPeekResult,
    image_ref: str,
    layer_index: int,
    layer_size: int = 0,
    conn: Optional[sqlite3.Connection] = None,
    db_path: str = DEFAULT_DB_PATH,
    json_dir: str = DEFAULT_JSON_DIR,
    check_exists: bool = True,
    force_overwrite: bool = False,
) -> tuple[bool, str]:
    """
    Save layer result to both JSON and SQLite.
    
    Handles cache checking and user prompts.
    
    Args:
        result: LayerPeekResult from peek operation
        image_ref: Image reference (e.g., "nginx:latest")
        layer_index: Zero-based layer number
        layer_size: Compressed layer size in bytes
        conn: Optional existing SQLite connection
        db_path: Path to SQLite database
        json_dir: Directory for JSON files
        check_exists: Whether to check for existing data
        force_overwrite: If True, overwrite existing data without prompting
        
    Returns:
        Tuple of (success, json_filepath or error message)
    """
    # Get or create database connection
    close_conn = False
    if conn is None:
        conn = init_database(db_path)
        close_conn = True
    
    try:
        # Check for existing data
        if check_exists and check_layer_exists(conn, result.digest):
            if not prompt_overwrite(result.digest, conn, force=force_overwrite):
                return (False, "Skipped - user chose not to overwrite")
            # Delete existing data before re-inserting
            delete_layer_data(conn, result.digest)
        
        # Save to JSON
        json_path = save_layer_json(
            result=result,
            image_ref=image_ref,
            layer_index=layer_index,
            layer_size=layer_size,
            output_dir=json_dir,
        )
        
        # Save to SQLite
        save_layer_sqlite(
            conn=conn,
            result=result,
            image_ref=image_ref,
            layer_index=layer_index,
            layer_size=layer_size,
            json_filename=os.path.basename(json_path),
        )
        
        return (True, json_path)
        
    finally:
        if close_conn:
            conn.close()


# =============================================================================
# Query Functions (for future Textual widget)
# =============================================================================

def get_all_layers(conn: sqlite3.Connection) -> list[dict]:
    """
    Get all layer metadata from database.
    
    Returns:
        List of layer metadata dicts
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM layer_metadata ORDER BY scraped_at DESC")
    return [dict(row) for row in cursor.fetchall()]


def get_layer_entries(
    conn: sqlite3.Connection,
    digest: str,
    parent_path: str = "",
) -> list[dict]:
    """
    Get entries for a layer, optionally filtered by parent path.
    
    Args:
        conn: SQLite connection
        digest: Layer digest
        parent_path: Filter to direct children of this path
        
    Returns:
        List of entry dicts
    """
    cursor = conn.cursor()
    
    if parent_path:
        # Filter to direct children of parent_path
        # Normalize parent path (remove trailing slash)
        parent = parent_path.rstrip("/")
        if parent:
            # Match entries where name starts with parent/ and has no more slashes
            pattern = f"{parent}/%"
            cursor.execute("""
                SELECT * FROM layer_entries 
                WHERE layer_digest = ? 
                AND name LIKE ?
                AND name NOT LIKE ?
                ORDER BY is_dir DESC, name ASC
            """, (digest, pattern, f"{parent}/%/%"))
        else:
            # Root level - match entries with no slashes (except trailing for dirs)
            cursor.execute("""
                SELECT * FROM layer_entries 
                WHERE layer_digest = ? 
                AND name NOT LIKE '%/%/%'
                AND (name NOT LIKE '%/%' OR name LIKE '%/' AND name NOT LIKE '%/%/%')
                ORDER BY is_dir DESC, name ASC
            """, (digest,))
    else:
        # Return all entries
        cursor.execute("""
            SELECT * FROM layer_entries 
            WHERE layer_digest = ?
            ORDER BY is_dir DESC, name ASC
        """, (digest,))
    
    return [dict(row) for row in cursor.fetchall()]

# =============================================================================
# Image Config Caching
# =============================================================================

def save_image_config(
    conn: sqlite3.Connection,
    config_digest: str,
    owner: str,
    repo: str,
    tag: str,
    config_json: dict,
    layer_digests: list[str],
    layer_sizes: list[int] = None,
    arch: str = "amd64",
) -> None:
    """
    Save image configuration and initialize layer tracking.
    
    Stores the full config JSON and creates entries in image_layers
    for each layer with peeked=0.
    
    Args:
        conn: SQLite connection
        config_digest: Config blob digest from manifest
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        config_json: Full config dict from registry
        layer_digests: Ordered list of layer digests (from rootfs.diff_ids or manifest)
        layer_sizes: Optional list of layer sizes (same order as layer_digests)
        arch: Architecture (default: amd64)
    """
    cursor = conn.cursor()
    fetched_at = datetime.now().isoformat()
    
    # Serialize config to JSON string
    config_json_str = json.dumps(config_json)
    layer_count = len(layer_digests)
    
    # Insert or replace image config
    cursor.execute("""
        INSERT OR REPLACE INTO image_configs (
            config_digest, owner, repo, tag, arch,
            config_json, layer_count, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        config_digest,
        owner,
        repo,
        tag,
        arch,
        config_json_str,
        layer_count,
        fetched_at,
    ))
    
    # Delete existing layer entries for this config (in case of refresh)
    cursor.execute(
        "DELETE FROM image_layers WHERE config_digest = ?",
        (config_digest,)
    )
    
    # Insert layer entries with peeked=0
    if layer_sizes is None:
        layer_sizes = [0] * layer_count
    
    for idx, (digest, size) in enumerate(zip(layer_digests, layer_sizes)):
        cursor.execute("""
            INSERT INTO image_layers (
                config_digest, layer_index, layer_digest, layer_size, peeked
            ) VALUES (?, ?, ?, ?, 0)
        """, (
            config_digest,
            idx,
            digest,
            size,
        ))
    
    conn.commit()


def get_cached_config(
    conn: sqlite3.Connection,
    owner: str,
    repo: str,
    tag: str,
    arch: str = "amd64",
) -> Optional[dict]:
    """
    Retrieve cached image configuration.
    
    Args:
        conn: SQLite connection
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        arch: Architecture (default: amd64)
        
    Returns:
        Dict with config_digest, config_json (parsed), layer_count, fetched_at
        or None if not cached
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT config_digest, config_json, layer_count, fetched_at
        FROM image_configs
        WHERE owner = ? AND repo = ? AND tag = ? AND arch = ?
    """, (owner, repo, tag, arch))
    
    row = cursor.fetchone()
    if row:
        return {
            "config_digest": row["config_digest"],
            "config_json": json.loads(row["config_json"]),
            "layer_count": row["layer_count"],
            "fetched_at": row["fetched_at"],
        }
    return None


def get_layer_status(
    conn: sqlite3.Connection,
    owner: str,
    repo: str,
    tag: str,
    arch: str = "amd64",
) -> Optional[dict]:
    """
    Get layer peek status for an image.
    
    Returns layer count, idx-to-digest mapping, and peek status per layer.
    
    Args:
        conn: SQLite connection
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        arch: Architecture (default: amd64)
        
    Returns:
        Dict with:
            - config_digest: str
            - config_cached: bool (always True if result returned)
            - layer_count: int
            - layers: list of {idx, digest, size, peeked, peeked_at, entries_count}
            - peeked_count: int
            - unpeeked_count: int
        or None if no cached config
    """
    cursor = conn.cursor()
    
    # First get the config
    cursor.execute("""
        SELECT config_digest, layer_count, fetched_at
        FROM image_configs
        WHERE owner = ? AND repo = ? AND tag = ? AND arch = ?
    """, (owner, repo, tag, arch))
    
    config_row = cursor.fetchone()
    if not config_row:
        return None
    
    config_digest = config_row["config_digest"]
    layer_count = config_row["layer_count"]
    
    # Get all layers for this config
    cursor.execute("""
        SELECT layer_index, layer_digest, layer_size, peeked, peeked_at, entries_count
        FROM image_layers
        WHERE config_digest = ?
        ORDER BY layer_index ASC
    """, (config_digest,))
    
    layers = []
    peeked_count = 0
    for row in cursor.fetchall():
        is_peeked = bool(row["peeked"])
        if is_peeked:
            peeked_count += 1
        layers.append({
            "idx": row["layer_index"],
            "digest": row["layer_digest"],
            "size": row["layer_size"],
            "peeked": is_peeked,
            "peeked_at": row["peeked_at"],
            "entries_count": row["entries_count"],
        })
    
    return {
        "config_digest": config_digest,
        "config_cached": True,
        "layer_count": layer_count,
        "layers": layers,
        "peeked_count": peeked_count,
        "unpeeked_count": layer_count - peeked_count,
    }


def update_layer_peeked(
    conn: sqlite3.Connection,
    config_digest: str,
    layer_index: int,
    entries_count: int = 0,
) -> None:
    """
    Mark a layer as peeked.
    
    Args:
        conn: SQLite connection
        config_digest: Config digest the layer belongs to
        layer_index: Layer index to mark as peeked
        entries_count: Number of filesystem entries found
    """
    cursor = conn.cursor()
    peeked_at = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE image_layers
        SET peeked = 1, peeked_at = ?, entries_count = ?
        WHERE config_digest = ? AND layer_index = ?
    """, (peeked_at, entries_count, config_digest, layer_index))
    
    conn.commit()


def get_config_by_digest(
    conn: sqlite3.Connection,
    config_digest: str,
) -> Optional[dict]:
    """
    Retrieve cached image configuration by its digest.
    
    Args:
        conn: SQLite connection
        config_digest: Config blob digest
        
    Returns:
        Dict with owner, repo, tag, arch, config_json (parsed), layer_count, fetched_at
        or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT owner, repo, tag, arch, config_json, layer_count, fetched_at
        FROM image_configs
        WHERE config_digest = ?
    """, (config_digest,))
    
    row = cursor.fetchone()
    if row:
        return {
            "owner": row["owner"],
            "repo": row["repo"],
            "tag": row["tag"],
            "arch": row["arch"],
            "config_json": json.loads(row["config_json"]),
            "layer_count": row["layer_count"],
            "fetched_at": row["fetched_at"],
        }
    return None


# =============================================================================
# File Layer Lookup (for Carve optimization)
# =============================================================================

def find_file_layers(
    conn: sqlite3.Connection,
    owner: str,
    repo: str,
    tag: str,
    file_path: str,
) -> list[dict]:
    """
    Find ALL layers containing a specific file path.
    
    A file can exist in multiple layers (each layer may modify it).
    Returns all layers with that file for change tracking / forensics.
    
    Args:
        conn: SQLite connection
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        file_path: Target file path (e.g., "/etc/passwd")
        
    Returns:
        List of dicts with layer_index, size, mtime for each occurrence,
        ordered by layer_index ascending (oldest to newest)
    """
    cursor = conn.cursor()
    
    # Normalize path - remove leading slash and ./ prefix
    normalized = file_path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/"):
        normalized = normalized[1:]
    
    # Query for all matches on normalized name
    cursor.execute("""
        SELECT layer_index, size, mtime, layer_digest
        FROM layer_entries
        WHERE owner = ? AND repo = ? AND tag = ?
        AND (name = ? OR name = ?)
        ORDER BY layer_index ASC
    """, (owner, repo, tag, normalized, file_path.lstrip("/")))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "layer_index": row["layer_index"],
            "size": row["size"],
            "mtime": row["mtime"],
            "layer_digest": row["layer_digest"],
        })
    return results


def get_cached_layers(
    conn: sqlite3.Connection,
    owner: str,
    repo: str,
    tag: str,
    arch: str = "amd64",
) -> Optional[list[dict]]:
    """
    Get cached layer info (digests and sizes) for an image.
    
    Returns layer info from image_layers table if the config is cached,
    allowing carve operations to skip the manifest fetch.
    
    Args:
        conn: SQLite connection
        owner: Image namespace/owner
        repo: Repository name
        tag: Image tag
        arch: Architecture (default: amd64)
        
    Returns:
        List of dicts with digest and size per layer, or None if not cached
    """
    cursor = conn.cursor()
    
    # First get the config digest
    cursor.execute("""
        SELECT config_digest
        FROM image_configs
        WHERE owner = ? AND repo = ? AND tag = ? AND arch = ?
    """, (owner, repo, tag, arch))
    
    config_row = cursor.fetchone()
    if not config_row:
        return None
    
    # Get layers for this config
    cursor.execute("""
        SELECT layer_index, layer_digest, layer_size
        FROM image_layers
        WHERE config_digest = ?
        ORDER BY layer_index ASC
    """, (config_row["config_digest"],))
    
    layers = []
    for row in cursor.fetchall():
        layers.append({
            "index": row["layer_index"],
            "digest": row["layer_digest"],
            "size": row["layer_size"],
        })
    
    return layers if layers else None


# =============================================================================
# History Query
# =============================================================================

VALID_SORTBY_COLUMNS = {"scraped_at", "owner", "repo", "tag", "layer_index", "layer_size"}


def get_history(
    conn: sqlite3.Connection,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 30,
    sortby: str = "scraped_at",
    order: str = "desc",
) -> list[dict]:
    """
    Query layer history from database with pagination, sorting, and filtering.
    
    Args:
        conn: SQLite connection
        q: Optional search query to filter by owner, repo, or tag
        page: Page number (1-indexed)
        page_size: Number of results per page
        sortby: Column to sort by (scraped_at, owner, repo, tag, layer_index, layer_size)
        order: Sort order (asc or desc)
        
    Returns:
        List of dicts with scraped_at, owner, repo, tag, layer_index, layer_size
    """
    # Validate sortby column
    if sortby not in VALID_SORTBY_COLUMNS:
        sortby = "scraped_at"
    
    # Validate order
    if order.lower() not in ("asc", "desc"):
        order = "desc"
    
    cursor = conn.cursor()
    
    # Build query
    base_query = """
        SELECT scraped_at, owner, repo, tag, layer_index, layer_size
        FROM layer_metadata
    """
    
    params = []
    
    # Add filter if search query provided
    if q:
        base_query += """
        WHERE owner LIKE ? OR repo LIKE ? OR tag LIKE ?
        """
        search_pattern = f"%{q}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # Add ORDER BY
    base_query += f" ORDER BY {sortby} {order.upper()}"
    
    # Add pagination
    offset = (page - 1) * page_size
    base_query += " LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    cursor.execute(base_query, params)
    return [dict(row) for row in cursor.fetchall()]