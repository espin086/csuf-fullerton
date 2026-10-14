"""`init` stores the FRED key without echoing it; the environment variable wins."""

from __future__ import annotations

import stat
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend
from typer.testing import CliRunner

from csuf_fullerton.cli.main import app
from csuf_fullerton.data import credentials

KEY = "abcdef0123456789abcdef0123456789"
runner = CliRunner()


class MemoryKeyring(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username), None)


@pytest.fixture
def memory_keyring(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> MemoryKeyring:
    kr = MemoryKeyring()
    previous = keyring.get_keyring()
    keyring.set_keyring(kr)
    monkeypatch.delenv(credentials.ENV_VAR, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    yield kr
    keyring.set_keyring(previous)


def test_init_stores_key(memory_keyring: MemoryKeyring) -> None:
    result = runner.invoke(app, ["init"], input=f"{KEY}\n")
    assert result.exit_code == 0
    assert KEY not in result.stdout
    assert memory_keyring.store[(credentials.SERVICE, credentials.USERNAME)] == KEY
    assert credentials.get_fred_key() == (KEY, "keyring")


def test_environment_wins(memory_keyring: MemoryKeyring, monkeypatch: pytest.MonkeyPatch) -> None:
    memory_keyring.set_password(credentials.SERVICE, credentials.USERNAME, KEY)
    monkeypatch.setenv(credentials.ENV_VAR, "f" * 32)
    assert credentials.get_fred_key() == ("f" * 32, "env")


def test_init_file_fallback_is_private(memory_keyring: MemoryKeyring, tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "--file"], input=f"{KEY}\n")
    assert result.exit_code == 0
    path = credentials.config_path()
    assert path.is_file() and stat.S_IMODE(path.stat().st_mode) == 0o600
    assert KEY not in result.stdout
    memory_keyring.store.clear()
    assert credentials.get_fred_key() == (KEY, "file")
    credentials.delete_fred_key()
    assert credentials.get_fred_key() == (None, "none")


def test_init_rejects_malformed_key(memory_keyring: MemoryKeyring) -> None:
    result = runner.invoke(app, ["init"], input="not-a-key\n")
    assert result.exit_code == 2
