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

## FAQ

- Q:Who is this for?
- A: Myself, mostly. 
  - But if you ever find yourself looking for the presence of files on a docker image, but *don't* want to download a billion gigs of useless images to scrape through them, this is for you. 
  - If you want to carve out only a specific layer of the overlayfs that has the data you want, this is for you.
  - If you like #YOLOSINT and like Full Contact Recon, this is for you.

- Q: How is this any different than `docker pull` and viewing the filesystem?
- A: Functionally, it is not that different. In practice however there are some key differences: This is a python script, very portable and light weight, does not require the docker client to even be installed in order to extract useful info. 
    - And because you only keep the slices you want, you don't need to download the entire image. That's better for the planet somehow, right?

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
 [1] RUN /bin/sh -c apt-get update   && apt-get install -y --no-install-recommends     ca-certificates     curl     git     gnupg     gpg     libfontconfig1     libfreetype6     procps     ssh-client     tini     unzip     tzdata   && rm -rf /var/lib/apt/lists/* # buildkit
 [2] ARG GIT_LFS_VERSION=3.6.1 (metadata only)
 [3] RUN |1 GIT_LFS_VERSION=3.6.1 /bin/sh -c arch=$(uname -m | sed -e 's/x86_64/amd64/g' -e 's/aarch64/arm64/g')   && curl -L -s -o git-lfs.tgz "https://github.com/git-lfs/git-lfs/releases/download/v${GIT_LFS_VERSION}/git-lfs-linux-${arch}-v${GIT_LFS_VERSION}.tar.gz"   && tar xzf git-lfs.tgz   && bash git-lfs-*/install.sh   && rm -rf git-lfs* # buildkit
 [4] ENV LANG=C.UTF-8 (metadata only)
 [5] ARG TARGETARCH=amd64 (metadata only)
 [6] ARG COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 (metadata only)
 [7] ARG user=jenkins (metadata only)
 [8] ARG group=jenkins (metadata only)
 [9] ARG uid=1000 (metadata only)
 [10] ARG gid=1000 (metadata only)
 [11] ARG http_port=8080 (metadata only)
 [12] ARG agent_port=50000 (metadata only)
 [13] ARG JENKINS_HOME=/var/jenkins_home (metadata only)
 [14] ARG REF=/usr/share/jenkins/ref (metadata only)
 [15] ENV JENKINS_HOME=/var/jenkins_home (metadata only)
 [16] ENV JENKINS_SLAVE_AGENT_PORT=50000 (metadata only)
 [17] ENV REF=/usr/share/jenkins/ref (metadata only)
 [18] RUN |11 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref /bin/sh -c mkdir -p $JENKINS_HOME   && chown ${uid}:${gid} $JENKINS_HOME   && groupadd -g ${gid} ${group}   && useradd -d "$JENKINS_HOME" -u ${uid} -g ${gid} -l -m -s /bin/bash ${user} # buildkit
 [19] VOLUME [/var/jenkins_home] (metadata only)
 [20] RUN |11 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref /bin/sh -c mkdir -p ${REF}/init.groovy.d # buildkit
 [21] ARG JENKINS_VERSION=2.504.1 (metadata only)
 [22] ENV JENKINS_VERSION=2.504.1 (metadata only)
 [23] ARG JENKINS_SHA=81026db18b0c4aad6b62cf408e4c42e5797661b41c517b37df606238e89b9df1 (metadata only)
 [24] ARG JENKINS_URL=https://repo.jenkins-ci.org/public/org/jenkins-ci/main/jenkins-war/2.504.1/jenkins-war-2.504.1.war (metadata only)
 [25] RUN |14 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref JENKINS_VERSION=2.504.1 JENKINS_SHA=81026db18b0c4aad6b62cf408e4c42e5797661b41c517b37df606238e89b9df1 JENKINS_URL=https://repo.jenkins-ci.org/public/org/jenkins-ci/main/jenkins-war/2.504.1/jenkins-war-2.504.1.war /bin/sh -c curl -fsSL ${JENKINS_URL} -o /usr/share/jenkins/jenkins.war   && echo "${JENKINS_SHA}  /usr/share/jenkins/jenkins.war" >/tmp/jenkins_sha   && sha256sum -c --strict /tmp/jenkins_sha   && rm -f /tmp/jenkins_sha # buildkit
 [26] ENV JENKINS_UC=https://updates.jenkins.io (metadata only)
 [27] ENV JENKINS_UC_EXPERIMENTAL=https://updates.jenkins.io/experimental (metadata only)
 [28] ENV JENKINS_INCREMENTALS_REPO_MIRROR=https://repo.jenkins-ci.org/incrementals (metadata only)
 [29] RUN |14 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref JENKINS_VERSION=2.504.1 JENKINS_SHA=81026db18b0c4aad6b62cf408e4c42e5797661b41c517b37df606238e89b9df1 JENKINS_URL=https://repo.jenkins-ci.org/public/org/jenkins-ci/main/jenkins-war/2.504.1/jenkins-war-2.504.1.war /bin/sh -c chown -R ${user} "$JENKINS_HOME" "$REF" # buildkit
 [30] ARG PLUGIN_CLI_VERSION=2.13.2 (metadata only)
 [31] ARG PLUGIN_CLI_URL=https://github.com/jenkinsci/plugin-installation-manager-tool/releases/download/2.13.2/jenkins-plugin-manager-2.13.2.jar (metadata only)
 [32] RUN |16 GIT_LFS_VERSION=3.6.1 TARGETARCH=amd64 COMMIT_SHA=2dc434f989966a32739719c8d9bb6c522cc33090 user=jenkins group=jenkins uid=1000 gid=1000 http_port=8080 agent_port=50000 JENKINS_HOME=/var/jenkins_home REF=/usr/share/jenkins/ref JENKINS_VERSION=2.504.1 JENKINS_SHA=81026db18b0c4aad6b62cf408e4c42e5797661b41c517b37df606238e89b9df1 JENKINS_URL=https://repo.jenkins-ci.org/public/org/jenkins-ci/main/jenkins-war/2.504.1/jenkins-war-2.504.1.war PLUGIN_CLI_VERSION=2.13.2 PLUGIN_CLI_URL=https://github.com/jenkinsci/plugin-installation-manager-tool/releases/download/2.13.2/jenkins-plugin-manager-2.13.2.jar /bin/sh -c curl -fsSL ${PLUGIN_CLI_URL} -o /opt/jenkins-plugin-manager.jar   && echo "$(curl -fsSL "${PLUGIN_CLI_URL}.sha256")  /opt/jenkins-plugin-manager.jar" >/tmp/jenkins_sha   && sha256sum -c --strict /tmp/jenkins_sha   && rm -f /tmp/jenkins_sha # buildkit
 [33] EXPOSE map[8080/tcp:{}] (metadata only)
 [34] EXPOSE map[50000/tcp:{}] (metadata only)
 [35] ENV COPY_REFERENCE_FILE_LOG=/var/jenkins_home/copy_reference_file.log (metadata only)
 [36] ENV JAVA_HOME=/opt/java/openjdk (metadata only)
 [37] ENV PATH=/opt/java/openjdk/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin (metadata only)
 [38] COPY /javaruntime /opt/java/openjdk # buildkit
 [39] USER jenkins (metadata only)
 [40] COPY jenkins-support /usr/local/bin/jenkins-support # buildkit
 [41] COPY jenkins.sh /usr/local/bin/jenkins.sh # buildkit
 [42] COPY jenkins-plugin-cli.sh /bin/jenkins-plugin-cli # buildkit
 [43] ENTRYPOINT ["/usr/bin/tini" "--" "/usr/local/bin/jenkins.sh"] (metadata only)
 [44] LABEL org.opencontainers.image.vendor=Jenkins project org.opencontainers.image.title=Official Jenkins Docker image org.opencontainers.image.description=The Jenkins Continuous Integration and Delivery server org.opencontainers.image.version=2.504.1 org.opencontainers.image.url=https://www.jenkins.io/ org.opencontainers.image.source=https://github.com/jenkinsci/docker org.opencontainers.image.revision=2dc434f989966a32739719c8d9bb6c522cc33090 org.opencontainers.image.licenses=MIT (metadata only)

📂 Peeking into all layers:

⦿ Layer [0] sha256:cf05a52c02353f0b2b6f9be0549ac916c3fb1dc8d4bacd405eac7f28562ec9f2
 Unauthorized. Fetching fresh pull token...
 Saved pull token to token_pull.txt.

 Layer contents:

📂 ./
  📄 bin (0.0 B)
📂 boot/
📂 dev/
📂 etc/
  📄 etc/.pwd.lock (0.0 B)
  📄 etc/adduser.conf (3.0 KB)
📂 etc/alternatives/
  📄 etc/alternatives/README (100.0 B)
  📄 etc/alternatives/awk (0.0 B)
  📄 etc/alternatives/awk.1.gz (0.0 B)
  📄 etc/alternatives/builtins.7.gz (0.0 B)
  📄 etc/alternatives/nawk (0.0 B)
  📄 etc/alternatives/nawk.1.gz (0.0 B)
  📄 etc/alternatives/pager (0.0 B)
  📄 etc/alternatives/pager.1.gz (0.0 B)
  📄 etc/alternatives/rmt (0.0 B)
  📄 etc/alternatives/rmt.8.gz (0.0 B)
  📄 etc/alternatives/which (0.0 B)
  📄 etc/alternatives/which.1.gz (0.0 B)
  📄 etc/alternatives/which.de1.gz (0.0 B)
  📄 etc/alternatives/which.es1.gz (0.0 B)
  📄 etc/alternatives/which.fr1.gz (0.0 B)
  📄 etc/alternatives/which.it1.gz (0.0 B)
  📄 etc/alternatives/which.ja1.gz (0.0 B)
  📄 etc/alternatives/which.pl1.gz (0.0 B)
  📄 etc/alternatives/which.sl1.gz (0.0 B)
📂 etc/apt/
📂 etc/apt/apt.conf.d/
  📄 etc/apt/apt.conf.d/01autoremove (399.0 B)
  📄 etc/apt/apt.conf.d/70debconf (182.0 B)
  📄 etc/apt/apt.conf.d/docker-autoremove-suggests (754.0 B)
  📄 etc/apt/apt.conf.d/docker-clean (1.1 KB)
  📄 etc/apt/apt.conf.d/docker-gzip-indexes (481.0 B)
  📄 etc/apt/apt.conf.d/docker-no-languages (269.0 B)
📂 etc/apt/auth.conf.d/
📂 etc/apt/keyrings/
📂 etc/apt/preferences.d/
📂 etc/apt/sources.list.d/
  📄 etc/apt/sources.list.d/debian.sources (443.0 B)
📂 etc/apt/trusted.gpg.d/
  📄 etc/apt/trusted.gpg.d/debian-archive-bookworm-automatic.asc (11.6 KB)
  📄 etc/apt/trusted.gpg.d/debian-archive-bookworm-security-automatic.asc (11.6 KB)
  📄 etc/apt/trusted.gpg.d/debian-archive-bookworm-stable.asc (461.0 B)
 [...]
```

## Contributing

Pull requests and issues are welcome! Please open an issue first for major changes.

## License

MIT License. See [LICENSE](LICENSE) for details.
