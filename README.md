# 🛡️ Layerslayer

**Layerslayer** is a CLI tool for browsing and extracting Docker image layers from public and private registries.

Instead of downloading full container images, Layerslayer allows you to **peek** inside individual filesystem layers, view **build steps** (Dockerfile commands), and selectively **download** only what you need.

---

## 🚀 Features

- Pull Docker manifests by `user/image:tag`
- List platforms (multi-arch support)
- Display build steps (from image config)
- Preview filesystem structure inside any layer
- Download individual layers as `.tar.gz`
- Supports authentication via bearer tokens
- Organizes downloads automatically by user/project/tag

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/layerslayer.git
cd layerslayer

# (Optional) Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```
## 🔐 Authentication
Layerslayer requires a valid Docker Hub bearer token for accessing protected images.

Create a file called token.txt in the root project folder.

Paste your Bearer token inside token.txt.

👉 Important: Your token is never uploaded if .gitignore is correctly configured.

Anonymous access is supported for public images, but full functionality is only available with authentication.

## 🛠️ Usage
```
python layerslayer.py
```

Follow the prompts:

- Enter an image reference like `moby/buildkit:latest`
- Select a platform (e.g., linux/amd64)
- View build steps
- Select layers to peek into
- Decide whether to download each layer

## ✨ Future Improvements
- Smarter token refresh handling
- Support for private registries
- JSON or HTML output modes
- Full offline mode with cached manifests
