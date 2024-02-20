import os
from typing import Callable, Coroutine

from git import Repo

from app.utils import Str


class Cmd(Str):
    def __init__(self, cmd: str, func: Callable, path: str, sudo: bool):
        self.cmd: str = cmd
        self.func: Callable = func
        self.path: str = path
        self.dirname: str = os.path.basename(os.path.dirname(path))
        self.doc: str = func.__doc__ or "Not Documented."
        self.sudo: bool = sudo


class Config:
    BOT_NAME = "Debrid-Bot"

    CMD = Cmd

    CMD_DICT: dict[str, Cmd] = {}

    CMD_TRIGGER: str = os.environ.get("CMD_TRIGGER", ".")

    DEV_MODE: int = int(os.environ.get("DEV_MODE", 0))

    DISABLED_SUPERUSERS: list[int] = []

    INIT_TASKS: list[Coroutine] = []

    LOG_CHAT: int = int(os.environ.get("LOG_CHAT"))

    OWNER_ID: int = int(os.environ.get("OWNER_ID"))

    REPO: Repo = Repo(".")

    SUDO: bool = False

    SUDO_TRIGGER: str = os.environ.get("SUDO_TRIGGER", "!")

    SUDO_CMD_LIST: list[str] = []

    SUDO_USERS: list[int] = []

    SUPERUSERS: list[int] = []

    UPSTREAM_REPO: str = os.environ.get(
        "UPSTREAM_REPO", "https://github.com/thedragonsinn/debrid-bot"
    )
