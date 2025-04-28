# utils.py
# Helper functions for Layerslayer

import os

def parse_image_ref(image_ref):
    """Parses an image ref like 'moby/buildkit:latest'."""
    if ':' not in image_ref:
        raise ValueError("Image reference must include tag (e.g., user/repo:tag)")
    name, tag = image_ref.split(':', 1)
    if '/' not in name:
        # If no namespace is given, assume "library/"
        full_repo = f"library/{name}"
    else:
        full_repo = name
    return full_repo, tag

def registry_base_url():
    """Returns the base URL for Docker Hub."""
    return "https://registry-1.docker.io/v2"

def auth_headers(token):
    """Returns Authorization header if token is provided."""
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    return headers

def ensure_download_dir(image_ref):
    """Ensures a structured download directory exists."""
    full_repo, tag = parse_image_ref(image_ref)
    path = os.path.join('downloads', full_repo.replace('/', '_'), tag)
    os.makedirs(path, exist_ok=True)
    return path

def load_token():
    """Loads token from token.txt if available."""
    if os.path.exists('token.txt'):
        with open('token.txt', 'r') as f:
            token = f.read().strip()
        if token:
            print("🔑 Loaded token from token.txt")
            return token
    return None

def select_from_list(items):
    """Prompts the user to select indexes from a list."""
    choice = input("\nSelect layer indexes to download (e.g., 0,2,3) or ALL: ").strip()
    if choice.lower() == 'all':
        return items
    indexes = [int(x.strip()) for x in choice.split(',') if x.strip().isdigit()]
    selected = [items[i] for i in indexes if 0 <= i < len(items)]
    return selected

def human_readable_size(size, decimal_places=1):
    """Converts bytes into a human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024
    return f"{size:.{decimal_places}f} PB"
