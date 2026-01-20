## Code Structure Overview for `fetcher.py`

The file contains:
- 2 dataclasses ([`LayerPeekResult`](fetcher.py:32), [`LayerSlayerResult`](fetcher.py:56))
- 1 module-level session ([`session`](fetcher.py:22))
- 9 functions organized into 5 logical sections

## Module Organization

```mermaid
flowchart TD
    subgraph DataClasses["Data Classes (32-79)"]
        LPR[LayerPeekResult]
        LSR[LayerSlayerResult]
    end
    
    subgraph TokenMgmt["Token Management (86-112)"]
        FPT[fetch_pull_token]
    end
    
    subgraph ManifestFetch["Manifest & Config (119-176)"]
        GM[get_manifest]
        FBS[fetch_build_steps]
    end
    
    subgraph FullDownload["Full Download (183-213)"]
        DLB[download_layer_blob]
    end
    
    subgraph Peek["Layer Peek Functions (220-648)"]
        PLB[peek_layer_blob]
        PLBC[peek_layer_blob_complete]
        PLBP[peek_layer_blob_partial]
        PLBS[peek_layer_blob_streaming]
    end
    
    subgraph Helpers["Helper Functions (368-391)"]
        TIMS[_tarinfo_mode_to_string]
        FMT[_format_mtime]
    end
    
    subgraph BulkPeek["Bulk Operations (655-736)"]
        LS[layerslayer]
    end
    
    LS --> PLBC
    PLBC --> TIMS
    PLBC --> FMT
    PLBC --> FPT
    PLBP --> FPT
    PLBS --> FPT
    PLB --> FPT
    GM --> FPT
    FBS --> FPT
    DLB --> FPT
```

## Main Function Control Flows

### fetch_pull_token (86-112)

```mermaid
flowchart TD
    START([user, repo]) --> REQ[requests.get auth_url]
    REQ --> TRY{try/except}
    TRY -->|RequestException| WARN1[Print warning] --> RET_NONE1([return None])
    TRY -->|Success| CHECK_TOK{token in response?}
    CHECK_TOK -->|No| WARN2[Print warning] --> RET_NONE2([return None])
    CHECK_TOK -->|Yes| SAVE[save_token]
    SAVE --> UPDATE[session.headers update]
    UPDATE --> RET_TOK([return token])
```

### get_manifest (119-148)

```mermaid
flowchart TD
    START([image_ref, token, specific_digest]) --> PARSE[parse_image_ref]
    PARSE --> BUILD_URL[Build URL with ref or digest]
    BUILD_URL --> TOK_CHK{token provided?}
    TOK_CHK -->|Yes| SET_AUTH[Set Authorization header]
    TOK_CHK -->|No| REQ1
    SET_AUTH --> REQ1[session.get]
    REQ1 --> AUTH1{status == 401?}
    AUTH1 -->|Yes| REFRESH[fetch_pull_token]
    REFRESH --> NEW_TOK{new_token?}
    NEW_TOK -->|Yes| REQ2[session.get retry]
    NEW_TOK -->|No| WARN[Print proceeding without token]
    REQ2 --> AUTH2
    WARN --> AUTH2{still 401?}
    AUTH1 -->|No| AUTH2
    AUTH2 -->|Yes| ERROR[Print error] --> EXIT([SystemExit 1])
    AUTH2 -->|No| RAISE[raise_for_status]
    RAISE --> RETURN([return resp.json])
```

### fetch_build_steps (151-176)

```mermaid
flowchart TD
    START([image_ref, config_digest, token]) --> PARSE[parse_image_ref]
    PARSE --> REQ1[session.get blob URL]
    REQ1 --> AUTH{status == 401?}
    AUTH -->|Yes| REFRESH[fetch_pull_token]
    REFRESH --> NEW{new_token?}
    NEW -->|Yes| REQ2[session.get retry]
    NEW -->|No| WARN[Print proceeding]
    REQ2 --> RAISE
    WARN --> RAISE[raise_for_status]
    AUTH -->|No| RAISE
    RAISE --> GET_JSON[resp.json]
    GET_JSON --> LOOP[For entry in history]
    LOOP --> GET_STEP[Get created_by]
    GET_STEP --> EMPTY{empty_layer?}
    EMPTY -->|Yes| ADD_META[Append metadata only tag]
    EMPTY -->|No| APPEND
    ADD_META --> APPEND[Append to steps]
    APPEND --> MORE{more entries?}
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN([return steps])
```

### download_layer_blob (183-213)

```mermaid
flowchart TD
    START([image_ref, digest, size, token]) --> PARSE[parse_image_ref]
    PARSE --> REQ1[session.get stream=True]
    REQ1 --> AUTH{status == 401?}
    AUTH -->|Yes| REFRESH[fetch_pull_token]
    REFRESH --> NEW{new_token?}
    NEW -->|Yes| REQ2[session.get retry stream=True]
    NEW -->|No| WARN[Print proceeding]
    REQ2 --> RAISE
    WARN --> RAISE
    AUTH -->|No| RAISE[raise_for_status]
    RAISE --> MKDIR[os.makedirs output_dir]
    MKDIR --> WRITE[Write chunks to file]
    WRITE --> PRINT([Print saved message])
```

### peek_layer_blob_complete (260-365)

```mermaid
flowchart TD
    START([image_ref, digest, layer_size, token]) --> PARSE[parse_image_ref]
    PARSE --> TOK_CHK{token?}
    TOK_CHK -->|No| GET_TOK[fetch_pull_token]
    TOK_CHK -->|Yes| BUILD
    GET_TOK --> BUILD[Build URL and headers]
    BUILD --> TOK_CHK2{token now?}
    TOK_CHK2 -->|Yes| SET_AUTH[Add Authorization]
    TOK_CHK2 -->|No| TRY
    SET_AUTH --> TRY
    
    TRY{try request}
    TRY -->|RequestException| ERR_RESULT([return error LayerPeekResult])
    TRY -->|Success| REQ1[requests.get stream]
    REQ1 --> AUTH{status == 401?}
    AUTH -->|Yes| RETRY_TOK[fetch_pull_token]
    RETRY_TOK --> RETRY_CHK{token?}
    RETRY_CHK -->|Yes| REQ2[requests.get retry]
    RETRY_CHK -->|No| RAISE
    REQ2 --> RAISE
    AUTH -->|No| RAISE[raise_for_status]
    RAISE --> READ[Read resp.content]
    
    READ --> TAR_TRY{try tarfile}
    TAR_TRY -->|Exception| TAR_ERR([return error LayerPeekResult])
    TAR_TRY -->|Success| OPEN_TAR[tarfile.open r:gz]
    OPEN_TAR --> LOOP[For member in tar]
    LOOP --> TYPE{typeflag?}
    TYPE --> CONVERT[_tarinfo_mode_to_string]
    CONVERT --> CREATE[Create TarEntry]
    CREATE --> APPEND[Append to entries]
    APPEND --> MORE{more members?}
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN([return LayerPeekResult])
```

### peek_layer_blob_partial (394-519)

```mermaid
flowchart TD
    START([image_ref, digest, token, initial_bytes]) --> PARSE[parse_image_ref]
    PARSE --> TOK_CHK{token?}
    TOK_CHK -->|No| GET_TOK[fetch_pull_token]
    TOK_CHK -->|Yes| BUILD
    GET_TOK --> BUILD[Build URL with Range header]
    BUILD --> TOK_CHK2{token?}
    TOK_CHK2 -->|Yes| SET_AUTH[Add Authorization]
    TOK_CHK2 -->|No| TRY
    SET_AUTH --> TRY
    
    TRY{try request}
    TRY -->|RequestException| ERR_REQ([return error result])
    TRY -->|Success| REQ1[requests.get with Range]
    REQ1 --> AUTH{status == 401?}
    AUTH -->|Yes| RETRY_TOK[fetch_pull_token]
    RETRY_TOK --> RETRY_CHK{token?}
    RETRY_CHK -->|Yes| REQ2[requests.get retry]
    RETRY_CHK -->|No| RAISE
    REQ2 --> RAISE
    AUTH -->|No| RAISE[raise_for_status]
    RAISE --> READ[raw.read initial_bytes]
    READ --> CLOSE[resp.close]
    
    CLOSE --> MAGIC{gzip magic 0x1f 0x8b?}
    MAGIC -->|No| ERR_MAGIC([return error: not gzip])
    MAGIC -->|Yes| DECOMP{try decompress}
    DECOMP -->|zlib.error| ERR_ZLIB([return decompression error])
    DECOMP -->|Success| SIZE_CHK{len >= 512?}
    SIZE_CHK -->|No| ERR_SIZE([return: not enough data])
    SIZE_CHK -->|Yes| LOOP[While offset + 512 <= len]
    
    LOOP --> PARSE_HDR[parse_tar_header]
    PARSE_HDR --> HDR_CHK{entry is None?}
    HDR_CHK -->|Yes| RETURN([return LayerPeekResult])
    HDR_CHK -->|No| APPEND[Append entry]
    APPEND --> OFFSET_CHK{next_offset valid?}
    OFFSET_CHK -->|No| RETURN
    OFFSET_CHK -->|Yes| UPDATE[offset = next_offset]
    UPDATE --> MORE{offset + 512 <= len?}
    MORE -->|Yes| LOOP
    MORE -->|No| RETURN
```

### layerslayer (655-736)

```mermaid
flowchart TD
    START([image_ref, layers, token, progress_callback]) --> PARSE[parse_image_ref]
    PARSE --> FILTER[Filter layers with digests]
    FILTER --> EMPTY{layer_info empty?}
    EMPTY -->|Yes| ERR_RESULT([return error: no layers])
    EMPTY -->|No| TOK_CHK{token?}
    TOK_CHK -->|No| GET_TOK[fetch_pull_token]
    TOK_CHK -->|Yes| LOOP
    GET_TOK --> LOOP
    
    LOOP[For i, digest, size in layer_info] --> CALLBACK{progress_callback?}
    CALLBACK -->|Yes| CALL_PROG[Call progress]
    CALLBACK -->|No| PEEK
    CALL_PROG --> PEEK[peek_layer_blob_complete]
    PEEK --> APPEND_RES[Append to layer_results]
    APPEND_RES --> ADD_BYTES[total_bytes += downloaded]
    ADD_BYTES --> ERR_CHK{result.error?}
    ERR_CHK -->|No| EXTEND[Extend all_entries]
    ERR_CHK -->|Yes| MORE
    EXTEND --> MORE{more layers?}
    MORE -->|Yes| LOOP
    MORE -->|No| DONE_CB{progress_callback?}
    DONE_CB -->|Yes| CALL_DONE[Call Done progress]
    DONE_CB -->|No| RETURN
    CALL_DONE --> RETURN([return LayerSlayerResult])
```

### Helper Functions

```mermaid
flowchart TD
    subgraph TarinfoMode["_tarinfo_mode_to_string (368-379)"]
        TM_START([mode, typeflag]) --> TYPE_CHAR[Map typeflag to d/l/-]
        TYPE_CHAR --> LOOP[For shift in 6,3,0]
        LOOP --> BITS[Extract 3 bits]
        BITS --> R{bit 4?}
        R -->|Yes| ADD_R[+= r]
        R -->|No| ADD_RD[+= -]
        ADD_R --> W{bit 2?}
        ADD_RD --> W
        W -->|Yes| ADD_W[+= w]
        W -->|No| ADD_WD[+= -]
        ADD_W --> X{bit 1?}
        ADD_WD --> X
        X -->|Yes| ADD_X[+= x]
        X -->|No| ADD_XD[+= -]
        ADD_X --> MORE{more shifts?}
        ADD_XD --> MORE
        MORE -->|Yes| LOOP
        MORE -->|No| TM_RET([return type_char + perms])
    end
    
    subgraph FormatMtime["_format_mtime (382-391)"]
        FM_START([unix_timestamp]) --> TRY{try}
        TRY --> NEG{timestamp <= 0?}
        NEG -->|Yes| DASH([return dashes])
        NEG -->|No| CONVERT[datetime.fromtimestamp]
        CONVERT --> FORMAT([return strftime])
        TRY -->|OSError/ValueError/Overflow| DASH
    end
```

## Summary of Branch Points

| Location | Condition | Branches |
|----------|-----------|----------|
| Line 97-101 | `requests.get` exception | Return None or continue |
| Line 104-106 | `token` in response | Return None or save and return |
| Line 129-130 | `token` provided | Set auth header or skip |
| Line 133-139 | `status_code == 401` | Refresh token or continue |
| Line 141-145 | Still 401 after retry | SystemExit(1) or continue |
| Line 159-165 | `status_code == 401` | Refresh token or continue |
| Line 173-174 | `empty_layer` flag | Add metadata tag or not |
| Line 191-197 | `status_code == 401` | Refresh token or continue |
| Line 230-236 | `token` provided/fetched | Set auth header or not |
| Line 239-244 | `status_code == 401` | Refresh and retry or continue |
| Line 253-257 | `member.isdir()` | Print [DIR] or [FILE] |
| Line 284-285 | `token` provided | Fetch new token or use existing |
| Line 291-292 | `token` available | Set auth header or skip |
| Line 298-302 | `status_code == 401` | Refresh and retry or continue |
| Line 306-315 | `RequestException` | Return error result |
| Line 329 | `typeflag` | Map to d/l/- character |
| Line 356-365 | Tar extraction exception | Return error result |
| Line 386-387 | `timestamp <= 0` | Return dashes |
| Line 390 | `OSError/ValueError/Overflow` | Return dashes |
| Line 419-420 | `token` provided | Fetch new or use existing |
| Line 429-430 | `token` available | Set auth header or skip |
| Line 436-440 | `status_code == 401` | Refresh and retry |
| Line 448-457 | `RequestException` | Return error result |
| Line 460-469 | Gzip magic check | Return error if not gzip |
| Line 475-484 | `zlib.error` | Return decompression error |
| Line 486-495 | Decompressed size < 512 | Return insufficient data error |
| Line 503-510 | `entry is None` or offset invalid | Break parse loop |
| Line 684-693 | Empty `layer_info` | Return error result |
| Line 696-697 | `token` provided | Fetch new or use existing |
| Line 705-706 | `progress_callback` | Call callback or skip |
| Line 719-720 | `result.error` | Skip extending entries |
| Line 722-723 | `progress_callback` | Call done callback or skip |

## Authentication Retry Pattern

All network functions follow the same authentication retry pattern:

```mermaid
flowchart LR
    REQ[Initial Request] --> CHK{401?}
    CHK -->|No| CONTINUE[Continue processing]
    CHK -->|Yes| REFRESH[fetch_pull_token]
    REFRESH --> GOT{Got token?}
    GOT -->|Yes| RETRY[Retry request]
    GOT -->|No| WARN[Print warning, continue]
    RETRY --> CONTINUE
    WARN --> CONTINUE
```