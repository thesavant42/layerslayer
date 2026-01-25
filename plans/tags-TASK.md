

# Task 1 - Tabbed Content on the Left Side Panel

I would like the Left panel to be a tabbedContent panel like the Right Side.

The right side has this code:
```python
class RightPanel(Static):
    """Right panel widget with tabbed content for repo details."""
    
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Repo Overview", id="repo-overview"):
                yield Static("Select a repository to view tags", id="repo-info")
                yield Select([], id="tag-select", prompt="Select a tag...")
                yield DataTable(id="config-table", cursor_type="row")
```

- 1. I would like a tab for the results table widget
- 2. I would like a tab on the left side "FileSystem Info"


# Task 2 - Move search bar

I'd like the to move the Docker Hub Search input to the `Left-Panel`, the "Results" panel

```python
    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Search Docker Hub...",
            id="search-input",
            type="text"
        )
        yield Static("", id="search-status")
```

![Imbalanced panels](/plans/current.png)

---

