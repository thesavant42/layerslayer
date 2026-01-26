# User Story : simulated file system, aka layer peeking

## Story so far
I want to find a specific file among a collection of docker hub containers.

I search using the search widget, I click the results of the repo I want to enumerate and the tags are populated. When I use the Select widget I choose a tag, and the imaage config build manifest is displayed, and ends in a list of sha256 digests, one for each layer.

## New Story component: peeking layers and viewing the fslog of the results.
(using drichnerdisnet/ollama:v1 as example.
)
- 1. When I scroll and see the digest of layers available, I select one of them and hit enter. 
    - which kicks off the following sequence:
        - Check to see if layer has already been peeked by issing a status check to the API:
            `http://localhost:8000/peek?image=drichnerdisney%2Follama%3Av1&layer=36&arch=0&hide_build=false&status_only=true`
            - If it has been peeked already the layer status will indicate true for any layer that has already been peeked:

```json
{
  "image": "drichnerdisney/ollama:v1",
  "config_digest": "sha256:ca8d937e089ff0c435b1166a42e7661bb02feb67e31a2eea952751da1c175c33",
  "config_cached": true,
  "layer_count": 37,
  "layers": [
    {
      "idx": 0,
      "digest": "sha256:5a7813e071bfadf18aaa6ca8318be4824a9b6297b3240f2cc84c1db6f4113040",
      "size": 29754290,
      "peeked": true,
      "peeked_at": "2026-01-23T17:06:57.513895",
      "entries_count": 0
[]...truncated for demonstrating to the AI the otput]
  ],
  "peeked_count": 37,
  "unpeeked_count": 0
}
```
 - **Key insight**: Layers are peeked individually
     - The same file can exist in multiple layers
     - We want to investigate all versions, so do not make any assunptions about what to keep
- **Key Insight** Only layers that have been peeked can be Viewed
    - If it has NOT been peeked, it must first be peeked, and can then be viewed.
    - Only the requested layer may be peeked.


- 2. If the layer has *not been cached*, **it must be "peeked"**: (Example request for layer idx[36])
`http://localhost:8000/peek?image=drichnerdisney%2Follama%3Av1&layer=36&arch=0&hide_build=false&status_only=false`

![example of output of peek layer 36](/plans/peek-output.png)

This process does not need to be visible to the end user; It can happen in the background as the user is directed to the "FileSystem Simulation" Tab.

## Viewing Layer Filesystems

/fslog displays the output of the sqlite database's peek layer contents. 

`http://localhost:8000/fslog?image=drichnerdisney%2Follama%3Av1&path=%2F&layer=0` 
### Example layer 0 output
```bash
lrwxrwxrwx       0.0 B  2024-04-22 06:08  bin -> usr/bin
drwxr-xr-x       0.0 B  2024-04-22 06:08  boot/
drwxr-xr-x       0.0 B  2025-01-26 18:09  dev/
drwxr-xr-x       0.0 B  2025-01-26 18:09  etc/
drwxr-xr-x       0.0 B  2025-01-26 18:09  home/
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib -> usr/lib
lrwxrwxrwx       0.0 B  2024-04-22 06:08  lib64 -> usr/lib64
drwxr-xr-x       0.0 B  2025-01-26 18:03  media/
drwxr-xr-x       0.0 B  2025-01-26 18:03  mnt/
drwxr-xr-x       0.0 B  2025-01-26 18:03  opt/
[]...]
```

This is a backstop file system display that utilizes the correct tables in the sqlite database, but does not return structured data, it's not yet a widget.

The fsslog-sqlite file has patterns that can be learned from and copied into a proper filesystem simulation widget dataTable with a row cursor.

### Navigation

By altering the {path} argumwent of fslog I can change the folder of the output. 
`http://localhost:8000/fslog?image=drichnerdisney/ollama:v1&path=/etc&layer=0`

#### Example: /etc

```bash
-rw-------       0.0 B  2025-01-26 18:03  .pwd.lock
drwxr-xr-x       0.0 B  2025-01-26 18:09  alternatives/
drwxr-xr-x       0.0 B  2025-01-26 18:03  apt/
-rw-r--r--      2.3 KB  2024-03-31 01:41  bash.bashrc
-rw-r--r--     367.0 B  2022-08-02 08:34  bindresvport.blacklist
drwxr-xr-x       0.0 B  2025-01-26 18:09  cloud/
drwxr-xr-x       0.0 B  2025-01-26 18:09  cron.d/
drwxr-xr-x       0.0 B  2025-01-26 18:09  cron.daily/
[...]
```

### Viewing All Layers at once

- By **not** providing a layer idx value, all layers will be displayed in a unified output.
    - `http://localhost:8000/fslog?image=drichnerdisney/ollama:v1&path=/`
    - A file that is superceded by a later layer is marked as `overridden`, but is still addressable. 
    - Symbolic links are indicated as such and can be followed to their intended destination.

### Example of overridden output

```bash
drwxr-xr-x       0.0 B  2025-10-08 22:11  etc/                                               [L15] (overridden)
drwxr-xr-x       0.0 B  2025-10-08 22:07  etc/                                               [L14] (overridden)
drwxr-xr-x       0.0 B  2025-10-08 22:07  etc/                                               [L13] (overridden)
```

## Key Insight:
- Multiple layers can be viewed at once
- The fslog-sqlite.py file is a backstop that produces plain text output
    - If raw json is needed, this will require SLIGHT refactoring to use the json unformatted.
- End user does not need to see the results of the peek process
    - Should still be present in the console logs



## Where to print this output?
Where will fslog output be displayed?

- New tab for tabbedcontent on `LeftPanel` - "FS Simulator"
    - dataTable with row cursor, zebra mode, etc.
    - Need to add in '..' directory breadcrumbs to navigate "back" a directory.

- [x] Task: Add New Tab to LeftPanel with a /fslog dataTable Widget
- [x] When I click enter on a sha256:digest from an Image Config manifest in the RightPanel, it should trigger a pre-flight check and and peek if necessary, then populate the widget

**COMPLETED**

---

## Saving Files (User Story Continued...)

- Once I've found the repository image I want to investigate (**for this example: drichnerdisney/ollama:v1**) and I've `/peeked` and seen the `/fslog` in the previous step, I've identified files that I want to save.

- The LSNG API offers two options to download a file: 
    - 1. saving as bytes as a typical download,
    - 2. or streamed as plain text to be viewed in the panel as a richlog widget

1. Streams the file to the browser in the REST API, with raw bytes and setting the content type as appropriate. 
    - http://localhost:8000/carve?image=drichnerdisney/ollama:v1&path=/root/.ollama/id_ed25519&layer=36`
2. For plain text, if I just want to view the contents and dont care if I save it, I can just call it like tjis, setting `as_text=true`
http://localhost:8000/carve?image=drichnerdisney/ollama:v1&path=/root/.ollama/id_ed25519&layer=36&as_text=true` 

The contents are displayed as normal text:

```txt
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtz
c2gtZWQyNTUxOQAAACD3xkzhNvDMoOMyZ/KAhXv8qPaaYRJh+zgCFCNUMtePAQAA
AIiAJ6IvgCeiLwAAAAtzc2gtZWQyNTUxOQAAACD3xkzhNvDMoOMyZ/KAhXv8qPaa
YRJh+zgCFCNUMtePAQAAAEDxlxOO+I7spFclH2Gq8cKpUcdSR56GPDRZxiCKutGu
RPfGTOE28Myg4zJn8oCFe/yo9pphEmH7OAIUI1Qy148BAAAAAAECAwQF
-----END OPENSSH PRIVATE KEY-----
```

### Saving Binary Files in textual

The following is asked from deepwiki reguarding saving files in textual:


# DeepWiki Q&A with Code Context for Repository: Textualize/textual
## Q1
how can I save a file stream in textual? If I've got the raw bytes from a file stream.
### Answer
To save a file stream from raw bytes in Textual, you can use the `App.deliver_binary()` method which handles file delivery in both terminal and web environments.

## Quick Answer

```python
# Assuming you have raw bytes in a file-like object
import io
from pathlib import Path

# Create a binary stream from your raw bytes
raw_bytes = b"your raw file data here"
binary_stream = io.BytesIO(raw_bytes)

# Deliver the file - works in both terminal and web
delivery_key = app.deliver_binary(
    binary_stream,
    save_filename="myfile.bin",
    save_directory="./downloads"
)
```

## Detailed Explanation

Textual provides a unified file delivery system through the `App.deliver_binary()` method textual:4716-4768 . This method accepts:

- `path_or_file`: A file path or `BinaryIO` object containing your raw bytes
- `save_directory`: Where to save the file (defaults to downloads)
- `save_filename`: The filename to use
- `open_method`: "browser" or "download" (web only)
- `mime_type`: Optional MIME type
- `name`: Optional identifier for tracking

The method internally calls `_deliver_binary()` textual:4796-4836  which:
1. Generates a unique delivery key
2. Determines the save location
3. Delegates to the driver's `deliver_binary()` method

The actual file saving is handled by the driver implementation. The base `Driver.deliver_binary()` method textual:208-277  saves files in a separate thread using chunked reads, making it efficient for large streams:

```python
def save_file_thread(binary: BinaryIO | TextIO, mode: str) -> None:
    with open(save_path, mode, encoding=encoding or "utf-8") as destination_file:
        chunk_size = 1024 * 64
        while True:
            data = binary.read(chunk_size)
            if not data:
                break
            destination_file.write(data)
```

## Environment-Specific Behavior

- **Terminal**: Files are saved directly to the specified directory textual:56-58 
- **Web Browser**: Files are streamed via an ephemeral download URL textual:58-59 

The system automatically handles the appropriate delivery method based on whether the app is running in a terminal or via `textual-serve` in a web browser.

## Notes

- The file stream will be closed by the delivery system after use
- For text content, consider using `App.deliver_text()` instead
- Delivery completion can be tracked via `DeliveryComplete` events textual:4838-4848 


### Citations
**File:** src/textual/app.py (L4716-4768)
```python
    def deliver_binary(
        self,
        path_or_file: str | Path | BinaryIO,
        *,
        save_directory: str | Path | None = None,
        save_filename: str | None = None,
        open_method: Literal["browser", "download"] = "download",
        mime_type: str | None = None,
        name: str | None = None,
    ) -> str | None:
        """Deliver a binary file to the end-user of the application.

        If an IO object is supplied, it will be closed by this method
        and *must not be used* after it is supplied to this method.

        If running in a terminal, this will save the file to the user's
        downloads directory.

        If running via a web browser, this will initiate a download via
        a single-use URL.

        This operation runs in a thread when running on web, so this method
        returning does not indicate that the file has been delivered.

        After the file has been delivered, a `DeliveryComplete` message will be posted
        to this `App`, which contains the `delivery_key` returned by this method. By
        handling this message, you can add custom logic to your application that fires
        only after the file has been delivered.

        Args:
            path_or_file: The path or file-like object to save.
            save_directory: The directory to save the file to. If None,
                the default "downloads" directory will be used. This
                argument is ignored when running via the web.
            save_filename: The filename to save the file to. If None, the following logic
                applies to generate the filename:
                - If `path_or_file` is a file-like object, the filename will be taken from
                  the `name` attribute if available.
                - If `path_or_file` is a path, the filename will be taken from the path.
                - If a filename is not available, a filename will be generated using the
                  App's title and the current date and time.
            open_method: The method to use to open the file. "browser" will open the file in the
                web browser, "download" will initiate a download. Note that this can sometimes
                be impacted by the browser's settings.
            mime_type: The MIME type of the file or None to guess based on file extension.
                If no MIME type is supplied and we cannot guess the MIME type, from the
                file extension, the MIME type will be set to "application/octet-stream".
            name: A user-defined named which will be returned in [`DeliveryComplete`][textual.events.DeliveryComplete]
                and [`DeliveryComplete`][textual.events.DeliveryComplete].

        Returns:
            The delivery key that uniquely identifies the file delivery.
        """
```
**File:** src/textual/app.py (L4796-4836)
```python
    def _deliver_binary(
        self,
        binary: BinaryIO | TextIO,
        *,
        save_directory: str | Path | None,
        save_filename: str | None,
        open_method: Literal["browser", "download"],
        encoding: str | None = None,
        mime_type: str | None = None,
        name: str | None = None,
    ) -> str | None:
        """Deliver a binary file to the end-user of the application."""
        if self._driver is None:
            return None

        # Generate a filename if the file-like object doesn't have one.
        if save_filename is None:
            save_filename = generate_datetime_filename(self.title, "")

        # Find the appropriate save location if not specified.
        save_directory = (
            user_downloads_path() if save_directory is None else Path(save_directory)
        )

        # Generate a unique key for this delivery
        delivery_key = str(uuid.uuid4().hex)

        # Save the file. The driver will determine the appropriate action
        # to take here. It could mean simply writing to the save_path, or
        # sending the file to the web browser for download.
        self._driver.deliver_binary(
            binary,
            delivery_key=delivery_key,
            save_path=save_directory / save_filename,
            encoding=encoding,
            open_method=open_method,
            mime_type=mime_type,
            name=name,
        )

        return delivery_key
```
**File:** src/textual/app.py (L4838-4848)
```python
    @on(events.DeliveryComplete)
    def _on_delivery_complete(self, event: events.DeliveryComplete) -> None:
        """Handle a successfully delivered screenshot."""
        if event.name == "screenshot":
            if event.path is None:
                self.notify("Saved screenshot", title="Screenshot")
            else:
                self.notify(
                    f"Saved screenshot to [$text-success]{str(event.path)!r}",
                    title="Screenshot",
                )
```
**File:** src/textual/driver.py (L208-277)
```python
    def deliver_binary(
        self,
        binary: BinaryIO | TextIO,
        *,
        delivery_key: str,
        save_path: Path,
        open_method: Literal["browser", "download"] = "download",
        encoding: str | None = None,
        mime_type: str | None = None,
        name: str | None = None,
    ) -> None:
        """Save the file `path_or_file` to `save_path`.

        If running via web through Textual Web or Textual Serve,
        this will initiate a download in the web browser.

        Args:
            binary: The binary file to save.
            delivery_key: The unique key that was used to deliver the file.
            save_path: The location to save the file to.
            open_method: *web only* Whether to open the file in the browser or
                to prompt the user to download it. When running via a standard
                (non-web) terminal, this is ignored.
            encoding: *web only* The text encoding to use when saving the file.
                This will be passed to Python's `open()` built-in function.
                When running via web, this will be used to set the charset
                in the `Content-Type` header.
            mime_type: *web only* The MIME type of the file. This will be used to
                set the `Content-Type` header in the HTTP response.
            name: A user-defined name which will be returned in [`DeliveryComplete`][textual.events.DeliveryComplete]
                and [`DeliveryFailed`][textual.events.DeliveryFailed].

        """

        def save_file_thread(binary: BinaryIO | TextIO, mode: str) -> None:
            try:
                with open(
                    save_path, mode, encoding=encoding or "utf-8"
                ) as destination_file:
                    read = binary.read
                    write = destination_file.write
                    chunk_size = 1024 * 64
                    while True:
                        data = read(chunk_size)
                        if not data:
                            # No data left to read - delivery is complete.
                            self._delivery_complete(
                                delivery_key, save_path=save_path, name=name
                            )
                            break
                        write(data)
            except Exception as error:
                # If any exception occurs during the delivery, pass
                # it on to the app via a DeliveryFailed event.
                log.error(f"Failed to deliver file: {error}")
                import traceback

                log.error(str(traceback.format_exc()))
                self._delivery_failed(delivery_key, exception=error, name=name)
            finally:
                if not binary.closed:
                    binary.close()

        if isinstance(binary, BinaryIO):
            mode = "wb"
        else:
            mode = "w"

        thread = threading.Thread(target=save_file_thread, args=(binary, mode))
        thread.start()
```
**File:** docs/blog/posts/textual-serve-files.md (L56-59)
```markdown
When accessing a Textual app using a terminal, these methods will write a file to disk, and notify the `App` when the write is complete.

In the browser, however, a download will be initiated and the file will be streamed via an ephemeral (one-time) download URL from the server that the Textual app is running on to the end-user's browser. If the app developer wishes, they can specify a custom file name, MIME type, and even whether the browser should attempt to open the file in a new tab or be downloaded.

```