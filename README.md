# Layerslayer

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/thesavant42/layerslayer)


**Layerslayer** is a CLI tool for browsing, inspecting, and selectively downloading Docker image layers via the Docker Registry HTTP API v2. 
Instead of pulling entire images, you can "peek" inside each layer to reconstruct an inferred filesystem, view manifest file build steps, and choose exactly which blobs to save.


```bash
`python .\main.py --help`

usage: main.py [-h] [--target-image IMAGE_REF] [--peek-all] [--save-all] [--log-file LOG_FILE] [--simple-output] [--bulk-peek] [--carve-file CARVE_FILE]
                      [--output-dir OUTPUT_DIR] [--quiet]

Explore and download individual Docker image layers.

options:
  -h, --help            show this help message and exit
  --target-image, -t IMAGE_REF
                        Image (user/repo:tag) to inspect
  --peek-all            Peek into all layers and exit (no download prompts)
  --save-all            Download all layers and exit (no peek listings)
  --log-file, -l LOG_FILE
                        Path to save a complete log of output
  --simple-output       Use simple output format instead of ls -la style
  --bulk-peek           Peek all layers in bulk and show combined filesystem
  --carve-file, -f CARVE_FILE
                        Extract a specific file from the image (e.g., /etc/passwd)
  --output-dir, -o OUTPUT_DIR
                        Output directory for carved files (default: ./carved)
  --quiet, -q           Suppress detailed progress output
```

## Features

- **NEW: API Mode**
    - `uvicorn app.modules.api.api:app --host 127.0.0.1 --port 8000 `

- **Interactive Mode**
  Step through platform selection, build steps, layer listing, and per-layer peek/download prompts.

- **Batch Mode**
  - `--peek-all`: Peek all layers (list filesystem contents) without downloading  the entire layer image.

- **File Carving** (NEW)
  Extract a specific file from a Docker image without downloading the entire layer.
  Uses HTTP Range requests to fetch compressed data incrementally, decompresses on-the-fly, and stops as soon as the target file is fully extracted.

### Docs

See [docs/DOCS.md](docs/DOCS.md) for a map of the technical documentation.

## Usage

```bash
python main.py [options]
```

### Interactive Mode

```bash
python main.py --interactive
```

See [docs/USAGE.md](docs/USAGE.md) for more examples.

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
