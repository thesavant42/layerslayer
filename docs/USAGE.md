## Help

- Print the basic help screen

`python .\main.py --help`

```bash
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

### Carve

 Download a file out of the Image Layer tar gzip, but only download the parts of the layer hat you need!

- By combining HTTP range with a sliding 256k buffer to catch a gzip header byte, seek to the begining of the packet, and then decompress until we reach the end of the sought after file (passwd in this example), and then the connection is immediately severed. Only the file size + ranging overhead

```bash
python main.py -t ubuntu:24.04 --carve-file /etc/passwd
(base) PS C:\Users\jbras\GitHub\lsng> python main.py -t ubuntu:24.04 --carve-file /etc/passwd
 Welcome to Layerslayer 

[*] Carve mode: extracting /etc/passwd from ubuntu:24.04

Fetching manifest for library/ubuntu:24.04...
Found 1 layer(s). Searching for /etc/passwd...

Scanning layer 1/1: sha256:20043066d3d5c...
  Layer size: 29,724,688 bytes
  Downloaded: 65,536B -> Decompressed: 300,732B -> Entries: 111
  FOUND: /etc/passwd (888 bytes) at entry #111

Done! File saved to: carved\etc\passwd
Stats: Downloaded 65,536 bytes of 29,724,688 byte layer (0.2%) in 1.14s
```
### Peek All Layers

List contents of all layers in one go (no download prompts):

```bash
python main.py --target-image "moby/buildkit:latest" --peek-all
```

### Download All Layers

Download every layer without listing file contents:

```bash
python main.py -t "moby/buildkit:latest" --save-all
```

### Logging

Tee all output to a log file:

```bash
python main.py -t "moby/buildkit:latest" -l layers_output.log
```

## Examples

- **Peek & log** all layers of `moby/buildkit:latest`:
  ```bash
  python main.py -t "moby/buildkit:latest" --peek-all -l peek.log
  ```

- **Interactive** inspection of `nginx:alpine`:
  ```bash
  python main.py -t nginx:alpine
  ```

- **Download** all layers of `ubuntu:20.04`:
  ```bash
  python main.py --target-image ubuntu:20.04 --save-all
  ```

### File Carving

Extract a specific file from a Docker image without downloading the entire layer:

```bash
# Extract /etc/passwd from ubuntu:24.04
python main.py -t ubuntu:24.04 --carve-file /etc/passwd

# Extract nginx config with custom output directory
python main.py -t nginx:alpine -f /etc/nginx/nginx.conf -o ./output

# Quiet mode (suppress progress)
python main.py -t alpine:latest -f /etc/os-release -q

# Custom chunk size (128KB)
python main.py -t ubuntu:24.04 -f /etc/passwd -c 128
```

You can also use the carver module directly:

```bash
python carver.py ubuntu:24.04 /etc/passwd
python carver.py nginx:alpine /etc/nginx/nginx.conf -o ./output
```
