"""Reads config.toml, so no script has to hardcode one person's folders.

Understands only the subset the file uses -- comments, `key = value`, and arrays of strings --
rather than needing a TOML library for thirty lines.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.toml")


def _values():
    out = {}
    try:
        with open(CONFIG, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if "#" in value and value.count('"') % 2 == 0:
                    value = value.split("#")[0]
                out[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return out


def path(key, default=None):
    """A configured path, or a default that sits inside the repository."""
    value = _values().get(key)
    if value:
        return value
    if default is None:
        return None
    return os.path.join(ROOT, default)


def require(key):
    """A path that only makes sense on a machine that has the thing it names."""
    value = _values().get(key)
    if not value:
        raise SystemExit(
            "`%s` is not set in config.toml.\n"
            "This script needs it; see config.example.toml for what it means." % key
        )
    return value
