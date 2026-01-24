
# App crash on peek
Critical bug in primary user flow.


## Problem Statement: The app crashes when attempting to pull layers.

- This happened after the most recent changes to [api.py](./app/modules/api/api.py) to make idx layers a **mandatory** field before downloading.
- When image configs are downloaded into the image config table [storage.py](./app/modules/keepers/storage.py)
they set a status of "has not been peeked" regardless of what's in the database.
- When I attempt to peek all layers to set them in the database, this [exception](###Exception) is thrown.

## What Should happen?
- Ideally the database contents would have been checked before setting the peek status.
    - Is there already contents in the database for that layer digest? Yes? status is peeked.
    - Not yet? Not peeked.
- If I request to /peek a layer IDX, it should do that. and then update the databasre to indicate that it's been done.


### Currently
- There is no verification
- there's no verbose debug printing to tell the user what's hapepning (on the console or anywhere else)
- app crashes when I try to download.

Commit https://github.com/thesavant42/layerslayer/commit/49704afe50611fbc9d9c19ead20d2a629c6df412.diff
- Plan to fix it
Commit that broke it: https://github.com/thesavant42/layerslayer/commit/849f6c1ac14ddc8ce55d401655009fb908f9a1e5.diff

The API sends 6 parameters, including IDX, but the  `update_layer_peeked()` function currently expects 4.

##3 Steps to reproduce: Attempt to /peek and leave all the default. I used the swagger docs.



### Exception

```bash
    127.0.0.1:30130 - "GET /peek?image=drichnerdisney%2Follama%3Av1&layer=all&arch=0&hide_build=false&status_only=false HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\jbras\miniconda3\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 416, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\middleware\exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\middleware\asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\routing.py", line 101, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\routing.py", line 355, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\fastapi\routing.py", line 245, in run_endpoint_function
    return await run_in_threadpool(dependant.call, **values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\starlette\concurrency.py", line 32, in run_in_threadpool
    return await anyio.to_thread.run_sync(func)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\anyio\to_thread.py", line 63, in run_sync
    return await get_async_backend().run_sync_in_worker_thread(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        func, args, abandon_on_cancel=abandon_on_cancel, limiter=limiter
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\anyio\_backends\_asyncio.py", line 2502, in run_sync_in_worker_thread
    return await future
           ^^^^^^^^^^^^
  File "C:\Users\jbras\miniconda3\Lib\site-packages\anyio\_backends\_asyncio.py", line 986, in run
    result = context.run(func, *args)
  File "C:\Users\jbras\GitHub\lsng\app\modules\api\api.py", line 539, in peek
    update_layer_peeked(conn, namespace, repo, tag, arch_str, idx)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: update_layer_peeked() takes from 3 to 4 positional arguments but 6 were given

```
