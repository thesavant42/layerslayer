

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


def human_readable_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

## Handle use cases involving library containers

def parse_image_ref(image_ref):
    if ":" in image_ref:
        repo, tag = image_ref.split(":")
    else:
        repo = image_ref
        tag = "latest"
    if "/" in repo:
        user, repo = repo.split("/", 1)
    else:
        user = "library"
    return user, repo, tag


## Parse the docker.io registry base (TODO: enable private registires, private registries must use registry-raider.py)

def registry_base_url(user, repo):
    return f"https://registry-1.docker.io/v2/{user}/{repo}"

