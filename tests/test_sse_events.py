from __future__ import annotations

import base64
import unittest

from backend.sse_events import encode_sse_event


class SseEventTest(unittest.TestCase):
    def test_event_data_is_base64_encoded_and_newline_safe(self) -> None:
        event = encode_sse_event("text", "line one\nline two")
        lines = event.splitlines()

        self.assertEqual(lines[0], "event: text")
        self.assertEqual(base64.b64decode(lines[1][6:]).decode("utf-8"), "line one\nline two")
        self.assertEqual(lines[2], "")

    def test_invalid_event_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encode_sse_event("bad event", "payload")


if __name__ == "__main__":
    unittest.main()
