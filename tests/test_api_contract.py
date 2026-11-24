from __future__ import annotations

import ast
import unittest
from pathlib import Path


class ApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).resolve().parents[1] / "backend" / "main.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_chat_request_does_not_accept_provider_credentials(self) -> None:
        model = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AgentChatRequest"
        )
        fields = {
            target.id
            for node in model.body
            if isinstance(node, ast.AnnAssign)
            for target in [node.target]
            if isinstance(target, ast.Name)
        }
        self.assertEqual(fields, {"message", "thread_id"})

    def test_health_document_and_evaluation_routes_are_declared(self) -> None:
        for path in ('"/health"', '"/documents"', '"/evaluation/run"'):
            with self.subTest(path=path):
                self.assertIn(path, self.source)

    def test_missing_thread_id_gets_a_new_session(self) -> None:
        self.assertIn('default_factory=lambda: str(uuid.uuid4())', self.source)


if __name__ == "__main__":
    unittest.main()
