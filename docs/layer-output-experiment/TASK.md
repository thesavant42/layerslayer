# Task: Store and Print Layer Peek data


I want to store the results of scraping the filesystem data from the image layer digests.

In addition to the existing workflow, I would like to store the peeked layer info as json objects.

# store fs layer info as json on disk
- Save to  loot/ as
    - owner-repo-tag-fslyr-34-MMDDYYYY.json
        - where owner, repo, tag, and filesystem layer number are from the data
        - the data is to add some order for multiple saves


# Also store results to a sqlite database
- Storing to a sqlite database allows for:
    - generating reports,
    - searching
    - sorting by column attribute
    - filtering

- `app\modules\keepers\storage.py` created
- need to wire into `app\modules\keepers\layerSlayerResults.py`
- **all layer peek data is now cached in sqlite and json.**







** DO NOT READ PAST HERE/**
----


# Phase 2

I need a way to navigate the virtual directory structure. To do this, a basic textual datable makes the most sense

### Displaying and navigating via a Textual dataTable
- https://textual.textualize.io/widgets/data_table/

### Make the rows easier to read
- https://textual.textualize.io/widgets/data_table/#textual.widgets.DataTable(zebra_stripes) true

### Enable Sorting
- https://textual.textualize.io/widgets/data_table/#sorting

### Use a Row cursor
https://textual.textualize.io/widgets/data_table/#textual.widgets.DataTable.cursor_row

Print out the filesystem, using patterns for print info used by [the FS Faker experiment](docs\layer-output-experiment\fs-faker-results.md)
- Allow the page to scroll 
- **do not prohibit the columns from stretching to avoid overflow or wrapping**.
- render ".."  to allow reverse directory traversal
