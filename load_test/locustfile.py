import json
import time
import random
from locust import HttpUser, task, between, events


class DashboardViewerUser(HttpUser):
    """
    Simulates concurrent users actively browsing the BotHost dashboard,
    fetching bot lists, reading metrics, and polling background job progress.
    Target: 2,000 concurrent users.
    """
    weight = 10
    wait_time = between(1, 3)

    def on_start(self):
        # Register or authenticate a simulated test user
        self.user_email = f"loadtest_{random.randint(1000, 999999)}@bothost.uz"
        self.token = None
        resp = self.client.post("/api/v1/auth/register", json={
            "email": self.user_email,
            "password": "LoadTestSecurePassword2026!",
        })
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(6)
    def view_dashboard_bots(self):
        """Fetch bot list with cursor pagination."""
        self.client.get("/api/v1/bots?limit=20")

    @task(3)
    def view_bot_metrics(self):
        """Fetch telemetry metrics."""
        self.client.get("/api/v1/bots/bot_news_uz/metrics")

    @task(1)
    def view_plans(self):
        """Inspect plan limits."""
        self.client.get("/api/v1/admin/stats")


class BotOperatorUser(HttpUser):
    """
    Simulates high-frequency bot operators triggering start/stop/restart operations.
    Target: 200 operations per minute.
    """
    weight = 2
    wait_time = between(3, 8)

    def on_start(self):
        self.user_email = f"operator_{random.randint(1000, 999999)}@bothost.uz"
        resp = self.client.post("/api/v1/auth/register", json={
            "email": self.user_email,
            "password": "OperatorSecurePassword2026!",
        })
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(1)
    def trigger_bot_action(self):
        action = random.choice(["start", "restart", "stop"])
        self.client.post("/api/v1/bots/bot_news_uz/action", json={"action": action})


class LogStreamerUser(HttpUser):
    """
    Simulates users maintaining long-lived SSE connections for live terminal logs.
    Target: 100 simultaneous streams.
    """
    weight = 1
    wait_time = between(10, 20)

    def on_start(self):
        self.user_email = f"streamer_{random.randint(1000, 999999)}@bothost.uz"
        resp = self.client.post("/api/v1/auth/register", json={
            "email": self.user_email,
            "password": "StreamerPassword2026!",
        })
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(1)
    def listen_to_sse_logs(self):
        with self.client.get(
            "/api/v1/bots/bot_news_uz/logs/sse",
            stream=True,
            catch_response=True,
            timeout=15,
        ) as response:
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"SSE failed with status {response.status_code}")
