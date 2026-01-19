# Module: sqlite log search + fs viewer for layer peek output

Storing the output from `layer-peek` to sqlite and reconstructing a simulated filesystem.

## Example Usage

- Help Message & Command arguments

```bash
usage: fs-log-sqlite.py [-h] [--search PATTERN] [--single-layer] [image_ref] [layer_or_path] [path]

Virtual filesystem navigator for Docker layer logs stored in sqlite

positional arguments:
  image_ref             Image reference: owner/repository:tag
  layer_or_path         Layer index number or path
  path                  Directory path to list (e.g., "/" or "/etc")

options:
  -h, --help            show this help message and exit
  --search, -s PATTERN  Search for files/directories matching pattern (supports SQL LIKE patterns)
  --single-layer        Show single layer instead of merged view (requires layer_index)

Examples:
  fs-log-sqlite.py alpine/git:v2.52.0 "/"
  fs-log-sqlite.py alpine/git:v2.52.0 "/etc"
  fs-log-sqlite.py alpine/git:v2.52.0 0 "/" --single-layer
  fs-log-sqlite.py --search shadow                        # search the database for "shadow"
  fs-log-sqlite.py --search shadow alpine/git:v2.52.0     # search all layers of container image
  fs-log-sqlite.py --search shadow alpine/git:v2.52.0 0   # search single layer of container image
        
```

### Example with overrides and symbolic links

```bash
python fs-log-sqlite.py --merged msmengr/disney:latest "/"
lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin                                     [L0]
drwxr-xr-x       0.0 B  2024-04-22 06:08  boot/                                              [L0]
-rw-r--r--      25.0 B  2025-03-23 23:49  deo                                                [L1]
drwxr-xr-x       0.0 B  2025-01-26 18:09  dev/                                               [L0]
drwxr-xr-x       0.0 B  2025-03-23 23:47  etc/                                               [L1]
drwxr-xr-x       0.0 B  2025-01-26 18:09  etc/                                               [L0] (overridden)
drwxr-xr-x       0.0 B  2025-01-26 18:09  home/                                              [L0]
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib -> usr/lib                                     [L0]
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib64 -> usr/lib64                                 [L0]
drwxr-xr-x       0.0 B  2025-01-26 18:03  media/                                             [L0]
drwxr-xr-x       0.0 B  2025-01-26 18:03  mnt/                                               [L0]
drwxr-xr-x       0.0 B  2025-01-26 18:03  opt/                                               [L0]
drwxr-xr-x       0.0 B  2024-04-22 06:08  proc/                                              [L0]
drwx------       0.0 B  2025-03-23 23:52  root/                                              [L1]
drwx------       0.0 B  2025-01-26 18:09  root/                                              [L0] (overridden)
drwxr-xr-x       0.0 B  2025-01-26 18:09  run/                                               [L0]
lrwxrwxrwx       0.0 B  2024-04-22 06:08  sbin -> usr/sbin                                   [L0]
drwxr-xr-x       0.0 B  2025-01-26 18:03  srv/                                               [L0]
drwxr-xr-x       0.0 B  2024-04-22 06:08  sys/                                               [L0]
drwxrwxrwx       0.0 B  2025-03-23 23:46  tmp/                                               [L1]
```

### Show output of a single later, the image layer index 0 "/"

```bash
python fs-log-sqlite.py msmengr/disney:latest 0 "/" --single-layer

lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin
drwxr-xr-x       0.0 B  2024-04-22 06:08  boot/
drwxr-xr-x       0.0 B  2025-01-26 18:09  dev/
drwxr-xr-x       0.0 B  2025-01-26 18:09  etc/
drwxr-xr-x       0.0 B  2025-01-26 18:09  home/
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib -> usr/lib
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib64 -> usr/lib64
[...]
```
