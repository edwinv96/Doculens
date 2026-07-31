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

    def test_env_path_is_assigned_before_it_is_loaded(self) -> None:
        assignment_lines = [
            node.lineno
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Name)
            and node.id == "env_path"
            and isinstance(node.ctx, ast.Store)
        ]
        load_lines = [
            node.lineno
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Name)
            and node.id == "env_path"
            and isinstance(node.ctx, ast.Load)
        ]

        self.assertTrue(assignment_lines)
        self.assertTrue(load_lines)
        self.assertLess(min(assignment_lines), min(load_lines))

    def test_frontend_only_advertises_supported_pdf_uploads(self) -> None:
        self.assertIn('type=["pdf"]', self.source)
        self.assertIn("timeout=120", self.source)

    def test_css_path_is_resolved_from_the_frontend_module(self) -> None:
        self.assertIn('load_css(FRONTEND_DIR / "style.css")', self.source)


if __name__ == "__main__":
    unittest.main()
