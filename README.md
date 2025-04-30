# Layerslayer

**Layerslayer** is a CLI tool for browsing, inspecting, and selectively downloading Docker image layers via the Docker Registry HTTP API v2. Instead of pulling entire images, you can peek inside each layer, view build steps, and choose exactly which blobs to save.

## Features

- **Interactive Mode**  
  Step through platform selection, build steps, layer listing, and per-layer peek/download prompts.

- **Batch Modes**  
  - `--peek-all`: Peek all layers (list contents) without download prompts.  
  - `--save-all`: Download all layers in one go without flooding your console with file listings.

- **CLI Flags**  
  - `--target-image, -t`  
    Specify the image reference (`user/repo:tag`) on the command line.  
  - `--log-file, -l`  
    Save full stdout/stderr to a log file (tee output to both console and file).

- **Multi-arch Support**  
  Auto-detects manifest lists vs single-arch manifests and handles both seamlessly.

- **Token Management**  
  Loads a bearer token from `token.txt` and automatically refreshes via Docker Hub auth when needed.

- **Human-Readable Sizes**  
  Prints blob sizes in KB/MB for readability.

## Prerequisites

- Python 3.7 or newer  
- `requests` library  

```bash
pip install requests
```

- (Optional) A Docker Registry bearer token saved as `token.txt` in the repo root.

## Installation

```bash
git clone https://github.com/thesavant42/layerslayer.git
cd layerslayer
```

(Optional) Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python layerslayer.py [options]
```

### Interactive Mode (default)

```bash
python layerslayer.py
```

Prompts you for:
1. **Image reference** (`user/repo:tag`)  
2. **Platform selection** (if multi-arch)  
3. **Layers to peek/download** with per-layer confirmation  

### Peek All Layers

List contents of all layers in one go (no download prompts):

```bash
python layerslayer.py --target-image ""moby/buildkit:latest"" --peek-all
```

### Download All Layers

Download every layer without listing file contents:

```bash
python layerslayer.py -t "moby/buildkit:latest" --save-all
```

### Logging

Tee all output to a log file:

```bash
python layerslayer.py -t "moby/buildkit:latest" -l layers_output.log
```

## Examples

- **Peek & log** all layers of `moby/buildkit:latest`:
  ```bash
  python layerslayer.py -t "moby/buildkit:latest" --peek-all -l peek.log
  ```

- **Interactive** inspection of `nginx:alpine`:
  ```bash
  python layerslayer.py -t nginx:alpine
  ```

- **Download** all layers of `ubuntu:20.04`:
  ```bash
  python layerslayer.py --target-image ubuntu:20.04 --save-all
  ```

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
