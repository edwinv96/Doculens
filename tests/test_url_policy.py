from __future__ import annotations

import unittest

from backend.url_policy import validate_public_http_url


class UrlPolicyTest(unittest.TestCase):
    def test_accepts_public_http_and_https_urls(self) -> None:
        resolver = lambda host, port: ["8.8.8.8"]

        self.assertEqual(
            validate_public_http_url("https://example.com/docs?q=rag", resolver),
            "https://example.com/docs?q=rag",
        )
        self.assertEqual(
            validate_public_http_url("http://example.com:8080/", resolver),
            "http://example.com:8080/",
        )

    def test_rejects_non_http_and_credentialed_urls(self) -> None:
        resolver = lambda host, port: ["8.8.8.8"]

        for url in (
            "file:///etc/passwd",
            "ftp://example.com/file",
            "https://user:password@example.com/private",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_public_http_url(url, resolver)

    def test_rejects_local_and_private_network_targets(self) -> None:
        cases = {
            "http://localhost/admin": ["127.0.0.1"],
            "http://internal.example/": ["10.0.0.10"],
            "http://metadata.example/": ["169.254.169.254"],
            "http://ipv6.example/": ["::1"],
        }

        for url, addresses in cases.items():
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_public_http_url(url, lambda host, port: addresses)

    def test_rejects_mixed_public_and_private_dns_answers(self) -> None:
        with self.assertRaises(ValueError):
            validate_public_http_url(
                "https://example.com/",
                lambda host, port: ["8.8.8.8", "127.0.0.1"],
            )


if __name__ == "__main__":
    unittest.main()
