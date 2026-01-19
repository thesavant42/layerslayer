import os
from app.modules.formatters import parse_image_ref, registry_base_url
from app.modules.auth import RegistryAuth

# =============================================================================
# Layer Download (Full)
# =============================================================================

def download_layer_blob(auth: RegistryAuth, image_ref: str, digest: str, size: int):
    """
    Stream a layer blob to disk as a .tar.gz file.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:alpine")
        digest: Layer digest
        size: Layer size (for info only)
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{digest}"

    resp = auth.request_with_retry("GET", url, stream=True)
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

    print(f"[+] Saved layer {digest} to {path}")


# =============================================================================
# Manifest & Config Fetching
# =============================================================================

def get_manifest(auth: RegistryAuth, image_ref: str, specific_digest: str = None):
    """
    Fetch either a multi-arch manifest list or a single-arch manifest.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:alpine")
        specific_digest: Optional digest to fetch instead of tag
        
    Returns:
        Manifest as dict
    """
    user, repo, tag = parse_image_ref(image_ref)
    ref = specific_digest or tag
    url = f"{registry_base_url(user, repo)}/manifests/{ref}"

    resp = auth.request_with_retry("GET", url)

    if resp.status_code == 401:
        # Final unauthorized -> clean exit
        print(f"X Error: Unauthorized fetching manifest for {image_ref}.")
        print("   - Ensure the image exists and is accessible.")
        raise SystemExit(1)

    resp.raise_for_status()
    return resp.json()


def fetch_build_steps(auth: RegistryAuth, image_ref: str, config_digest: str):
    """
    Download the image config blob and parse Dockerfile 'created_by' history.
    
    Args:
        auth: RegistryAuth instance for authenticated requests
        image_ref: Image reference (e.g., "nginx:alpine")
        config_digest: Config blob digest
        
    Returns:
        List of build step strings
    """
    user, repo, _ = parse_image_ref(image_ref)
    url = f"{registry_base_url(user, repo)}/blobs/{config_digest}"

    resp = auth.request_with_retry("GET", url)
    resp.raise_for_status()
    config = resp.json()

    steps = []
    for entry in config.get("history", []):
        step = entry.get("created_by", "").strip()
        if entry.get("empty_layer", False):
            step += " (metadata only)"
        steps.append(step)
    return steps
