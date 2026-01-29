## Problem statement:

The description needs to be vieweable in a non-truncated state, but this forces the need for horizontal scroll by defauly on the search widget. There's plenty of unused space beneath the datatable, above the pagination component. 

Widget: search_panel
- [search_panel.py](/app/tui/widgets/search_panel/search_panel.py)

## Proposal:
Use the free space to print the untrancated slug and description. Let them wrap.

### Requirements
New container widget 
    - the full width of the viewport,
    - beneath the #results-table widget
    - Above the pagination widget
    - fully inside of the rectangular border

- The SearchPanel is currently structured as a vertical flow with these components:
    - #search-label - Static title "Search Docker Hub"
    - #search-input - Input field with placeholder
    - #search-status - Empty Static for status messages
    - #results-table - DataTable with height: 1fr (fills available space)
    - #pagination-container - Centered Horizontal bar with buttons and status

- The geometry is currently fluid - the table uses 1fr to fill remaining space, and the pagination is fixed at 3 rows tall

I want to add the text rows above the #pagination-container and under the #results-table, inside of the border rectangle that frames the widget

### Details
- Row 1: Slug, no truncation, enable wrap. 
- Row 2: Description, no truncation

### Activation
- When a row has been `highlighted` in the data table,
    - update the two rows beneath the table to display:
        - Row 1 Slug
        - Row 2 Description
- Updates as user scrolls through results