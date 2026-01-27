# Task - Migrate Search into Left Panel
Move the search widget into the main viewport, left panel.

## Problem Statement UI Is imbalanced

- I want to give the application TUI more visual symmetry. 
-To do this I will move the Search-Input and Search-status widgets to the LeftPanel.
- `#top-panel` should now be empty, collapse to `0` height; 
    - Or Remove, **if safe to remove**

![mockup of migration](/docs/move-search.png)


This code block from [/app/tui/style.tcss](/app/tui/style.tcss):9-31 is for search widgets out of `#top-panel` to [left-spacer](#left-spacer)

```css
/* TODO When search is fully migrated to the Left Panel, the top Panel will not be needed
/* Top panel - flows below header in vertical layout (not docked) */
#top-panel {
    height: auto;
    min-height: 5;
    padding: 1 2;
    background: $surface;
    border: solid $primary;
    layout: vertical;
}

/* TODO Move #search-input and #search-status to the space currently occupied by #left-spacer
/* Search input styling */
#search-input {
    width: 100%;
    margin-bottom: 1;
}

/* Search status text */
#search-status {
    height: auto;
    color: $text-muted;
}
```

And move to place currently occupied by placeholder widget 

####left-spacer

lines: 58-62
```css
/* TODO Move search input Widget to the space occupied by #left-spacer
/* Spacer to align with right panel widgets */
#left-spacer {
    height: 9;
}
```