# Manifest Download Function + API Expansion

## Summary
 
The file [plans\config-manifest-route\authed-image-config.py](plans\config-manifest-route\authed-image-config.py) was developed unrelated to this project, but it contains patterns that I would like to incorporate into this project.

 `authed-image-config.py` downloads the Build Configuration JSON of a {TAG} as a JSON object, with ENV variables, cmd instructions, the entry point, working dir, etc etc. LOTS of useful info. It does so with anonymous authentication and tested patterns. 

## Goal
I would like to extend the routes in [app/modules/api/](app/modules/api) to include a route to
 - utilize the new [shared authentication](app/modules/auth) 
    - to download the image configuration of a container image, given the {repo} and {tag}.

This function, given {repo} and {tag} will return the container's build config as a JSON object with all sorts of desired metadata. 

## User Story

As a researcher, the build config tells me a lot about which layers I want to focus a manual investigation on.
 The image could also serve as an index of sorts when constructing the virtual file system, as well as serve as structured data with which to populate a UI (tbd).
 - Full list of fields to be included in tbd UI : [container-image-config\container-image-config.md](container-image-config\container-image-config.md)

### Known shortcomings
- It currently hard-codes the containter registry address to `registry-1.docker.io`, I would like it to be a variable we can pass it, for maximum flexibility.

### Open Question
**QUESTION**
Question: - The Shared auth module in auth.py sets `registry.docker.io`, *not* `registry-1.docker.io` is that a problem?
Answer:


## TASK
- Create a new module under app\modules\finders\manifests
    - logic for downloading the manifests should live here and be reusable
    - requires {repo} {tag} {registry} default to `registry-1.docker.io`

## Acceptance Criteria

```python
# fetch whatever the tag points to (index OR manifest)
resp = requests.get(
    f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
    headers=headers,
).json()

# CASE 1: multi-arch index
if "manifests" in resp:
    # pick first platform (or choose by arch) TODO this should be an argument we can influece as a user!
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
```
