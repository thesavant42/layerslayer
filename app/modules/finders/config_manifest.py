"""
Image config manifest fetching.

Retrieves the full configuration JSON for a container image,
including ENV, CMD, Entrypoint, WorkingDir, Labels, history, rootfs, etc.

Supports caching to SQLite to avoid redundant upstream requests.
"""

from typing import Optional
from app.modules.auth import RegistryAuth
from app.modules.keepers.storage import (
    init_database,
    get_cached_config,
    save_image_config,
)


def get_image_config(
    namespace: str,
    repo: str,
    tag: str,
    registry: str = "registry-1.docker.io",
    arch: Optional[str] = None,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict:
    """
    Fetch the full image configuration JSON for a container image.
    
    Handles both multi-arch manifest lists and single-arch manifests.
    Supports caching to SQLite database to avoid redundant upstream requests.
    
    Args:
        namespace: Docker Hub namespace (e.g., "library", "nginx")
        repo: Repository name (e.g., "nginx", "alpine")
        tag: Image tag (e.g., "latest", "v1")
        registry: Registry host (default: "registry-1.docker.io")
        arch: Target architecture for multi-arch images (e.g., "amd64", "arm64").
              If None, selects the first available platform.
        use_cache: If True, check database cache before fetching (default: True)
        force_refresh: If True, bypass cache and fetch fresh from registry (default: False)
    
    Returns:
        Full config blob as dict containing architecture, os, config.Env,
        config.Cmd, config.Entrypoint, config.WorkingDir, config.Labels,
        history, rootfs, etc.
    
    Raises:
        requests.RequestException: On network/HTTP errors
        ValueError: If manifest structure is unexpected
    """
    # Determine effective arch for cache lookup
    effective_arch = arch or "amd64"
    
    # Check cache first (unless disabled or force refresh)
    if use_cache and not force_refresh:
        conn = init_database()
        try:
            cached = get_cached_config(conn, namespace, repo, tag, effective_arch)
            if cached:
                return cached["config_json"]
        finally:
            conn.close()
    
    # Fetch from registry
    config_json, config_digest, layer_digests, layer_sizes = _fetch_config_from_registry(
        namespace=namespace,
        repo=repo,
        tag=tag,
        registry=registry,
        arch=arch,
    )
    
    # Cache the result
    if use_cache:
        conn = init_database()
        try:
            save_image_config(
                conn=conn,
                config_digest=config_digest,
                owner=namespace,
                repo=repo,
                tag=tag,
                config_json=config_json,
                layer_digests=layer_digests,
                layer_sizes=layer_sizes,
                arch=effective_arch,
            )
        finally:
            conn.close()
    
    return config_json


def _fetch_config_from_registry(
    namespace: str,
    repo: str,
    tag: str,
    registry: str = "registry-1.docker.io",
    arch: Optional[str] = None,
) -> tuple[dict, str, list[str], list[int]]:
    """
    Fetch image config from registry (internal, no caching).
    
    Returns:
        Tuple of (config_json, config_digest, layer_digests, layer_sizes)
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
        
        # Extract layer digests and sizes from manifest
        layer_digests = []
        layer_sizes = []
        for layer in manifest_data.get("layers", []):
            layer_digests.append(layer.get("digest", ""))
            layer_sizes.append(layer.get("size", 0))
        
        # Fetch the config blob
        resp = auth.request_with_retry("GET", f"{base_url}/blobs/{config_digest}")
        resp.raise_for_status()
        config_json = resp.json()
        
        return config_json, config_digest, layer_digests, layer_sizes
    
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
