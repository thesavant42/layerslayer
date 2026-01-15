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


def prompt_overwrite(digest: str, conn: sqlite3.Connection) -> bool:
    """
    Prompt user to confirm overwriting existing layer data.
    
    Shows existing data info and asks for confirmation.
    
    Args:
        digest: Layer digest (sha256:...)
        conn: SQLite connection for fetching existing info
        
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
            if not prompt_overwrite(result.digest, conn):
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
