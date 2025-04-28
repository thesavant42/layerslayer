# fetcher.py
# Handles HTTP requests to registry + peeking layers + fetching build steps

import requests
import os
import io
import tarfile
import json
import time
from utils import parse_image_ref, registry_base_url, auth_headers, human_readable_size

TOKEN_FILE = "token_pull.txt"
TOKEN_EXPIRY_SECONDS = 300  # Assume 5 minutes safe expiry

session_token = None  # Updated dynamically

def load_cached_token():
    """Load a cached pull token if fresh."""
    if not os.path.exists(TOKEN_FILE):
        return None

    mtime = os.path.getmtime(TOKEN_FILE)
    if (time.time() - mtime) > TOKEN_EXPIRY_SECONDS:
        print("⚡ Cached token expired, fetching new one...")
        return None

    with open(TOKEN_FILE, 'r') as f:
        token = f.read().strip()
        if token:
            print("🔑 Loaded cached pull token from token_pull.txt.")
            return token
    return None

def save_token(token):
    """Save pull token to disk."""
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    print("💾 Saved pull token to token_pull.txt.")

def get_manifest(image_ref, token=None):
    """Fetches the manifest for a given image ref."""
    global session_token
    token = token or session_token

    repo, tag = parse_image_ref(image_ref)
    url = f"{registry_base_url()}/{repo}/manifests/{tag}"
    headers = auth_headers(token)
    headers['Accept'] = 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json'

    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_anonymous_token(repo)
        session_token = token  # Update session
        headers = auth_headers(token)
        headers['Accept'] = 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json'
        resp = requests.get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()

def get_manifest_by_digest(image_ref, digest, token=None):
    """Fetches a manifest by specific digest (for a platform-specific image)."""
    global session_token
    token = token or session_token

    repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url()}/{repo}/manifests/{digest}"
    headers = auth_headers(token)
    headers['Accept'] = 'application/vnd.docker.distribution.manifest.v2+json'

    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_anonymous_token(repo)
        session_token = token
        headers = auth_headers(token)
        headers['Accept'] = 'application/vnd.docker.distribution.manifest.v2+json'
        resp = requests.get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()

def download_layer_blob(image_ref, digest, token=None, output_dir="downloads"):
    """Downloads a layer blob (.tar.gz) from the registry."""
    global session_token
    token = token or session_token

    repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url()}/{repo}/blobs/{digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_anonymous_token(repo)
        session_token = token
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers, stream=True)

    resp.raise_for_status()

    filename = digest.replace(':', '_') + '.tar.gz'
    path = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    with open(path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"✅ Saved layer {digest} to {path}")

def peek_layer_blob(image_ref, digest, token=None):
    """Streams a layer blob and lists files/folders in tree view."""
    global session_token
    token = token or session_token

    repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url()}/{repo}/blobs/{digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_anonymous_token(repo)
        session_token = token
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers, stream=True)

    resp.raise_for_status()

    buffer = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=8192):
        buffer.write(chunk)

    buffer.seek(0)

    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        files = []

        for member in tar.getmembers():
            files.append((member.name, member.isdir(), member.size))

        files.sort()

        print("\n📦 Layer contents:\n")
        for path, is_dir, size in files:
            parts = path.strip('/').split('/')
            indent = '  ' * (len(parts) - 1)
            name = parts[-1]
            if is_dir:
                print(f"{indent}📂 {name}/")
            else:
                readable_size = human_readable_size(size)
                print(f"{indent}📄 {name} ({readable_size})")

def fetch_build_steps(image_ref, config_digest, token=None):
    """Fetches the config blob and extracts Dockerfile build steps."""
    global session_token
    token = token or session_token

    repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url()}/{repo}/blobs/{config_digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_anonymous_token(repo)
        session_token = token
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers, stream=True)

    resp.raise_for_status()

    config_data = resp.json()
    history = config_data.get('history', [])

    if not history:
        print("⚠️ No build history found in config.")
        return

    print("\n🛠️  Build Steps (Dockerfile Commands):\n----------------------------------------")
    for idx, entry in enumerate(history):
        created_by = entry.get('created_by', '').strip()
        empty_layer = entry.get('empty_layer', False)

        if created_by:
            flag = "(metadata only)" if empty_layer else ""
            print(f"Step {idx}: {created_by} {flag}")
    print("----------------------------------------\n")

def fetch_anonymous_token(repo):
    """Fetches an anonymous Bearer token for pulling public Docker images."""
    service = "registry.docker.io"
    scope = f"repository:{repo}:pull"
    auth_url = f"https://auth.docker.io/token?service={service}&scope={scope}"

    resp = requests.get(auth_url)
    resp.raise_for_status()

    token = resp.json().get('token')
    if not token:
        raise Exception("Failed to retrieve anonymous pull token.")

    save_token(token)
    print("🔑 Retrieved and saved anonymous pull token.")
    return token
