import os
import requests

# Add after line 2 (import requests):
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
              "application/vnd.oci.image.manifest.v1+json"
})


def auth_headers(token=None):
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers



## function to manage readaing the jwt  TODO finish migration

def load_token(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return f.read().strip()
    return None

## function to manage writing the jwt  TODO finish migration

def save_token(token, filename="token.txt"):
    with open(filename, "w") as f:
        f.write(token)


# =============================================================================
# Token Management
# =============================================================================

def fetch_pull_token(user, repo):
    """
    Retrieve a Docker Hub pull token (anonymous or authenticated).
    Bypasses the shared session so no extra headers confuse the auth endpoint.
    """
    auth_url = (
        f"https://auth.docker.io/token"
        f"?service=registry.docker.io&scope=repository:{user}/{repo}:pull"
    )
    try:
        # Use plain requests.get() here—no Accept or stale Auth headers
        resp = requests.get(auth_url)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f" Warning: pull-token endpoint error: {e}")
        return None

    token = resp.json().get("token")
    if not token:
        print(" Warning: token endpoint returned no token")
        return None

    save_token(token, filename="token_pull.txt")
    print(" Saved pull token to token_pull.txt.")
    # Now inject the fresh token into our session for all registry calls
    session.headers["Authorization"] = f"Bearer {token}"
    return token

