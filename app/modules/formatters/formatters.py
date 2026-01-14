

#========= FORMATTER
def _tarinfo_mode_to_string(mode: int, typeflag: str) -> str:
    """Convert tarfile mode integer to ls-style permission string."""
    type_char = {'5': 'd', '2': 'l', '0': '-'}.get(typeflag, '-')
    
    perms = ''
    for shift in [6, 3, 0]:
        bits = (mode >> shift) & 0o7
        perms += 'r' if bits & 4 else '-'
        perms += 'w' if bits & 2 else '-'
        perms += 'x' if bits & 1 else '-'
    
    return type_char + perms

#========= FORMATTER
def _format_mtime(unix_timestamp: int) -> str:
    """Format Unix timestamp to readable string."""
    from datetime import datetime
    try:
        if unix_timestamp <= 0:
            return "----.--.-- --:--"
        dt = datetime.fromtimestamp(unix_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return "----.--.-- --:--"

