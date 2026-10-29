import time
from collections import deque
import numpy as np


class PrometheusMetricsExporter:
    """
    In-memory Prometheus-compatible metrics collector.
    Tracks API latencies (p50, p95, p99), queue depth, active containers, and error rates.
    """
    def __init__(self, history_size: int = 2000):
        self.latency_records: deque = deque(maxlen=history_size)
        self.request_count = 0
        self.error_count = 0
        self.status_codes: dict[int, int] = {}

    def record_request(self, duration_ms: float, status_code: int):
        self.request_count += 1
        self.latency_records.append(duration_ms)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if status_code >= 500:
            self.error_count += 1

    def calculate_percentiles(self) -> tuple[float, float, float]:
        if not self.latency_records:
            return 0.0, 0.0, 0.0
        arr = np.array(self.latency_records)
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        return round(p50, 2), round(p95, 2), round(p99, 2)

    def generate_prometheus_output(
        self,
        queue_depth: int = 0,
        running_containers: int = 0,
        node_ram_percent: float = 0.0,
        node_cpu_percent: float = 0.0,
    ) -> str:
        p50, p95, p99 = self.calculate_percentiles()
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0.0

        lines = [
            "# HELP bothost_api_requests_total Total number of HTTP requests processed",
            "# TYPE bothost_api_requests_total counter",
            f"bothost_api_requests_total {self.request_count}",
            "",
            "# HELP bothost_api_errors_total Total number of 5xx HTTP responses",
            "# TYPE bothost_api_errors_total counter",
            f"bothost_api_errors_total {self.error_count}",
            "",
            "# HELP bothost_api_error_rate_percent Percentage of requests resulting in error",
            "# TYPE bothost_api_error_rate_percent gauge",
            f"bothost_api_error_rate_percent {round(error_rate, 2)}",
            "",
            "# HELP bothost_api_latency_ms HTTP request latency percentiles in milliseconds",
            "# TYPE bothost_api_latency_ms gauge",
            f'bothost_api_latency_ms{{quantile="0.50"}} {p50}',
            f'bothost_api_latency_ms{{quantile="0.95"}} {p95}',
            f'bothost_api_latency_ms{{quantile="0.99"}} {p99}',
            "",
            "# HELP bothost_queue_depth_jobs Number of pending tasks in Redis job queue",
            "# TYPE bothost_queue_depth_jobs gauge",
            f"bothost_queue_depth_jobs {queue_depth}",
            "",
            "# HELP bothost_running_containers Active running Telegram bot containers",
            "# TYPE bothost_running_containers gauge",
            f"bothost_running_containers {running_containers}",
            "",
            "# HELP bothost_node_ram_usage_percent Worker node RAM utilization percentage",
            "# TYPE bothost_node_ram_usage_percent gauge",
            f"bothost_node_ram_usage_percent {node_ram_percent}",
            "",
            "# HELP bothost_node_cpu_usage_percent Worker node CPU utilization percentage",
            "# TYPE bothost_node_cpu_usage_percent gauge",
            f"bothost_node_cpu_usage_percent {node_cpu_percent}",
        ]
        return "\n".join(lines) + "\n"


metrics_exporter = PrometheusMetricsExporter()
