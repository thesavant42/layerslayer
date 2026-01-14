# registry-raider

import sys, os, requests, json

# Show usage if no argument provided
if len(sys.argv) < 2:
    print("Usage: python registry-raider.py <registry_url>")
    print("")
    print("  Enumerate Docker Registry repositories, tags, and manifests.")
    print("")
    print("  Example: python registry-raider.py http://165.22.182.63:5000/")
    sys.exit(1)

# get url from command line
base = sys.argv[1].rstrip('/') + '/'
url = base + "v2/_catalog"

# Must keep verify=False
resp = requests.get(url, verify=False).json()

# Fetching Catalog from http://165.22.182.63:5000/
print(f"Fetching Catalog from {base}\n")

repos = resp.get("repositories", [])
print(f"  Repositories:  {len(repos)}\n")

for i, r in enumerate(repos, 1):
    print(f"  {i}. {r}")

print(f"\n")

#   Repositories:  2
#   1. op-cdr/go-consumer
#   2. op-cdr/go-s3collector

# prompt user to select the key corresponding to the repository they want to enumerate
# - parse the repository and its owner (namespace) from previous
# then request to `base/v2/namespace/repository/tags/list`` and parse the json response
#
# Tags for: library/ubuntu
#  Total:  2
#
#  1. latest
#  2. dev
#

def list_tags(base_url, repository):
    """Fetch and display tags for a given repository (namespace/repo)."""
    url = f"{base_url}v2/{repository}/tags/list"
    resp = requests.get(url, verify=False).json()
    tags = resp.get("tags", [])
    
    print(f"Tags for: {repository}")
    print(f"  Total:  {len(tags)}\n")
    
    for i, tag in enumerate(tags, 1):
        print(f"  {i}. {tag}")
    
    print("")
    return tags


def get_manifest(base_url, repository, tag):
    """Fetch and display manifest for a given repository and tag."""
    url = f"{base_url}v2/{repository}/manifests/{tag}"
    resp = requests.get(url, verify=False).json()
    
    print(f"\nManifest for: {repository}:{tag}")
    print("-" * 50)
    
    # Basic info from manifest
    if "architecture" in resp:
        print(f"architecture: {resp.get('architecture')}")
    
    # Parse history entries for config and build commands
    history = resp.get("history", [])
    if history:
        # First entry typically has the full config
        first_entry = history[0]
        v1_compat = first_entry.get("v1Compatibility", "{}")
        try:
            config_data = json.loads(v1_compat)
            
            # Extract OS
            if "os" in config_data:
                print(f"os:           {config_data.get('os')}")
            
            # Extract config details
            config = config_data.get("config", {})
            
            # Exposed ports
            exposed_ports = config.get("ExposedPorts", {})
            for port in exposed_ports:
                print(f"ExposedPorts: {port}")
            
            # Environment variables
            env_vars = config.get("Env", [])
            for env in env_vars:
                print(f"ENV:          {env}")
            
            # Entrypoint
            entrypoint = config.get("Entrypoint", [])
            if entrypoint:
                print(f"ENTRYPOINT:   {' '.join(entrypoint)}")
            
            # Working directory
            workdir = config.get("WorkingDir")
            if workdir:
                print(f"WORKINGDIR:   {workdir}")
            
            # Created timestamp
            if "created" in config_data:
                print(f"created:      {config_data.get('created')}")
            
            # ID and parent
            if "id" in config_data:
                print(f"id:           {config_data.get('id')}")
            if "parent" in config_data:
                print(f"parent:       {config_data.get('parent')}")
            
        except json.JSONDecodeError:
            print("  [Could not parse v1Compatibility]")
        
        # Display build commands from all history entries
        print(f"\nBuild History ({len(history)} layers):")
        print("-" * 50)
        for i, entry in enumerate(history):
            v1_compat = entry.get("v1Compatibility", "{}")
            try:
                layer_data = json.loads(v1_compat)
                container_config = layer_data.get("container_config", {})
                cmd = container_config.get("Cmd", [])
                
                # Try to get command string
                cmd_str = None
                if cmd:
                    # cmd can be a list or a single command
                    cmd_str = cmd[0] if isinstance(cmd, list) else cmd
                
                print(f"  [{i+1}] {cmd_str}")
            except json.JSONDecodeError:
                print(f"  [{i+1}] (could not parse layer)")
    
    print("")
    return resp


def format_size(size_bytes):
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_blob_size(base_url, repository, digest):
    """Get blob size using HEAD request. Returns size in bytes or None on error."""
    url = f"{base_url}v2/{repository}/blobs/{digest}"
    try:
        resp = requests.head(url, verify=False, allow_redirects=True)
        if resp.status_code == 200:
            content_length = resp.headers.get('Content-Length')
            if content_length:
                return int(content_length)
    except requests.exceptions.RequestException:
        pass
    return None


def list_fs_layers(base_url, repository, manifest):
    """Display fsLayers from manifest with sizes. Returns list of digests."""
    fs_layers = manifest.get("fsLayers", [])
    
    print(f"\nfsLayers ({len(fs_layers)} total):")
    print("-" * 50)
    
    digests = []
    for i, layer in enumerate(fs_layers, 1):
        digest = layer.get("blobSum", "")
        digests.append(digest)
        
        # Get size via HEAD request
        size = get_blob_size(base_url, repository, digest)
        size_str = f"({format_size(size)})" if size else "(size unknown)"
        
        # Show abbreviated digest for readability
        print(f"  {i:02d}. {digest} {size_str}")
    
    print("")
    return digests


def download_blob(base_url, repository, digest, tag, layer_num, output_dir="."):
    """Download blob and save to output_dir as {namespace}-{repo}-{tag}-{layer}.tar.gz"""
    url = f"{base_url}v2/{repository}/blobs/{digest}"
    
    # Build filename: namespace-repo-tag-layernumber.tar.gz
    # Replace / with - for filesystem safety
    safe_repo = repository.replace("/", "-")
    filename = f"{safe_repo}-{tag}-layer{layer_num}.tar.gz"
    filepath = os.path.join(output_dir, filename)
    
    print(f"Downloading {digest}...")
    
    try:
        resp = requests.get(url, verify=False, stream=True)
        resp.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Saved as {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"Error downloading blob: {e}")
        return None


def parse_layer_selection(selection, max_count):
    """
    Parse layer selection string into list of indices.
    
    Supports:
      - Single number: "5"
      - Comma-separated: "1,3,5"
      - Range: "1-5"
      - Combined: "1-5,8,10-12"
    
    Returns tuple: (sorted list of 0-based indices, error message or None)
    """
    indices = set()
    
    # Split by comma
    parts = selection.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        if '-' in part:
            # Range: "1-5"
            try:
                range_parts = part.split('-', 1)
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
                
                if start > end:
                    start, end = end, start  # Allow reverse ranges
                
                # Check bounds
                if start < 1 or end > max_count:
                    return None, f"Layer numbers must be between 1 and {max_count}."
                
                for i in range(start, end + 1):
                    indices.add(i - 1)  # Convert to 0-based
            except (ValueError, IndexError):
                return None, "Invalid range format. Use format like '1-5'."
        else:
            # Single number
            try:
                num = int(part)
                if num < 1 or num > max_count:
                    return None, f"Layer {num} is out of range. Must be between 1 and {max_count}."
                indices.add(num - 1)
            except ValueError:
                return None, f"Invalid number: '{part}'."
    
    if not indices:
        return None, "No valid layers specified."
    
    return sorted(indices), None


# Prompt user to select a repository
while True:
    try:
        selection = input("Select a repository (number) or 'q' to quit: ").strip()
        if selection.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        
        idx = int(selection) - 1
        if 0 <= idx < len(repos):
            selected_repo = repos[idx]
            print(f"\n")
            tags = list_tags(base, selected_repo)
            break
        else:
            print(f"Invalid selection. Please enter a number between 1 and {len(repos)}.")
    except ValueError:
        print("Please enter a valid number or 'q' to quit.")
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


# Prompt user to select a tag and retrieve the manifest
while True:
    try:
        selection = input("Select a tag (number) or 'q' to quit: ").strip()
        if selection.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        
        idx = int(selection) - 1
        if 0 <= idx < len(tags):
            selected_tag = tags[idx]
            manifest = get_manifest(base, selected_repo, selected_tag)
            break
        else:
            print(f"Invalid selection. Please enter a number between 1 and {len(tags)}.")
    except ValueError:
        print("Please enter a valid number or 'q' to quit.")
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


# Display fsLayers and prompt for download
digests = list_fs_layers(base, selected_repo, manifest)

if digests:
    # Track which layers to download
    layers_to_download = []
    
    while True:
        try:
            selection = input("Select fsLayer(s) - number, range (1-5), list (1,3,5), 'a' for all, or 'q' to quit: ").strip()
            if selection.lower() == 'q':
                print("Exiting.")
                sys.exit(0)
            
            if selection.lower() == 'a':
                # Download all layers
                layers_to_download = list(range(len(digests)))
                break
            
            # Parse selection (supports single, range, comma-separated, or combined)
            indices, error = parse_layer_selection(selection, len(digests))
            if error:
                print(f"Error: {error}")
                continue
            
            layers_to_download = indices
            break
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)
    
    # Prompt for output directory
    try:
        output_dir = input("Output directory [press Enter for current dir]: ").strip()
        if not output_dir:
            output_dir = "."
        
        # Create directory if it doesn't exist
        if output_dir != "." and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        # Download selected layer(s)
        total = len(layers_to_download)
        for i, idx in enumerate(layers_to_download, 1):
            digest = digests[idx]
            layer_num = idx + 1
            safe_repo = selected_repo.replace("/", "-")
            filename = f"{safe_repo}-{selected_tag}-layer{layer_num}.tar.gz"
            
            if total > 1:
                print(f"\n[{i}/{total}] Saving layer {layer_num} as {filename}")
            else:
                print(f"\nSaving layer {layer_num} as {filename}")
            
            download_blob(base, selected_repo, digest, selected_tag, layer_num, output_dir)
        
        if total > 1:
            print(f"\nDownloaded {total} layers to {output_dir}")
    
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


# See [reg-raider-manifests-info.md](reg-raider-manifests-info.md) for details.
