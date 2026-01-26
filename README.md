# Layerslayer

![Logo](/docs/layerslayer_banner.png)


[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/thesavant42/layerslayer)


TL;DR - 
1. venv, pip requirements, yada yada
2. Start the API first (in a .venv) `python main.py -A`
3. in a seperate terminal launch the TUI: `python /app/tui/app.py`
4. ctrl+q to quit, or upper left corner menu.



**Layerslayer** is a CLI tool for browsing, inspecting, and selectively downloading Docker image layers via the Docker Registry HTTP API v2. 
Instead of pulling entire images, you can "peek" inside each layer to reconstruct an inferred filesystem, view manifest file build steps, and choose exactly which blobs to save.

![tags](/docs/screencaps/tags.png)

## **NEW**


![saveas](/docs/screencaps/saveas.png)

If you try to view a binary as plain text you now get a helpful error (instead of a crash)

![warning](/docs/screencaps/binary-oops.png)


Implemented --peek-layer CLI flag and /peek API endpoint.

### Changes made:

- main.py - Replaced --peek-all with --peek-layer=<value>:

    `--peek-layer=all` - peeks all layers (previous `--peek-all` behavior)
    `--peek-layer=N` - peeks only layer at index N
    - Fixed `sys.exit(1)` calls to use return (API compatibility)
    `api.py` - Replaced `/peek-all` with `/peek:`
    
    `GET /peek?image=...&layer=all` - all layers
    `GET /peek?image=...&layer=2` - specific layer
    Usage:

# CLI - all layers
`python main.py -t library/alpine:latest --peek-layer=all --arch=0`

# CLI - specific layer
`python main.py -t library/alpine:latest --peek-layer=2 --arch=0`

# API - all layers  
`GET /peek?image=library/alpine:latest&layer=all&arch=0`

# API - specific layer
`GET /peek?image=library/alpine:latest&layer=2&arch=0`


![privkey](/docs/screencaps/privkey.png)


## Features

- **API Mode**
    - ~~`uvicorn app.modules.api.api:app --host 127.0.0.1 --port 8000`~~
    - `python  main.py -A`

- **Interactive Mode**
  Step through platform selection, build steps, layer listing, and per-layer peek/download prompts.

- **Batch Mode**
  - `--peek-all`: Peek all layers (list filesystem contents) without downloading  the entire layer image.

- **File Carving** (NEW)
  Extract a specific file from a Docker image without downloading the entire layer.
  Uses HTTP
 Range requests to fetch compressed data incrementally, decompresses on-the-fly, and stops as soon as the target file is fully extracted.

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
