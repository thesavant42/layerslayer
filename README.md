# Layerslayer

**Layerslayer** is a CLI tool for browsing, inspecting, and selectively downloading Docker image layers via the Docker Registry HTTP API v2. Instead of pulling entire images, you can peek inside each layer, view build steps, and choose exactly which blobs to save.

## Features

- **Interactive Mode**
  Step through platform selection, build steps, layer listing, and per-layer peek/download prompts.

- **Batch Modes**
  - `--peek-all`: Peek all layers (list contents) without download prompts.
  - `--save-all`: Download all layers in one go without flooding your console with file listings.

- **File Carving** (NEW)
  Extract a specific file from a Docker image without downloading the entire layer.
  Uses HTTP Range requests to fetch compressed data incrementally, decompresses on-the-fly, and stops as soon as the target file is fully extracted.

- **CLI Flags**
  - `--target-image, -t`
    Specify the image reference (`user/repo:tag`) on the command line.
  - `--carve-file, -f`
    Extract a specific file from the image (e.g., `/etc/passwd`).
  - `--output-dir, -o`
    Output directory for carved files (default: `./carved`).
  - `--chunk-size, -c`
    Chunk size in KB for streaming carve (default: 64).
  - `--quiet, -q`
    Suppress detailed progress output.
  - `--log-file, -l`
    Save full stdout/stderr to a log file (tee output to both console and file).

- **Multi-arch Support**
  Auto-detects manifest lists vs single-arch manifests and handles both seamlessly.

- **Token Management**
  Loads a bearer token from `token.txt` and automatically refreshes via Docker Hub auth when needed.

- **Human-Readable Sizes**
  Prints blob sizes in KB/MB for readability.

## FAQ

- Q:Who is this for?
- A: Myself, mostly. 
  - But if you ever find yourself looking for the presence of files on a docker image, but *do not* want to download a billion gigs of useless images to scrape through them, this is for you. 
  - If you want to carve out only a specific layer of the overlayfs that has the data you want, this is for you.
  - If you like #YOLOSINT and like Full Contact Recon, this is for you.

- Q: How is this any different than `docker pull` and viewing the filesystem?
- A: Functionally, it is not that different. In practice however there are some key differences:
    -  This is a python script, very portable and light weight, does not require the docker client to even be installed in order to extract useful info. 
    - And because you only keep the slices you want, you don't need to download the entire image.
    -  That's better for the planet somehow, right? You get me.

## Prerequisites

- Python 3.7 or newer  
- `requests` library  

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
python layerslayer.py --target-image "moby/buildkit:latest" --peek-all
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

### File Carving

Extract a specific file from a Docker image without downloading the entire layer:

```bash
# Extract /etc/passwd from ubuntu:24.04
python layerslayer.py -t ubuntu:24.04 --carve-file /etc/passwd

# Extract nginx config with custom output directory
python layerslayer.py -t nginx:alpine -f /etc/nginx/nginx.conf -o ./output

# Quiet mode (suppress progress)
python layerslayer.py -t alpine:latest -f /etc/os-release -q

# Custom chunk size (128KB)
python layerslayer.py -t ubuntu:24.04 -f /etc/passwd -c 128
```

You can also use the carver module directly:

```bash
python carver.py ubuntu:24.04 /etc/passwd
python carver.py nginx:alpine /etc/nginx/nginx.conf -o ./output
```

#### Sample Carve Output

```bash
$ python layerslayer.py -t ubuntu:24.04 -f /etc/passwd

 Welcome to Layerslayer

[*] Carve mode: extracting /etc/passwd from ubuntu:24.04

Fetching manifest for library/ubuntu:24.04...
Found 1 layer(s). Searching for /etc/passwd...

Scanning layer 1/1: sha256:ff65ddf9395b...
  Layer size: 29,724,688 bytes
  Downloaded: 65,536B -> Decompressed: 312,832B -> Entries: 98
  FOUND: /etc/passwd (1,622 bytes) at entry #98

Done! File saved to: carved/etc/passwd
Stats: Downloaded 65,536 bytes of 29,724,688 byte layer (0.2%) in 0.87s
```

### Sample Output of Print Only mode

```bash
 Welcome to Layerslayer 

 Loaded token from token.txt
 Using loaded token.
 Unauthorized. Fetching fresh pull token...
 Saved pull token to token_pull.txt.

Available platforms:
 [0] linux/amd64
 [1] linux/arm64
 [2] linux/s390x
 [3] linux/ppc64le
 [4] unknown/unknown
 [5] unknown/unknown
 [6] unknown/unknown
 [7] unknown/unknown

Select a platform [0]:  Unauthorized. Fetching fresh pull token...
 Saved pull token to token_pull.txt.
 Unauthorized. Fetching fresh pull token...
 Saved pull token to token_pull.txt.

Build steps:
 [0] # debian.sh --arch 'amd64' out/ 'bookworm' '@1745798400'
 [1] RUN /bin/sh -c apt-get update   && apt-get install -y --no-install-recommends     ca-certificates     curl     git     gnupg     gpg     libfontconfig1     libfreetype6     procps     [
[...]]
 [18] RUN |11 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref /bin/sh -c mkdir -p $JENKINS_HOME   && chown ${uid}:${gid} $JENKINS_HOME   && groupadd -g ${gid} ${group}   && useradd -d "$JENKINS_HOME" -u ${uid} -g ${gid} -l -m -s /bin/bash ${user} # buildkit
 [19] VOLUME [/var/jenkins_home] (metadata only)
 [20] RUN |11 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref /bin/sh -c mkdir -p ${REF}/init.groovy.d # buildkit
 [21] ARG JENKINS_VERSION=2.504.1 (metadata only)
 [...] 
 [33] EXPOSE map[8080/tcp:{}] (metadata only)
 [34] EXPOSE map[50000/tcp:{}] (metadata only)
 
 [...]
 Layer contents:

| ./
|- bin (0.0 B)
| boot/
| dev/
| etc/
  |- etc/.pwd.lock (0.0 B)
  |- etc/adduser.conf (3.0 KB)
  | etc/alternatives/
  |- etc/alternatives/README (100.0 B)
  |- etc/alternatives/awk (0.0 B)
  |- etc/alternatives/awk.1.gz (0.0 B)
  |- etc/alternatives/builtins.7.gz (0.0 B)
  |- etc/alternatives/nawk (0.0 B)
  |- etc/alternatives/nawk.1.gz (0.0 B)
  |- etc/alternatives/pager (0.0 B)
 [...]
  | etc/apt/trusted.gpg.d/
  |- etc/apt/trusted.gpg.d/debian-archive-bookworm-automatic.asc (11.6 KB)
  |- etc/apt/trusted.gpg.d/debian-archive-bookworm-security-automatic.asc (11.6 KB)
  |- etc/apt/trusted.gpg.d/debian-archive-bookworm-stable.asc (461.0 B)
 [...]
```

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
