# Store Image Configs to SQLite - Detailed Plan

## Background

### Phase 4: Carve Integration
- [ ] Update [`carve_file_to_bytes()`](app/modules/keepers/carver.py:553) to check `image_layers` table

---

## Benefits

1. **Reduced upstream requests**: Config fetched once, reused
2. **Layer count known upfront**: No out-of-range errors
3. **Peek progress visible**: UI can show which layers have been reviewed
4. **IDX mapping solved**: `/peek/status` provides the mapping
5. **OSINT audit trail**: Track what was investigated and when

---

## Relationship to Existing Tables

Current tables:
- `layer_metadata` - stores peek results (digest, size, entry counts)
- `layer_entries` - stores filesystem entries from peeked layers

New tables:
- `image_configs` - stores the image config JSON and metadata
- `image_layers` - tracks peek status per layer, references config

The new `image_layers` table provides the idx-to-digest mapping that `layer_metadata` lacks at the image level. Both can coexist:
- `image_layers`: "what layers does this image have, and have they been peeked?"
- `layer_metadata`: "details about a specific peeked layer"
- `layer_entries`: "filesystem entries within a layer"
