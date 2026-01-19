# This script generated the json at [container-image-config\container-image-config.json](container-image-config\container-image-config.json)

import requests, json

repo = "drichnerdisney/ollama"
tag = "v1"

# begin auth
## this is far ore straightforward, compared to what's currently implemented
token = requests.get(
    "https://auth.docker.io/token",
    params={"service": "registry.docker.io", "scope": f"repository:{repo}:pull"},
).json()["token"]

headers = {"Authorization": f"Bearer {token}"}
# end auth




# fetch whatever the tag points to (index OR manifest)
resp = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
    headers=headers,
).json()

# CASE 1: multi-arch index
if "manifests" in resp:
    # pick first platform (or choose by arch) TODO this should be an argument we can influece as a user
    digest = resp["manifests"][0]["digest"]

# CASE 2: single-arch manifest
else:
    digest = resp["config"]["digest"]  # this is the config blob digest
    # but we still need the manifest to get layers
    manifest = resp
    config = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}",
        headers=headers,
    ).json()
    print(json.dumps(config, indent=2))
    exit()

# fetch platform-specific manifest
manifest = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/manifests/{digest}",
    headers=headers,
).json()

# fetch config blob
config_digest = manifest["config"]["digest"]
config = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/blobs/{config_digest}",
    headers=headers,
).json()

print(json.dumps(config, indent=2))