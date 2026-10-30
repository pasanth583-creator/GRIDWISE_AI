"""
GRIDWISE AI - Application Monitoring & Telemetry Service
Tracks request throughput, latency, endpoint metrics, and system statistics.
"""

import time
import threading
from typing import Dict, Any, List
from collections import deque

class ApplicationMonitoring:
    """In-memory telemetry collector for production monitoring."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ApplicationMonitoring, cls).__new__(cls)
                cls._instance._init_metrics()
            return cls._instance
            
    def _init_metrics(self):
        self.start_time = time.time()
        self.requests_total = 0
        self.requests_2xx = 0
        self.requests_4xx = 0
        self.requests_5xx = 0
        self.optimization_runs_total = 0
        self.latencies_ms = deque(maxlen=1000)
        self.endpoints_count: Dict[str, int] = {}
        self._metric_lock = threading.Lock()
        
    def record_request(self, endpoint: str, status_code: int, duration_ms: float):
        """Records an HTTP request lifecycle."""
        with self._metric_lock:
            self.requests_total += 1
            if 200 <= status_code < 300:
                self.requests_2xx += 1
            elif 400 <= status_code < 500:
                self.requests_4xx += 1
            elif status_code >= 500:
                self.requests_5xx += 1
                
            self.latencies_ms.append(duration_ms)
            self.endpoints_count[endpoint] = self.endpoints_count.get(endpoint, 0) + 1

    def record_optimization_run(self):
        """Increment optimization run counter."""
        with self._metric_lock:
            self.optimization_runs_total += 1

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns structured application metrics."""
        with self._metric_lock:
            uptime_seconds = int(time.time() - self.start_time)
            avg_latency = round(sum(self.latencies_ms) / max(len(self.latencies_ms), 1), 2) if self.latencies_ms else 0.0
            p95_latency = 0.0
            if self.latencies_ms:
                sorted_lat = sorted(self.latencies_ms)
                idx_95 = int(len(sorted_lat) * 0.95)
                p95_latency = round(sorted_lat[min(idx_95, len(sorted_lat) - 1)], 2)
                
            top_endpoints = sorted(self.endpoints_count.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
                "requests_total": self.requests_total,
                "status_breakdown": {
                    "2xx_success": self.requests_2xx,
                    "4xx_client_error": self.requests_4xx,
                    "5xx_server_error": self.requests_5xx
                },
                "latency_metrics": {
                    "average_ms": avg_latency,
                    "p95_ms": p95_latency,
                    "sample_size": len(self.latencies_ms)
                },
                "optimization_runs_total": self.optimization_runs_total,
                "top_endpoints": dict(top_endpoints)
            }

monitoring = ApplicationMonitoring()

