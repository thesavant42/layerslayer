# utils.py
#  Layerslayer utilities

import os

## TODO Move to app\modules\formatters\formatters.py
## formatter for file size human readability

def human_readable_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

## TODO app\modules\formatters\formatters.py
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

