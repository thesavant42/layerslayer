# fetcher.py
#  Layerslayer registry fetch helpers with resilient token handling
#  Includes streaming layer peek using HTTP Range requests

import os
import zlib
import requests
import tarfile
import io
from dataclasses import dataclass, field
from typing import Optional, Callable, Generator, List

from utils import (
    parse_image_ref,
    registry_base_url,
    human_readable_size,
    save_token,
)
from tar_parser import TarEntry, parse_tar_header

# Persistent session to reuse headers & TCP connections for registry calls
session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
})


