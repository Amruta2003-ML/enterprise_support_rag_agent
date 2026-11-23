import unittest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.main import app


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "healthy")

    def test_web_ui(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Enterprise IT Support", response.text)

    def test_get_services(self):
        response = self.client.get("/services")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_get_incidents(self):
        response = self.client.get("/incidents?department=engineering")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_create_and_get_ticket(self):
        payload = {
            "user_id": "test_user_api",
            "department": "engineering",
            "title": "API Test Ticket",
            "description": "Testing ticket creation via REST endpoint",
            "priority": "medium",
        }
        create_res = self.client.post("/tickets", json=payload)
        self.assertEqual(create_res.status_code, 200)
        ticket = create_res.json()
        ticket_id = ticket["ticket_id"]
        self.assertTrue(ticket_id.startswith("INC-"))

        # Fetch detail
        detail_res = self.client.get(f"/tickets/{ticket_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["ticket_id"], ticket_id)

    def test_chat_endpoint(self):
        payload = {
            "user_id": "api_eval",
            "department": "engineering",
            "message": "VPN is connected but GitLab is unreachable.",
            "conversation_id": "test_api_conv",
        }
        response = self.client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertIsInstance(data["citations"], list)
        self.assertIsInstance(data["tools_used"], list)


if __name__ == "__main__":
    unittest.main()
