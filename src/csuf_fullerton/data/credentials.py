"""FRED API key storage.

Lookup order: ``FRED_API_KEY`` environment variable, then the OS keychain through ``keyring``
(service ``csuf-fullerton``, user ``fred_api_key``), then a ``0600`` TOML file under the user
config directory. The key is never logged or written to outputs.
"""

from __future__ import annotations

import contextlib
import os
import re
import tomllib
from pathlib import Path

SERVICE = "csuf-fullerton"
USERNAME = "fred_api_key"
ENV_VAR = "FRED_API_KEY"
KEY_PATTERN = re.compile(r"^[a-z0-9]{32}$")


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "csuf-fullerton" / "credentials.toml"


def valid_key(key: str) -> bool:
    """FRED keys are 32 lower-case alphanumeric characters."""
    return bool(KEY_PATTERN.match(key))


def _keyring_usable() -> bool:
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return False
    return not isinstance(keyring.get_keyring(), fail.Keyring)


def get_fred_key() -> tuple[str | None, str]:
    """Return (key, where it came from). ``where`` is ``env``, ``keyring``, ``file`` or ``none``."""
    env = os.environ.get(ENV_VAR, "").strip()
    if env:
        return env, "env"
    if _keyring_usable():
        import keyring

        try:
            stored = keyring.get_password(SERVICE, USERNAME)
        except Exception:
            stored = None
        if stored:
            return stored, "keyring"
    path = config_path()
    if path.is_file():
        data = tomllib.loads(path.read_text())
        key = str(data.get(USERNAME, "")).strip()
        if key:
            return key, "file"
    return None, "none"


def store_fred_key(key: str, prefer_file: bool = False) -> str:
    """Store the key; returns ``keyring`` or the file path used."""
    if not prefer_file and _keyring_usable():
        import keyring

        keyring.set_password(SERVICE, USERNAME, key)
        return "keyring"
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(f'{USERNAME} = "{key}"\n')
    os.chmod(path, 0o600)
    return str(path)


def delete_fred_key() -> None:
    if _keyring_usable():
        import keyring
        from keyring.errors import PasswordDeleteError

        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(SERVICE, USERNAME)
    path = config_path()
    if path.is_file():
        path.unlink()
