# fetcher.py
# 🛡️ Layerslayer registry fetch helpers

import os
import requests
import tarfile
import io
from utils import (
    parse_image_ref,
    registry_base_url,
    auth_headers,
    human_readable_size,
    save_token,
)

def get_manifest(image_ref, token=None, specific_digest=None):
    user, repo, tag = parse_image_ref(image_ref)
    ref = specific_digest if specific_digest else tag
    url = f"{registry_base_url(user, repo)}/manifests/{ref}"

    headers = auth_headers(token)

    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_pull_token(user, repo)
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def fetch_pull_token(user, repo):
    auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{user}/{repo}:pull"
    resp = requests.get(auth_url)
    resp.raise_for_status()
    token = resp.json().get("token")
    if token:
        save_token(token, filename="token_pull.txt")
        print("💾 Saved pull token to token_pull.txt.")
    return token

def fetch_build_steps(image_ref, config_digest, token=None):
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{config_digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_pull_token(user, repo)
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers)

    resp.raise_for_status()
    config = resp.json()
    steps = []
    history = config.get("history", [])
    for entry in history:
        created_by = entry.get("created_by", "")
        if entry.get("empty_layer", False):
            created_by += " (metadata only)"
        steps.append(created_by.strip())
    return steps

def download_layer_blob(image_ref, digest, size, token=None):
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_pull_token(user, repo)
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers, stream=True)

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
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"
    headers = auth_headers(token)

    resp = requests.get(url, headers=headers, stream=True)
    if resp.status_code == 401:
        print("🔄 Unauthorized. Fetching fresh pull token...")
        token = fetch_pull_token(user, repo)
        headers = auth_headers(token)
        resp = requests.get(url, headers=headers, stream=True)

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
