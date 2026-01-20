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

For private-container related features, see also [reg-rav-readme.md](docs/carver-py.md) (Work in progress, TBD)

## Features

- **Interactive Mode**
  Step through platform selection, build steps, layer listing, and per-layer peek/download prompts.

- **Batch Mode**
  - `--peek-all`: Peek all layers (list filesystem contents) without download prompts.

- **API MODE** `uvicorn app.modules.api.api:app --host 0.0.0.0 --port 8000`

- **File Carving** (NEW)
  Extract a specific file from a Docker image without downloading the entire layer.
  Uses HTTP Range requests to fetch compressed data incrementally, decompresses on-the-fly, and stops as soon as the target file is fully extracted.

- **Multi-arch Support**
  Auto-detects manifest lists vs single-arch manifests and handles both seamlessly.

- **Human-Readable Sizes**
  Prints blob sizes in KB/MB for readability.

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

#### Sample Carve Output

```bash
python main.py -t ubuntu:24.04 --carve-file /etc/passwd
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
(base) cat .\carved\etc\passwd

root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
...continues
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

[...]
-rw-r--r--     205.0 B  2025-11-29 02:44  nsswitch.conf
drwxr-xr-x       0.0 B  2025-12-16 23:03  opt/
lrwxrwxrwx       0.0 B  2025-12-16 23:03  os-release -> ../usr/lib/os-release
-rw-r--r--     702.0 B  2025-11-29 02:44  passwd
drwxr-xr-x       0.0 B  2025-12-16 23:03  periodic/
-rw-r--r--     547.0 B  2025-11-29 02:44  profile
drwxr-xr-x       0.0 B  2025-12-16 23:03  profile.d/
-rw-r--r--      3.1 KB  2025-11-29 02:44  protocols
drwxr-xr-x       0.0 B  2025-12-16 23:03  secfixes.d/
-rw-r--r--     156.0 B  2025-12-16 06:19  securetty
-rw-r--r--     12.5 KB  2025-11-29 02:44  services
-rw-r-----     260.0 B  2025-12-16 23:03  shadow
-rw-r--r--      38.0 B  2025-11-29 02:44  shells
```

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
