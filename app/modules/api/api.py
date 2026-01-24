import sys
import re
import importlib.util
from io import StringIO
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse, Response, StreamingResponse
import httpx
import requests
import fastapi_swagger_dark as fsd

# Import main module
import main

# Import image config fetcher
from app.modules.finders import get_image_config

# Import search module
from app.modules.search import search_dockerhub

# Import storage module for history queries and config caching
from app.modules.keepers.storage import (
    init_database,
    get_history,
    VALID_SORTBY_COLUMNS,
    get_layer_status,
    get_cached_config,
    update_layer_peeked,
)

# Import carver for file extraction
from app.modules.keepers.carver import carve_file_to_bytes

# Import auth and formatters for layer streaming
from app.modules.auth import RegistryAuth
from app.modules.formatters import parse_image_ref, registry_base_url

# Import fs-log-sqlite module using importlib (due to hyphen in filename)
spec = importlib.util.spec_from_file_location("fs_log_sqlite", "app/modules/fs-log-sqlite.py")
fs_log_sqlite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs_log_sqlite)

app = FastAPI(
    title="Docker Dorker API", 
    docs_url=None,
    description="""
**Docker Dorker API**
* WIP
* TBD    
    """,
    version="1.0.0"
    )

# Create a router for the dark docs
router = APIRouter()

# Install dark theme on the router
fsd.install(router)

# Include the router in the app
app.include_router(router)

# Validate image reference format to prevent injection
IMAGE_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*/[a-zA-Z0-9][a-zA-Z0-9_-]*(:[a-zA-Z0-9_-]+)?$')



@app.get("/search.data", response_class=PlainTextResponse)
async def search_data(
    q: str = Query(..., description="Search query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    sortby: str = Query(default="updated_at", description="Sort field: pull_count or updated_at"),
    order: str = Query(default="desc", description="Sort order: asc or desc")
):
    """
    ## /search.data
    
    Search Docker Hub for images, users, and organizations.
    
    - Returns formatted text table with search results.
    
    - Example: `/search.data?q=nginx&page=1&sortby=pull_count&order=desc`
    """
    # Validate sortby
    if sortby not in ['pull_count', 'updated_at']:
        raise HTTPException(
            status_code=400,
            detail="sortby must be 'pull_count' or 'updated_at'"
        )
    
    # Validate order
    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'"
        )
    
    try:
        result = await search_dockerhub(
            query=q,
            page=page,
            sortby=sortby,
            order=order
        )
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Docker Hub API error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to Docker Hub: {str(e)}"
        )


@app.get("/history", response_class=PlainTextResponse)
def history(
    q: str = Query(default=None, description="Filter by owner, repo, or tag"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=30, ge=1, le=100, description="Results per page"),
    sortby: str = Query(default="scraped_at", description="Column to sort by"),
    order: str = Query(default="desc", description="Sort order: asc or desc")
):
    """
    ## /history
    
    List cached scan results from the database.
    
    - Returns formatted text table with previously peeked layers.
    
    - Example: `/history?q=nginx&page=1&page_size=30&sortby=scraped_at&order=desc`
    
    """
    
    # Validate sortby
    if sortby not in VALID_SORTBY_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"sortby must be one of: {', '.join(sorted(VALID_SORTBY_COLUMNS))}"
        )
    
    # Validate order
    if order not in ['asc', 'desc']:
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'"
        )
    
    # Query database
    conn = init_database()
    try:
        rows = get_history(
            conn=conn,
            q=q,
            page=page,
            page_size=page_size,
            sortby=sortby,
            order=order
        )
    finally:
        conn.close()
    
    # Format output as text table
    # Column widths: scraped_at(12), owner(<25), repo(<25), tag(<20), layer_index(<4), layer_size
    header = f"{'scraped_at':<12} | {'owner':<25} | {'repo':<25} | {'tag':<20} | {'idx':<4} | {'layer_size':>12}"
    separator = f"{'-'*12}-+-{'-'*25}-+-{'-'*25}-+-{'-'*20}-+-{'-'*4}-+-{'-'*12}"
    
    lines = [header, separator]
    
    for row in rows:
        # Truncate long strings
        scraped_at = str(row.get('scraped_at', ''))[:10]
        owner = str(row.get('owner', ''))[:25]
        repo = str(row.get('repo', ''))[:25]
        tag = str(row.get('tag', ''))[:20]
        layer_index = str(row.get('layer_index', ''))
        layer_size = row.get('layer_size', 0) or 0
        
        lines.append(
            f"{scraped_at:<12} | {owner:<25} | {repo:<25} | {tag:<20} | {layer_index:<4} | {layer_size:>12}"
        )
    
    return "\n".join(lines)


@app.get("/fslog", response_class=PlainTextResponse)
def fslog(image: str, path: str, layer: int = Query(default=None)):
    """
    ## /fslog
    
    Browse filesystem logs for a Docker image layer.
    
    """
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        if layer is not None:
            sys.argv = ["fs-log-sqlite.py", image, str(layer), path, "--single-layer"]
        else:
            sys.argv = ["fs-log-sqlite.py", image, path]
        fs_log_sqlite.main()
    except SystemExit:
        pass  # fs-log-sqlite calls sys.exit() for empty results
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


@app.get("/fslog-search", response_class=PlainTextResponse)
def fslog_search(q: str, image: str = Query(default=None), layer: int = Query(default=None)):
    """
    ## /fslog-search
    
    Search filesystem logs for files matching a pattern.
    
    """
    if image and not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        sys.argv = ["fs-log-sqlite.py", "--search", q]
        if image:
            sys.argv.append(image)
            if layer is not None:
                sys.argv.append(str(layer))
        fs_log_sqlite.main()
    except SystemExit:
        pass  # fs-log-sqlite calls sys.exit() for empty results
    finally:
        sys.stdout = old_stdout
    
    return captured_output.getvalue()


@app.get("/repositories")
async def repositories(
    namespace: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None)
):
    """
    ## /repositories
    
    
    Pass-through proxy for Docker Hub's /v2/repositories API.
    
    - Returns the upstream JSON response verbatim.

    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}"
    params = {}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


@app.get("/repositories/{namespace}/{repo}/tags")
async def repository_tags(
    namespace: str,
    repo: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None),
    ordering: str = Query(default="last_updated")
):
    """
    ## /tags
    
    Pass-through proxy for Docker Hub's repository tags API.
    
    - Returns the upstream JSON response verbatim.
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags"
    params = {"ordering": ordering}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


@app.get("/repositories/{namespace}/{repo}/tags/{tag}/images")
async def repository_tag_images(
    namespace: str,
    repo: str,
    tag: str,
    page: int = Query(default=None),
    page_size: int = Query(default=None),
    ordering: str = Query(default="last_updated")
):
    """
    ## Images 
    
    Pass-through proxy for Docker Hub's repository tag images API.
    
    - Returns the upstream JSON response verbatim.
    - 
     
    """
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags/{tag}/images"
    params = {"ordering": ordering}
    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["page_size"] = page_size
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return JSONResponse(content=response.json(), status_code=200)


@app.get("/repositories/{namespace}/{repo}/tags/{tag}/config")
def get_tag_config(
    namespace: str,
    repo: str,
    tag: str,
    arch: str = Query(default=None, description="Target architecture: amd64, arm64, etc."),
    force_refresh: bool = Query(default=False, description="Bypass cache and fetch fresh from registry"),
):
    """
    ## Get Image Build Config
    
    Fetch the full image configuration JSON for a tagged image.
    
    - Configs are cached in SQLite to avoid redundant upstream requests
    - Use `force_refresh=true` to bypass cache and fetch fresh data
    
    - Returns useful OSINT metadata:
        - environment variables
        - entrypoint
        - 'cmd' history
        - working directory
        - labels
        - build history
        - and other image metadata
    """
    try:
        config = get_image_config(
            namespace=namespace,
            repo=repo,
            tag=tag,
            arch=arch,
            force_refresh=force_refresh,
        )
        return JSONResponse(content=config, status_code=200)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Registry request failed: {e}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/peek/status")
def peek_status(
    image: str = Query(..., description="Image reference: namespace/repo:tag"),
    arch: str = Query(default="amd64", description="Target architecture: amd64, arm64, etc."),
):
    """
    ## Peek Status
    
    Get layer peek status for an image without triggering a peek.
    
    Returns:
    - Whether config is cached
    - Layer count
    - List of layers with idx, digest, size, and peek status
    - Count of peeked vs unpeeked layers
    
    Use this endpoint to:
    - Check how many layers an image has before peeking
    - See which layers have already been peeked
    - Get the idx-to-digest mapping for precise operations
    
    Example: `/peek/status?image=nginx/nginx:alpine`
    """
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # Parse image reference
    namespace, repo, tag = parse_image_ref(image)
    
    # Query database for layer status
    conn = init_database()
    try:
        status = get_layer_status(conn, namespace, repo, tag, arch)
        
        if status is None:
            # Config not cached - need to fetch it first
            # Try to get config (which will cache it)
            try:
                get_image_config(
                    namespace=namespace,
                    repo=repo,
                    tag=tag,
                    arch=arch,
                )
                # Now query again
                status = get_layer_status(conn, namespace, repo, tag, arch)
            except Exception as e:
                return JSONResponse(
                    content={
                        "image": image,
                        "config_cached": False,
                        "error": str(e),
                        "message": "Failed to fetch config from registry",
                    },
                    status_code=200,
                )
        
        if status:
            return JSONResponse(
                content={
                    "image": image,
                    **status,
                },
                status_code=200,
            )
        else:
            return JSONResponse(
                content={
                    "image": image,
                    "config_cached": False,
                    "message": "No cached config found",
                },
                status_code=200,
            )
    finally:
        conn.close()


@app.get("/peek")
def peek(
    image: str,
    layer: str = Query(default="all"),
    arch: int = Query(default=0),
    hide_build: bool = Query(default=False, description="Hide build steps output"),
    status_only: bool = Query(default=False, description="Return status JSON instead of peeking"),
):
    """
    ## /peek
    
    Scan headers of tar.gz layer image to infer filesystem,
    output is printed by UI as a simulated tty running `ls -la`
    
    ### CLI Equivalent
    
    `python main.py -t "{image}" --peek-layer={layer} --arch={arch} --force`
    
    - Args:
        - `image`: Image reference (e.g., "nginx/nginx:latest")
        - `layer`: Layer to peek - 'all' for all layers, or integer index for specific layer
        - `arch`: Platform index for multi-arch images
        - `hide_build`: If true, hide verbose build steps output
        - `status_only`: If true, return JSON status without triggering a peek (same as /peek/status)
    """
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # If status_only, redirect to peek_status logic
    if status_only:
        namespace, repo, tag = parse_image_ref(image)
        arch_str = "amd64"  # Default arch string for status lookup
        conn = init_database()
        try:
            status = get_layer_status(conn, namespace, repo, tag, arch_str)
            if status is None:
                try:
                    get_image_config(namespace=namespace, repo=repo, tag=tag, arch=arch_str)
                    status = get_layer_status(conn, namespace, repo, tag, arch_str)
                except Exception as e:
                    return JSONResponse(
                        content={"image": image, "config_cached": False, "error": str(e)},
                        status_code=200,
                    )
            return JSONResponse(
                content={"image": image, **(status or {"config_cached": False})},
                status_code=200,
            )
        finally:
            conn.close()
    
    # Parse image reference for tracking
    namespace, repo, tag = parse_image_ref(image)
    arch_str = "amd64"  # Default architecture
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Set argv as if called from CLI
        sys.argv = [
            "main.py",
            "-t", image,
            f"--peek-layer={layer}",
            f"--arch={arch}",
            "--force"
        ]
        if hide_build:
            sys.argv.append("--hide-build")
        
        # Call main directly
        main.main()
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    # Track which layers were peeked
    conn = init_database()
    try:
        if layer == "all":
            # Get layer count from cached config
            status = get_layer_status(conn, namespace, repo, tag, arch_str)
            if status and "layer_count" in status:
                for idx in range(status["layer_count"]):
                    update_layer_peeked(conn, namespace, repo, tag, arch_str, idx)
        else:
            # Single layer was peeked
            try:
                layer_idx = int(layer)
                update_layer_peeked(conn, namespace, repo, tag, arch_str, layer_idx)
            except ValueError:
                pass  # Invalid layer index, skip tracking
    finally:
        conn.close()
    
    return PlainTextResponse(captured_output.getvalue())


@app.get("/carve")
def carve(
    image: str,
    path: str = Query(..., description="File path in container, e.g., /etc/passwd"),
    layer: int = Query(..., description="Layer index to extract from (REQUIRED). Use /peek/status to discover layer indices."),
    as_text: bool = Query(default=False, description="Render as plain text in browser instead of downloading"),
):
    """
    ## Carve
    
    Carve a single file from a Docker image and return it as a browser download.
    
    - Uses HTTP Range requests to efficiently extract just the target file
    without downloading the entire layer.
    
    **IMPORTANT:** The `layer` parameter is REQUIRED. Use `/peek/status` to discover
    which layer(s) contain your target file before carving.
    
    ### Parameters
        
    - `image` : `nginx/nginx:alpine`
        - `namespace/repo:tag`
    - `path` : `/etc/passwd`
        - Absolute path of the remote file
    - `layer` : `0` (REQUIRED)
        - Layer index containing the file to carve
        - Use `/peek/status?image=...` to discover layer indices
        - Example: `/carve?image=nginx/nginx:alpine&path=/etc/passwd&layer=0`
    - `as_text` : `true`
        - Allows viewing the file in browser instead of saving to disk
        - Example: `/carve?image=nginx/nginx:alpine&path=/etc/passwd&layer=0&as_text=true`
    """
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    content, result = carve_file_to_bytes(image, path, layer_index=layer)
    
    if not result.found:
        detail = result.error or f"File not found: {path}"
        raise HTTPException(status_code=404, detail=detail)
    
    # Extract just the filename for Content-Disposition
    filename = Path(path).name
    
    # Guess content type based on extension
    ext = Path(path).suffix.lower()
    content_types = {
        ".json": "application/json",
        ".xml": "application/xml",
        ".txt": "text/plain",
        ".sh": "text/x-shellscript",
        ".py": "text/x-python",
        ".conf": "text/plain",
        ".cfg": "text/plain",
        ".ini": "text/plain",
        ".yml": "text/yaml",
        ".yaml": "text/yaml",
    }
    media_type = content_types.get(ext, "application/octet-stream")
    
    headers = {
        "Content-Length": str(len(content)),
    }

    if as_text:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers=headers,
        )

    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )


@app.get("/layer/download")
def download_layer(
    image: str,
    digest: str = Query(..., description="Layer digest, e.g., sha256:abc123..."),
):
    """
    ## Stream a layer
    
    Stream a layer blob directly to the browser as a download.
    
    - Acts as an authenticated proxy - fetches the layer from the registry
    and streams it directly to the browser without intermediate storage.
    
    Example: `/layer/download?image=nginx/nginx:alpine&digest=sha256:abc123...`
    
    ### Paramteters
        
    - `image` : `nginx/nginx:alpine`   
        - `namespace/repo:tag`
    - `digest` : `sha256:88885ce2e36df0fbb0f9313c53d9f5775f37385128b9818a5496806d59dd34e9`
    """
    
    if not IMAGE_PATTERN.match(image):
        raise HTTPException(status_code=400, detail="Invalid image reference format")
    
    # Validate digest format
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise HTTPException(
            status_code=400,
            detail="Invalid digest format. Expected sha256:<64 hex chars>"
        )
    
    # Parse image reference to get namespace and repo
    namespace, repo, _ = parse_image_ref(image)
    url = f"{registry_base_url(namespace, repo)}/blobs/{digest}"
    
    # Create authenticated session and fetch the layer
    auth = RegistryAuth(namespace, repo)
    
    try:
        resp = auth.request_with_retry("GET", url, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        auth.invalidate()
        raise HTTPException(status_code=502, detail=f"Registry request failed: {e}")
    
    # Generate a clean filename from the digest
    filename = digest.replace(":", "_") + ".tar.gz"
    
    # Get content length if available
    content_length = resp.headers.get("Content-Length", "")
    
    # Stream the response content directly to the browser
    def generate():
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            resp.close()
            auth.invalidate()
    
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if content_length:
        headers["Content-Length"] = content_length
    
    return StreamingResponse(
        generate(),
        media_type="application/gzip",
        headers=headers,
    )

