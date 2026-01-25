# Enumerate Tags into Select Widget

## User Story

Picking up in the user story, we have searched for a query and returned a data table of repositories. 

---


When I find a repository I want to investigate I need to enumerate the available `TAGs` for a repository.


### Enumerating Tags
The API route to do this is `/repositories/{namespace}/{repo}/tags`

To enunerate tags for the `nginx` repository in the `library` catalog, and to account for pagination and ordering, the full request URL would be:

`http://localhost:8000/repositories/library/nginx/tags?page=1&page_size=30&ordering=last_updated`
- page 1
- page size = 30 results per page
- ordering = last_updated

Returns: **1,0231 tags**
- Will need pagination

```json
{
  "count": 1021,
  "next": "https://hub.docker.com/v2/repositories/library/nginx/tags?ordering=last_updated&page=2&page_size=30",
  "previous": null,
  "results": [
    {
      "creator": 1156886,
      "id": 987274600,
      "images": [
        {
          "architecture": "amd64",
          "features": "",
          "variant": null,
          "digest": "sha256:f3524ef8b8746145d97e06b96554e32398b82f90500220d431950d7d1a3a043f",
          "os": "linux",
          "os_features": "",
          "os_version": null,
          "size": 75009095,
          "status": "active",
          "last_pulled": "2026-01-25T02:37:50.940976192Z",
          "last_pushed": "2026-01-13T06:52:14.349887969Z"
        },
[...coninues...]
```
 
The respponse includes:
 - count of tags
 - Next - the pagination bread crumbs indicating there are more results on the next page
 - previous - the pagination bread crumbs indicating there are more results on the previous page
 - metadata per tag...

---

When I find a repository I want to enumerate and highlight the the reult in the results panel in the lower left portion of the screen.  I press hit enter to initiate enumeration.


The Right-Panel should be converted to a ['TabbedContent'](/plans/docs/tabbed_content.md) textual widget. 
Tab 1: Repo Overview 
- Select Widget populated with the layer's tags, sorted by recently updated. 
- Selecting a tag from the select widget must retrieve the Image Config Manifest for that Tag. 
    - `/repositories/{namespace}/{repo}/tags/{tag}/config`
    - http://localhost:8000/repositories/drichnerdisney/ollama/tags/v1/config?force_refresh=false
    - Full json response: [here](/plans/docs/config-example.json) 
    
 - Build Config Contains array of layer images to peek `/peek`

Links: [Swagger Doc](/plans/docs/openapi.json)
