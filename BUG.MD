# BUG In Core Workflow

When layers-peeking `sahiljahagirdar91/fastapi_first:latest` the layers received were from a different repo entirely, `dimmyjing/psa-fastapi:latest` 


Note: The launching command is `python main.py --target-image "sahiljahagirdar91/fastapi_first:latest" --peek-all`
 
 - **Namespace: `sahiljahagirdar91`**
 - Repository: `fastapi_first`
 - Tag: `latest`

# Severity: Low - There's a workaround, it's not a showstopper
- Bug #1: Theres's no workflow for a non-interactive workflow if the container supports multiple architectures; the route pops up a prompt for Available platforms


# Severity: Critical
- Bug #2: First phase of application uses the correct endpoint. But when it reaches the "Peeking into all layers" phase it uses the wrong container entirely.
    - The image digest referenced, `[Layer 0] sha256:119d43eec815e5f9a47da3a7d59454581b1e204b0c34db86f171b7ceb3336533`, does not appear in the `sahiljahagirdar91/fastapi_first:latest` repository at all!
    - `dimmyjing/psa-fastapi:latest` is the actual origin of this container imahge digesgt, and the contents of the layer being peeked. 
    - Pulls MULTIPLE JWTs for a single repository; the grants should persist.

```BASH
python main.py --target-image "sahiljahagirdar91/fastapi_first:latest" --peek-all
(base) PS C:\Users\jbras\GitHub\lsng> python main.py --target-image "sahiljahagirdar91/fastapi_first:latest" --peek-all
 Welcome to Layerslayer 

 No token found; proceeding anonymously.
 Unauthorized. Fetching fresh pull token...
 Saved pull token to token_pull.txt.

Available platforms:
 [0] linux/amd64         #                                          <------ I picked layer 0
 [1] linux/arm64
 [2] unknown/unknown
 [3] unknown/unknown
Select a platform [0]: 0

Build steps:
 [0] # debian.sh --arch 'amd64' out/ 'trixie' '@1768176000'
 [1] ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin (metadata only)
[...SNIP...] #                                                              ...up to here the correct image is being used]
[*] Peeking into all layers (complete enumeration):

[Layer 0] sha256:119d43eec815e5f9a47da3a7d59454581b1e204b0c34db86f171b7ceb3336533 # <------ Not the correct image layer manifest, wrong repo, wrong namespace
           Size: 28.4 MB
 Saved pull token to token_pull.txt.

  [Stats] Downloaded: 28.4 MB of 28.4 MB (100.00%)
  [Stats] Files found: 3260 (complete)
[...snip...] 
  Layer sha256:119d43eec815... already exists in database.
    - Scraped: 2026-01-17T21:02:06.730018
    - Entries: 3,260 files
    **- Image: dimmyjing/psa-fastapi:latest                                 #         <-------- WRONG NAMESPACE! WRONG REPO!!
  [...ended connection here...]
```
