import requests

repo = "library/ubuntu"
tag = "latest"

# token
token = requests.get(
    "https://auth.docker.io/token",
    params={"service": "registry.docker.io", "scope": f"repository:{repo}:pull"},
).json()["token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.oci.image.manifest.v1+json",
}

# fetch index or manifest
index = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
    headers=headers,
).json()

# resolve platform manifest if needed
if "manifests" in index:
    digest = index["manifests"][0]["digest"]
    manifest = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{digest}",
        headers=headers,
    ).json()
else:
    manifest = index

print("=== IMAGE MANIFEST ===")
print(manifest)

# --- NEW PART: fetch config JSON ---
config_digest = manifest["config"]["digest"]

config = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/blobs/{config_digest}",
    headers={"Authorization": f"Bearer {token}"},
).json()

print("\n=== CONFIG JSON (Dockerfile instructions, env, entrypoint, etc.) ===")
print(config)