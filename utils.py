# utils.py
#  Layerslayer utilities

import os


## formatter for file size human readability

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


## Parse the docker.io registry base (private registries use registry-raider.py)

def registry_base_url(user, repo):
    return f"https://registry-1.docker.io/v2/{user}/{repo}"


## Auth Management

## create an authenticated header
def auth_headers(token=None):
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers



## function to manage readaing the jwt 
def load_token(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return f.read().strip()
    return None

## function to manage writing the jwt 
def save_token(token, filename="token.txt"):
    with open(filename, "w") as f:
        f.write(token)
