from __future__ import annotations

import ast
import unittest
from pathlib import Path


class FrontendSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = Path(__file__).resolve().parents[1] / "frontend" / "app.py"
        cls.source = cls.source_path.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_source_is_valid_python(self) -> None:
        self.assertIsInstance(self.tree, ast.Module)

    def test_frontend_does_not_load_or_transmit_provider_credentials(self) -> None:
        self.assertNotIn("load_dotenv", self.source)
        self.assertNotIn("api_keys", self.source)
        self.assertNotIn('text_input("API Key"', self.source)
        self.assertIn('st.caption("Provider credentials stay in backend/.env', self.source)

    def test_product_brand_and_demo_document_use_doculens(self) -> None:
        self.assertIn('page_title="DocuLens"', self.source)
        self.assertIn('st.title("DocuLens")', self.source)
        self.assertIn('"DocuLens_Demo.pdf"', self.source)

    def test_frontend_only_advertises_supported_pdf_uploads(self) -> None:
        self.assertIn('type=["pdf"]', self.source)
        self.assertIn("timeout=120", self.source)

    def test_css_path_is_resolved_from_the_frontend_module(self) -> None:
        self.assertIn('load_css(FRONTEND_DIR / "style.css")', self.source)


if __name__ == "__main__":
    unittest.main()
