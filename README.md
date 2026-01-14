# Layerslayer

**Layerslayer** is a CLI tool for browsing, inspecting, and selectively downloading Docker image layers via the Docker Registry HTTP API v2. Instead of pulling entire images, you can peek inside each layer, view build steps, and choose exactly which blobs to save.

For private-container related features, see also [reg-rav-readme.md](docs/carver-py.md)

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

### Docs
See [docs/DOCS.md](docs/DOCS.md) for a map of the technical documentation.


## FAQ

- Q: Who is this for?
- A: Myself, mostly. 
  - But if you ever find yourself looking for the presence of files on a docker image, but *do not* want to download a billion gigs of useless images to scrape through them, this is for you. 
  - If you want to carve out only a specific layer of the overlayfs that has the data you want, this is for you.
  - If you like #YOLOSINT and like Full Contact Recon, this is for you.

- Q: How is this any different than `docker pull` and viewing the filesystem?
- A: Functionally, it is not that different. In practice however there are some key differences:
    -  This is a python script, very portable and light weight, does not require the docker client to even be installed in order to extract useful info. 
    - And because you only keep the slices you want, you don't need to download the entire image.
    -  That's better for the planet somehow, right? You get me.

- Q: ...
- A: *Ok*, let's say you need to quickly search for the existence of a specific passwd file and all of the candidate containers are 40+ gigabytes. They're unmanaged; you could download each of them, mount the images, and crawl for the file. But that could take hours, days... and could take up countless gigabytes of space.

Or, you could use ths, and wthin seconds,  search each layer image for a passwd file and only spend a few hundred kilobytes of overhead for your trouble.

I prefer the fast option. 

## Speed from Efficiency

- It is fast by nature of only decompressing the parts of the file that are actually needed with HTTP range and sliding-window file decompression.
    - followed by an abrupt closure of the connection.

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

See [docs/USAGE.md](docs/USAGE.md) for more examples.

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
