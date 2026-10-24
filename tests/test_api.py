"""
AFTERSHOCK AI — REST API Endpoint Tests
Module: tests/test_api.py
"""

import json
import socket
import unittest
from app import app, create_local_server


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for Flask REST API routes, payloads, status codes, and input validation."""

    def setUp(self):
        self.client = app.test_client()

    def test_homepage_redirects_to_simulation(self):
        """GET / redirects to the Simulation page."""
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/simulation")

    def test_local_server_falls_back_when_preferred_port_is_occupied(self):
        occupied_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            occupied_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        occupied_socket.bind(("127.0.0.1", 0))
        occupied_socket.listen(1)
        occupied_port = occupied_socket.getsockname()[1]
        server = None

        try:
            server = create_local_server(preferred_port=occupied_port)
            self.assertNotEqual(server.server_port, occupied_port)
        finally:
            if server:
                server.server_close()
            occupied_socket.close()

    def test_all_pages_serve_html(self):
        """Verify all four remaining feature pages return HTTP 200."""
        pages = ["/simulation", "/infrastructure", "/optimizer", "/risks"]
        for p in pages:
            res = self.client.get(p)
            self.assertEqual(res.status_code, 200, f"Page route {p} failed to load.")
            self.assertIn(b"AFTERSHOCK", res.data)

    def test_status_endpoint(self):
        """GET /api/status returns successful online status, target city, and demonstration mode."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["project"], "AFTERSHOCK AI")
        self.assertIn("Mangaluru", data["target_city"])
        self.assertTrue(data["offline_ready"])

    def test_cities_endpoint(self):
        """GET /api/cities returns configured cities list including active Mangaluru."""
        response = self.client.get("/api/cities")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["active_city"], "mangaluru")
        self.assertIsInstance(data["cities"], list)
        city_ids = [c["id"] for c in data["cities"]]
        self.assertIn("mangaluru", city_ids)

    def test_infrastructure_endpoint(self):
        """GET /api/infrastructure returns JSON list of assets and dependencies."""
        response = self.client.get("/api/infrastructure")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total_assets"], 0)
        self.assertIsInstance(data["assets"], list)
        self.assertIsInstance(data["dependencies"], list)

    def test_scenarios_endpoint(self):
        """GET /api/scenarios returns expected disaster scenarios."""
        response = self.client.get("/api/scenarios")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        scenario_ids = [s["id"] for s in data["scenarios"]]
        self.assertIn("flood", scenario_ids)
        self.assertIn("power_outage", scenario_ids)
        self.assertIn("communication_failure", scenario_ids)

    def test_interventions_endpoint(self):
        """GET /api/interventions returns available interventions and currency information."""
        response = self.client.get("/api/interventions")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total_interventions"], 0)
        for item in data["interventions"]:
            self.assertIn("id", item)
            self.assertIn("cost", item)
            self.assertIn("asset_id", item)

    def test_risks_endpoint(self):
        """GET /api/risks returns demonstration classifications and synthetic data warning."""
        response = self.client.get("/api/risks")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("assets", data)
        self.assertIn("warning", data)

    def test_simulate_valid_request(self):
        """POST /api/simulate executes successfully with valid payload."""
        payload = {
            "scenario": "flood",
            "protected_assets": ["INT-SUB"],
        }
        response = self.client.post(
            "/api/simulate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("simulation", data)
        self.assertEqual(data["simulation"]["scenario"], "flood")

    def test_simulate_invalid_scenario_rejected(self):
        """POST /api/simulate returns HTTP 400 for unknown scenario."""
        payload = {"scenario": "volcano_eruption"}
        response = self.client.post(
            "/api/simulate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "error")

    def test_simulate_invalid_asset_rejected(self):
        """POST /api/simulate returns HTTP 400 for nonexistent protected asset ID."""
        payload = {
            "scenario": "flood",
            "protected_assets": ["NONEXISTENT_ASSET_123"],
        }
        response = self.client.post(
            "/api/simulate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_optimize_valid_request(self):
        """POST /api/optimize returns recommended plan within budget."""
        payload = {
            "scenario": "flood",
            "budget": 50000,
        }
        response = self.client.post(
            "/api/optimize",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        plan = data["plan"]
        self.assertLessEqual(plan["total_cost"], 50000)
        self.assertIn("selected_interventions", plan)

    def test_optimize_negative_budget_rejected(self):
        """POST /api/optimize returns HTTP 400 for negative budget."""
        payload = {
            "scenario": "flood",
            "budget": -5000,
        }
        response = self.client.post(
            "/api/optimize",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "error")

    def test_optimize_boolean_budget_rejected(self):
        """POST /api/optimize returns HTTP 400 for boolean budget."""
        payload = {
            "scenario": "flood",
            "budget": True,
        }
        response = self.client.post(
            "/api/optimize",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_route_returns_404(self):
        """GET /api/nonexistent returns HTTP 404."""
        response = self.client.get("/api/nonexistent")
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "error")


if __name__ == "__main__":
    unittest.main()

