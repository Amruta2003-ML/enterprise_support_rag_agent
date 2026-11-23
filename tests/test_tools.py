import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.tools import (
    create_ticket,
    incident_search,
    list_all_services,
    list_user_tickets,
    service_status,
)


class TestTools(unittest.TestCase):
    def test_service_status_known_service(self):
        vpn_status = service_status("vpn")
        self.assertEqual(vpn_status["status"], "operational")
        self.assertIn("VPN", vpn_status["service"])

        gitlab_status = service_status("gitlab")
        self.assertEqual(gitlab_status["status"], "operational")

    def test_service_status_unknown_service(self):
        unknown = service_status("non_existent_corp_tool_xyz")
        self.assertEqual(unknown["status"], "unknown")
        self.assertIn("not in the monitored", unknown["message"])

    def test_list_all_services(self):
        services = list_all_services()
        self.assertGreater(len(services), 5)
        keys = [s["key"] for s in services]
        self.assertIn("vpn", keys)
        self.assertIn("okta", keys)

    def test_create_and_list_ticket(self):
        test_user = "test_employee_42"
        res = create_ticket(
            user_id=test_user,
            department="engineering",
            title="Unable to connect to internal DB",
            description="Timeout after 30 seconds",
            priority="high",
        )
        self.assertTrue(res["ticket_id"].startswith("INC-"))
        self.assertEqual(res["priority"], "high")

        # List user's tickets
        user_tickets = list_user_tickets(test_user)
        self.assertGreaterEqual(len(user_tickets), 1)
        ticket_ids = [t["ticket_id"] for t in user_tickets]
        self.assertIn(res["ticket_id"], ticket_ids)

    def test_incident_search(self):
        results = incident_search("GitLab VPN", department="engineering")
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("ticket_id", results[0])
            self.assertIn("resolution", results[0])


if __name__ == "__main__":
    unittest.main()
