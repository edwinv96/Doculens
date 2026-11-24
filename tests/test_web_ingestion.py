from __future__ import annotations

import unittest

from backend.web_ingestion import fetch_public_page


class FakeResponse:
    def __init__(self, status_code, headers=None, body=b"", encoding="utf-8"):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.encoding = encoding
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        self.closed = True


class WebIngestionTest(unittest.TestCase):
    def test_validates_each_redirect_before_following(self) -> None:
        responses = [FakeResponse(302, {"Location": "http://127.0.0.1/admin"})]
        calls = []

        def request_get(url, **kwargs):
            calls.append((url, kwargs))
            return responses.pop(0)

        with self.assertRaises(ValueError):
            fetch_public_page(
                "https://public.example/",
                request_get=request_get,
                resolver=lambda host, port: ["8.8.8.8"] if host == "public.example" else ["127.0.0.1"],
            )

        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][1]["allow_redirects"])

    def test_follows_public_redirect_and_returns_final_url(self) -> None:
        responses = [
            FakeResponse(302, {"Location": "/article"}),
            FakeResponse(200, {"Content-Type": "text/html; charset=utf-8"}, b"<p>RAG</p>"),
        ]

        final_url, content_type, body = fetch_public_page(
            "https://public.example/",
            request_get=lambda url, **kwargs: responses.pop(0),
            resolver=lambda host, port: ["8.8.8.8"],
        )

        self.assertEqual(final_url, "https://public.example/article")
        self.assertEqual(content_type, "text/html")
        self.assertEqual(body, "<p>RAG</p>")

    def test_rejects_unsupported_content_type_and_oversized_body(self) -> None:
        resolver = lambda host, port: ["8.8.8.8"]
        with self.assertRaisesRegex(ValueError, "Only HTML"):
            fetch_public_page(
                "https://public.example/file.pdf",
                request_get=lambda url, **kwargs: FakeResponse(200, {"Content-Type": "application/pdf"}),
                resolver=resolver,
            )
        with self.assertRaisesRegex(ValueError, "response-size limit"):
            fetch_public_page(
                "https://public.example/large",
                request_get=lambda url, **kwargs: FakeResponse(200, {"Content-Type": "text/plain"}, b"012345"),
                resolver=resolver,
                max_bytes=5,
            )


if __name__ == "__main__":
    unittest.main()
