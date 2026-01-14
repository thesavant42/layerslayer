# Guide to Documentation

## Project Docs

[README.md](README.md)
- README.md contains overview of the project, some examples of usage. 

[docs/carver-py.md](carver-py.md)
- The carving process uses an incremental streaming approach:
    -  it fetches compressed data in chunks via HTTP Range requests,
    -  decompresses on-the-fly,
    -  scans tar headers looking for the target file,
    -  and **stops as soon as the target is fully extracted**
        - **avoiding downloading entire layers unnecessarily**.

[docs/layerslayer-py.md](docs/layerslayer-py.md)
The code has 4 mutually exclusive operational modes (carve, bulk-peek, peek-all, save-all, interactive) with the interactive mode being the default fallback.

[fetcher.md](fetcher.md)
The biggest file in the collection, handles far too many things. It's important to not break this file.


[docs/parser-tarparser.md](docs/parser-tarparser.md)
- [`parser.py`](parser.py) handles **what's in the Docker image** at the manifest level (platforms, layers)
- [`tar_parser.py`](tar_parser.py) handles **what's inside each layer** at the binary tar archive level (files, directories, permissions)

[docs\reg-rav-readme.md](docs\reg-rav-readme.md)
- private container registry file downloads
    -  needs to be updated to do proper peeking

## 3rd party APIs

[docs\3rdpartyapis](docs\3rdpartyapis)
docker registry and docker hub APIs