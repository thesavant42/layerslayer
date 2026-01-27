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

TUI refactoring complete. The monolithic files have been reorganized into logical submodules:

New TUI Directory Structure:

```txt
app/tui/
├── __init__.py              # Package exports DockerDorkerApp
├── app.py                   # Slimmed from 1093 to ~450 lines
├── styles.tcss              # Core layout only (~50 lines)
├── modals/
│   ├── __init__.py          # Exports FileActionModal, TextViewerModal, SaveFileModal
│   ├── file_action.py       # FileActionModal class
│   ├── save_file.py         # SaveFileModal class
│   ├── text_viewer.py       # TextViewerModal class
│   └── styles.tcss          # All modal styles (~100 lines)
├── utils/
│   ├── __init__.py          # Exports all formatters
│   └── formatters.py        # format_history_date, flatten_nested, is_binary_content, format_config, parse_slug
└── widgets/
    ├── __init__.py          # Exports SearchPanel, RepoPanel, FSSimulator, parse_fslog_line
    ├── search_panel/        # Search input, results table, pagination
    │   ├── __init__.py
    │   ├── search_panel.py
    │   └── styles.tcss
    ├── repo_panel/          # Tag selection, config display
    │   ├── __init__.py
    │   ├── repo_panel.py
    │   └── styles.tcss
    └── fs_simulator/        # Filesystem browser widget
        ├── __init__.py
        ├── fs_simulator.py
        └── styles.tcss

```

![saveas](/docs/screencaps/saveas.png)

If you try to view a binary as plain text you now get a helpful error (instead of a crash)

![warning](/docs/screencaps/binary-oops.png)


![privkey](/docs/screencaps/privkey.png)


## Features

- **API Mode**
    - `python  main.py -A`
- Enable this to use with the TUI

- **Interactive Mode**
  - Deprecated in favor of TUI

- **File Carving** (NEW)
  Extract a specific file from a Docker image without downloading the entire layer.
  Uses HTTP
 Range requests to fetch compressed data incrementally, decompresses on-the-fly, and stops as soon as the target file is fully extracted.

## Usage

```bash
python main.py [options]
```

### API Mode

```bash
python main.py -A
```

See [docs/USAGE.md](docs/USAGE.md) for more examples.

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
