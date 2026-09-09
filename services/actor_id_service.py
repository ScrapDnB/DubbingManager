"""Stable actor identifier generation and legacy-ID migration helpers."""

import re
from typing import Any, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5


_LEGACY_TIMESTAMP_ACTOR_ID = re.compile(
    r"^(?:global_)?\d{10}\.\d+$"
)


def new_actor_id() -> str:
    """Return a new opaque actor UUID."""
    return str(uuid4())


def migrated_actor_id(actor_id: Any) -> Optional[str]:
    """Return a stable UUID for a legacy timestamp ID, otherwise ``None``."""
    value = str(actor_id)
    if not _LEGACY_TIMESTAMP_ACTOR_ID.fullmatch(value):
        return None
    return str(uuid5(
        NAMESPACE_URL,
        f"https://dubbingmanager.app/legacy-actor/{value}",
    ))


def normalize_actor_id(actor_id: Any) -> str:
    """Return an actor ID in its current canonical representation."""
    value = str(actor_id)
    return migrated_actor_id(value) or value
