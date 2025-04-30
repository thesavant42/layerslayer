# fetcher.py
# 🛡️ Layerslayer registry fetch helpers with Basic-or-Bearer logic

import os
import io
import base64
import requests
import tarfile
from utils import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
    save_token,
)

# Persistent session for registry calls
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
})

def _set_auth_header(token: str):
    """
    If token contains a colon, treat as Basic (username:pat).
    Otherwise treat as Bearer.
    """
    if not token:
        session.headers.pop("Authorization", None)
    elif ":" in token:
        # Basic auth: base64-encode "username:pat"
        b64 = base64.b64encode(token.encode()).decode()
        session.headers["Authorization"] = f"Basic {b64}"
    else:
        # Bearer (e.g. JWT)
        session.headers["Authorization"] = f"Bearer {token}"

def fetch_pull_token(user, repo):
    """
    Only used when doing Bearer/JWT flows.
    Fetches a pull-token from auth.docker.io, then installs it as a Bearer header.
    """
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{user}/{repo}:pull"
    )
    # Bypass session here – don't inherit Accept/Authorization
    resp = requests.get(auth_url)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"⚠️ Warning: pull-token endpoint error: {e}")
        return None

    token = resp.json().get("token")
    if not token:
        print("⚠️ Warning: token endpoint returned no token")
        return None

    save_token(token, filename="token_pull.txt")
    print("💾 Saved pull token to token_pull.txt.")
    _set_auth_header(token)
    return token

def get_manifest(image_ref, token=None, specific_digest=None):
    """
    Fetch multi-arch manifest list or single-arch manifest.
    Uses Basic if token contains ":", otherwise Bearer+refresh flow.
    """
    user, repo, tag = parse_image_ref(image_ref)
    ref = specific_digest or tag
    url = f"{registry_base_url(user, repo)}/manifests/{ref}"

    # Apply the provided token (Basic or Bearer)
    _set_auth_header(token or "")

    resp = session.get(url)
    if resp.status_code == 401 and (token and ":" not in token):
        # Bearer flow: try refreshing
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)

    if resp.status_code == 401:
        # Still unauthorized
        print(f"❌ Error: Unauthorized fetching manifest for {image_ref}.")
        print("   • Check that your credentials in token.txt are correct.")
        raise SystemExit(1)

    resp.raise_for_status()
    return resp.json()

def fetch_build_steps(image_ref, config_digest, token=None):
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{config_digest}"

    _set_auth_header(token or "")
    resp = session.get(url)
    if resp.status_code == 401 and (token and ":" not in token):
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)

    resp.raise_for_status()
    config = resp.json()

    steps = []
    for entry in config.get("history", []):
        step = entry.get("created_by", "").strip()
        if entry.get("empty_layer", False):
            step += " (metadata only)"
        steps.append(step)
    return steps

def download_layer_blob(image_ref, digest, size, token=None):
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    _set_auth_header(token or "")
    resp = session.get(url, stream=True)
    if resp.status_code == 401 and (token and ":" not in token):
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)

    resp.raise_for_status()

    out_dir = os.path.join("downloads", f"{user}_{repo}", "latest")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, digest.replace(":", "_") + ".tar.gz")

    with open(path, "wb") as f:
        for chunk in resp.iter_content(8192):
            if chunk:
                f.write(chunk)
    print(f"✅ Saved layer {digest} to {path}")

def peek_layer_blob(image_ref, digest, token=None):
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    _set_auth_header(token or "")
    resp = session.get(url, stream=True)
    if resp.status_code == 401 and (token and ":" not in token):
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)

    resp.raise_for_status()

    data = io.BytesIO(resp.content)
    with tarfile.open(fileobj=data, mode="r:gz") as tar:
        print("\n📦 Layer contents:\n")
        for m in tar.getmembers():
            if m.isdir():
                print(f"📂 {m.name}/")
            else:
                print(f"  📄 {m.name} ({human_readable_size(m.size)})")
