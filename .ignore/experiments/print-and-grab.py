import requests

repo = "library/ubuntu"
tag = "latest"

# 1. Get repo-scoped token
token = requests.get(
    "https://auth.docker.io/token",
    params={"service": "registry.docker.io", "scope": f"repository:{repo}:pull"},
).json()["token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.oci.image.manifest.v1+json",
}

# 2. Fetch top-level manifest (may be an OCI index)
index = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
    headers=headers,
).json()

print("=== OCI INDEX ===")
print(index)

# 3. If it's an index, resolve the first manifest entry
if "manifests" in index:
    digest = index["manifests"][0]["digest"]
    manifest = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{digest}",
        headers=headers,
    ).json()
else:
    manifest = index

print("\n=== IMAGE MANIFEST ===")
print(manifest)

# 4. Extract first layer digest
layer_digest = manifest["layers"][0]["digest"]

# 5. Download the layer blob
blob = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/blobs/{layer_digest}",
    headers={"Authorization": f"Bearer {token}"},
).content

print("\nLayer digest:", layer_digest)
print("Downloaded bytes:", len(blob))