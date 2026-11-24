from __future__ import annotations

import base64
import re


_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def encode_sse_event(event_name: str, data: str) -> str:
    """Format one newline-safe SSE event using the app's base64 data convention."""
    if not _EVENT_NAME.fullmatch(event_name):
        raise ValueError("Invalid SSE event name.")
    encoded = base64.b64encode(data.encode("utf-8")).decode("ascii")
    return f"event: {event_name}\ndata: {encoded}\n\n"
