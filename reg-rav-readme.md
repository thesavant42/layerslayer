# registory-raider

Interactive CLI tool for enumerating Docker Registry v2 repositories, tags, manifests, and downloading filesystem layers.

## Usage

```bash
python registory-raider.py <registry_url>
```

**Example:**
```bash
python registory-raider.py http://192.168.1.100:5000/
```

## Workflow

The tool guides through an interactive selection process:

1. **Repository selection** - Lists all repositories in the registry catalog
2. **Tag selection** - Lists available tags for the selected repository
3. **Manifest display** - Shows image metadata (architecture, OS, ENV, ENTRYPOINT, build history)
4. **Layer listing** - Displays filesystem layers with sizes (via HEAD requests)
5. **Layer download** - Downloads selected layers to specified directory

## Layer Selection Syntax

| Input | Effect |
|-------|--------|
| `5` | Single layer |
| `1,3,5` | Multiple specific layers |
| `1-5` | Range (inclusive) |
| `1-3,7,9-10` | Combined ranges and numbers |
| `a` | All layers |
| `q` | Quit |

Out-of-bounds selections produce an error.

## Output

Downloaded layers are saved as:
```
{namespace}-{repository}-{tag}-layer{N}.tar.gz
```

**Example:** `op-cdr-go-consumer-latest-layer3.tar.gz`

Output directory is prompted after selection. Non-existent directories are created automatically.

---

## API Reference

### Functions

#### `list_tags(base_url, repository)`
Fetches and displays tags for a repository.
- **Returns:** List of tag strings

#### `get_manifest(base_url, repository, tag)`
Fetches manifest and displays image metadata (architecture, OS, ENV, ENTRYPOINT, build history).
- **Returns:** Full manifest dict

#### `list_fs_layers(base_url, repository, manifest)`
Displays filesystem layers with sizes obtained via HEAD requests.
- **Returns:** List of digest strings

#### `get_blob_size(base_url, repository, digest)`
Gets blob size using HEAD request to blob endpoint.
- **Returns:** Size in bytes, or `None` on error

#### `download_blob(base_url, repository, digest, tag, layer_num, output_dir=".")`
Downloads a blob and saves to output directory.
- **Returns:** Filepath on success, `None` on error

#### `parse_layer_selection(selection, max_count)`
Parses layer selection string (supports numbers, ranges, comma-separated).
- **Returns:** Tuple of `(list of 0-based indices, error_message or None)`

#### `format_size(size_bytes)`
Formats bytes to human-readable string (bytes/KB/MB).
- **Returns:** Formatted string

---

## Docker Registry V2 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `BASE/v2/_catalog` | List repositories |
| `BASE/v2/{namespace}/{repo}/tags/list` | List tags |
| `BASE/v2/{namespace}/{repo}/manifests/{tag}` | Get manifest |
| `BASE/v2/{namespace}/{repo}/blobs/{digest}` | Download layer blob |

---

## Dependencies

- `requests`
- Python 3.6+

## Related Documentation

- [reg-raider-manifests-info.md](reg-raider-manifests-info.md) - Manifest structure details
