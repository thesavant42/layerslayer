from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
from datetime import datetime


@dataclass
class The11434TCP:
    pass


@dataclass
class ExposedPorts:
    the_11434_tcp: The11434TCP


@dataclass
class Labels:
    com_nvidia_cudnn_version: str
    maintainer: str
    org_opencontainers_image_ref_name: str
    org_opencontainers_image_version: str


@dataclass
class Conconfig:
    hostname: str
    domainname: str
    user: str
    attach_stdin: bool
    attach_stdout: bool
    attach_stderr: bool
    exposed_ports: ExposedPorts
    tty: bool
    open_stdin: bool
    stdin_once: bool
    env: List[str]
    cmd: List[str]
    image: str
    volumes: None
    working_dir: str
    entrypoint: List[str]
    on_build: None
    labels: Labels
    shell: List[str]


class Comment(Enum):
    BUILDKIT_DOCKERFILE_V0 = "buildkit.dockerfile.v0"


@dataclass
class History:
    created: datetime
    created_by: str
    empty_layer: Optional[bool] = None
    comment: Optional[Comment] = None


@dataclass
class Rootfs:
    type: str
    diff_ids: List[str]


@dataclass
class Config:
    architecture: str
    config: Conconfig
    container: str
    container_config: Conconfig
    created: datetime
    docker_version: str
    history: List[History]
    os: str
    rootfs: Rootfs
