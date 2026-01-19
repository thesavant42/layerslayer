"""
Image config manifest fetching.

Retrieves the full configuration JSON for a container image,
including ENV, CMD, Entrypoint, WorkingDir, Labels, history, rootfs, etc.
"""

from typing import Optional
from app.modules.auth import RegistryAuth


def get_image_config(
    namespace: str,
    repo: str,
    tag: str,
    registry: str = "registry-1.docker.io",
    arch: Optional[str] = None,
) -> dict:
    """
    Fetch the full image configuration JSON for a container image.
    
    Handles both multi-arch manifest lists and single-arch manifests.
    
    Args:
        namespace: Docker Hub namespace (e.g., "library", "nginx")
        repo: Repository name (e.g., "nginx", "alpine")
        tag: Image tag (e.g., "latest", "v1")
        registry: Registry host (default: "registry-1.docker.io")
        arch: Target architecture for multi-arch images (e.g., "amd64", "arm64").
              If None, selects the first available platform.
    
    Returns:
        Full config blob as dict containing architecture, os, config.Env,
        config.Cmd, config.Entrypoint, config.WorkingDir, config.Labels,
        history, rootfs, etc.
    
    Raises:
        requests.RequestException: On network/HTTP errors
        ValueError: If manifest structure is unexpected
    """
    auth = RegistryAuth(namespace, repo)
    base_url = f"https://{registry}/v2/{namespace}/{repo}"
    
    try:
        # Fetch whatever the tag points to (index OR manifest)
        resp = auth.request_with_retry("GET", f"{base_url}/manifests/{tag}")
        resp.raise_for_status()
        manifest_data = resp.json()
        
        # CASE 1: Multi-arch index (has "manifests" key)
        if "manifests" in manifest_data:
            platform_manifest = _select_platform(manifest_data["manifests"], arch)
            if platform_manifest is None:
                raise ValueError(f"No matching platform found for arch={arch}")
            
            digest = platform_manifest["digest"]
            
            # Fetch platform-specific manifest
            resp = auth.request_with_retry("GET", f"{base_url}/manifests/{digest}")
            resp.raise_for_status()
            manifest_data = resp.json()
        
        # CASE 2: Single-arch manifest (or resolved from multi-arch above)
        # Extract config digest and fetch the config blob
        if "config" not in manifest_data:
            raise ValueError("Manifest does not contain 'config' key")
        
        config_digest = manifest_data["config"]["digest"]
        resp = auth.request_with_retry("GET", f"{base_url}/blobs/{config_digest}")
        resp.raise_for_status()
        
        return resp.json()
    
    finally:
        auth.invalidate()


def _select_platform(manifests: list, arch: Optional[str]) -> Optional[dict]:
    """
    Select a platform manifest from a multi-arch manifest list.
    
    Args:
        manifests: List of platform manifests from the index
        arch: Target architecture (e.g., "amd64", "arm64").
              If None, returns the first manifest.
    
    Returns:
        The matching manifest dict, or None if no match found.
    """
    if not manifests:
        return None
    
    if arch is None:
        return manifests[0]
    
    # Find matching architecture
    for m in manifests:
        platform = m.get("platform", {})
        if platform.get("architecture") == arch:
            return m
    
    return None
