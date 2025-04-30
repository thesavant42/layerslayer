# fetcher.py
# 🛡️ Layerslayer registry fetch helpers with resilient token handling

import os
import requests
import tarfile
import io
from utils import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
    save_token,
)

# Persistent session to reuse headers & TCP connections for registry calls
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
})

def fetch_pull_token(user, repo):
    """
    Retrieve a Docker Hub pull token (anonymous or authenticated).
    Bypasses the shared session so no extra headers confuse the auth endpoint.
    """
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{user}/{repo}:pull"
    )
    try:
        # Use plain requests.get() here—no Accept or stale Auth headers
        resp = requests.get(auth_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️ Warning: pull-token endpoint error: {e}")
        return None

    token = resp.json().get("token")
    if not token:
        print("⚠️ Warning: token endpoint returned no token")
        return None

    save_token(token, filename="token_pull.txt")
    print("💾 Saved pull token to token_pull.txt.")
    # Now inject the fresh token into our session for all registry calls
    session.headers["Authorization"] = f"Bearer {token}"
    return token

def get_manifest(image_ref, token=None, specific_digest=None):
    """
    Fetch either a multi-arch manifest list or a single-arch manifest.
    On 401, attempts one token refresh; if still 401, exits with a friendly message.
    """
    user, repo, tag = parse_image_ref(image_ref)
    ref = specific_digest or tag
    url = f"{registry_base_url(user, repo)}/manifests/{ref}"

    # If caller provided a token, set it before the request
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    resp = session.get(url)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)
        else:
            print("⚠️ Proceeding without refreshed token.")

    if resp.status_code == 401:
        # Final unauthorized → clean exit
        print(f"❌ Error: Unauthorized fetching manifest for {image_ref}.")
        print("   • Ensure the image exists and token.txt (if used) is valid.")
        raise SystemExit(1)

    resp.raise_for_status()
    return resp.json()

def fetch_build_steps(image_ref, config_digest, token=None):
    """
    Download the image config blob and parse Dockerfile 'created_by' history.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{config_digest}"

    resp = session.get(url)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url)
        else:
            print("⚠️ Proceeding without refreshed token.")

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
    """
    Stream a layer blob to disk as a .tar.gz file.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print("⚠️ Proceeding without refreshed token.")

    resp.raise_for_status()

    user_repo = f"{user}_{repo}"
    output_dir = os.path.join("downloads", user_repo, "latest")
    os.makedirs(output_dir, exist_ok=True)

    filename = digest.replace(":", "_") + ".tar.gz"
    path = os.path.join(output_dir, filename)

    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"✅ Saved layer {digest} to {path}")

def peek_layer_blob(image_ref, digest, token=None):
    """
    Download a layer blob into memory and list its contents.
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = session.get(url, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        new_token = fetch_pull_token(user, repo)
        if new_token:
            resp = session.get(url, stream=True)
        else:
            print("⚠️ Proceeding without refreshed token.")

    resp.raise_for_status()

    tar_bytes = io.BytesIO(resp.content)
    with tarfile.open(fileobj=tar_bytes, mode="r:gz") as tar:
        print("\n📦 Layer contents:\n")
        for member in tar.getmembers():
            if member.isdir():
                print(f"📂 {member.name}/")
            else:
                size = human_readable_size(member.size)
                print(f"  📄 {member.name} ({size})")
