# Docker Hub Flat-Array JSON Parser

## Data Structure

Flat JSON array where `{"_N": M}` means: key name is `data[N]`, value is `data[M]`

Negative M values = null

## Parser

```python
import json

def resolve(data, idx):
    if isinstance(idx, int):
        if idx < 0:
            return None
        idx = data[idx]
    
    if isinstance(idx, dict):
        obj = {}
        for k, v in idx.items():
            if k.startswith('_'):
                obj[data[int(k[1:])]] = resolve(data, v)
        return obj
    
    if isinstance(idx, list):
        return [resolve(data, i) for i in idx]
    
    return idx

def get_results(data):
    for i, v in enumerate(data):
        if v == "searchResults":
            sr = resolve(data, data[i + 1])
            return sr.get('results', [])
    return []

# Test
with open('plans/search/search.data/yahoo-search.data.json') as f:
    data = json.load(f)

for r in get_results(data):
    print(r.get('id'), r.get('pull_count'), r.get('publisher', {}).get('name'))
```

## Output Fields

| slug | star_count | pull_count | publisher.name | created_at | updated_at | short_description |

Dates: MM-DD-YYYY, no truncation
