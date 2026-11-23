import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.rag import chunk_text, read_file, search


class TestRAG(unittest.TestCase):
    def test_chunk_text(self):
        sample_text = "This is a sentence. " * 80
        chunks = chunk_text(sample_text, size=200, overlap=50)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 250 for c in chunks))

    def test_chunk_empty_text(self):
        chunks = chunk_text("")
        self.assertEqual(chunks, [])

    def test_read_file(self):
        test_file = BASE_DIR / "data" / "docs" / "vpn.md"
        if test_file.exists():
            content = read_file(test_file)
            self.assertIn("VPN", content)

    def test_search_rbsc(self):
        results = search(query="VPN connection", department="engineering", k=3)
        self.assertIsInstance(results, list)
        for r in results:
            self.assertIn("source", r)
            self.assertIn("text", r)


if __name__ == "__main__":
    unittest.main()
