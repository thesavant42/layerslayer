"""
Utility functions for formatting data in the TUI.

Contains:
- Date formatting helpers
- Data structure flattening
- Binary content detection
- OCI config formatting
- Repository slug parsing
"""


def format_history_date(iso_date: str) -> str:
    """Convert ISO date to MM-DD-YYYY format.
    
    Args:
        iso_date: ISO 8601 date string like '2025-01-27T04:14:00.804659581Z'
        
    Returns:
        Formatted date string like '01-27-2025'
    """
    if not iso_date:
        return ""
    try:
        # Parse ISO format and reformat
        date_part = iso_date.split("T")[0]  # '2025-01-27'
        parts = date_part.split("-")  # ['2025', '01', '27']
        if len(parts) == 3:
            return f"{parts[1]}-{parts[2]}-{parts[0]}"  # MM-DD-YYYY
    except Exception:
        pass
    return iso_date


def flatten_nested(obj: dict | list, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten nested dict/list into (field, value) tuples with dot notation.
    
    Args:
        obj: Dictionary or list to flatten
        prefix: Optional prefix for field names (used in recursion)
        
    Returns:
        List of (field_name, value_string) tuples
    """
    rows = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            field = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                rows.extend(flatten_nested(value, field))
            elif isinstance(value, list):
                if len(value) == 0:
                    rows.append((field, "(empty list)"))
                else:
                    for i, item in enumerate(value):
                        item_field = f"{field}[{i}]"
                        if isinstance(item, dict):
                            rows.extend(flatten_nested(item, item_field))
                        else:
                            rows.append((item_field, str(item)))
            elif value is None:
                rows.append((field, "(null)"))
            else:
                rows.append((field, str(value)))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            item_field = f"{prefix}[{i}]" if prefix else f"[{i}]"
            if isinstance(item, dict):
                rows.extend(flatten_nested(item, item_field))
            else:
                rows.append((item_field, str(item)))
    
    return rows


def is_binary_content(content: str) -> bool:
    """Detect if content appears to be binary data.
    
    Checks for:
    1. Null bytes (\\x00) - definitive binary indicator
    2. High ratio of non-printable characters (>10%)
    
    Args:
        content: String content to check
        
    Returns:
        True if content appears to be binary data
    """
    if '\x00' in content:
        return True
    
    # Sample first 1000 chars to check non-printable ratio
    sample = content[:1000]
    if not sample:
        return False
    
    non_printable = sum(1 for c in sample if not c.isprintable() and c not in '\n\r\t')
    return non_printable / len(sample) > 0.1  # >10% non-printable = binary


def format_config(config: dict) -> list[tuple[str, str]]:
    """Format OCI config JSON for display per tags-TASK.md requirements.
    
    Groups data in order:
    1. architecture, os (top-level)
    2. config.* values
    3. history entries combined: MM-DD-YYYY - created_by (skip empty_layer)
    4. rootfs.type and rootfs.diff_ids
    
    Args:
        config: OCI config JSON dict
        
    Returns:
        List of (field_name, value_string) tuples
    """
    rows = []
    
    # 1. Architecture and OS at top
    if "architecture" in config:
        rows.append(("architecture", str(config["architecture"])))
    if "os" in config:
        rows.append(("os", str(config["os"])))
    
    # 2. Useful config.* values only (Env, Cmd, Entrypoint, Labels, WorkingDir, ExposedPorts)
    if "config" in config and isinstance(config["config"], dict):
        cfg = config["config"]
        
        # Env variables
        if "Env" in cfg and isinstance(cfg["Env"], list):
            for env_val in cfg["Env"]:
                rows.append(("", str(env_val)))
        
        # Cmd
        if "Cmd" in cfg and isinstance(cfg["Cmd"], list):
            rows.append(("Cmd", " ".join(cfg["Cmd"])))
        
        # Entrypoint
        if "Entrypoint" in cfg and isinstance(cfg["Entrypoint"], list):
            rows.append(("Entrypoint", " ".join(cfg["Entrypoint"])))
        
        # WorkingDir
        if "WorkingDir" in cfg and cfg["WorkingDir"]:
            rows.append(("WorkingDir", str(cfg["WorkingDir"])))
        
        # ExposedPorts
        if "ExposedPorts" in cfg and isinstance(cfg["ExposedPorts"], dict):
            for port in cfg["ExposedPorts"].keys():
                rows.append(("ExposedPort", str(port)))
        
        # Labels
        if "Labels" in cfg and isinstance(cfg["Labels"], dict):
            for key, val in cfg["Labels"].items():
                rows.append(("", f"{key}={val}"))
    
    # 3. History entries - combine date + created_by, skip empty_layer, no field label
    if "history" in config and isinstance(config["history"], list):
        for i, entry in enumerate(config["history"]):
            if not isinstance(entry, dict):
                continue
            
            created = entry.get("created", "")
            created_by = entry.get("created_by", "")
            
            # Format: MM-DD-YYYY - command (no field label, just the value)
            date_str = format_history_date(created)
            if date_str and created_by:
                rows.append(("", f"{date_str} - {created_by}"))
            elif created_by:
                rows.append(("", created_by))
            elif date_str:
                rows.append(("", date_str))
    
    # 4. rootfs.type and rootfs.diff_ids
    if "rootfs" in config and isinstance(config["rootfs"], dict):
        rootfs = config["rootfs"]
        if "type" in rootfs:
            rows.append(("rootfs.type", str(rootfs["type"])))
        if "diff_ids" in rootfs and isinstance(rootfs["diff_ids"], list):
            for i, diff_id in enumerate(rootfs["diff_ids"]):
                rows.append((f"rootfs.diff_ids[{i}]", str(diff_id)))
    
    return rows


def parse_slug(slug: str) -> tuple[str, str]:
    """Extract namespace and repo from slug.
    
    Args:
        slug: Repository slug like 'library/nginx' or 'username/reponame'
        
    Returns:
        Tuple of (namespace, repo)
    """
    parts = slug.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    # Handle single-part slugs - assume 'library' namespace
    return "library", parts[0]
