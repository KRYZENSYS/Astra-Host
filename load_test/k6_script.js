import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metric trends for SLO validation
export const errorRate = new Rate('errors');
export const dashboardLoadTrend = new Trend('dashboard_load_ms');

export const options = {
  scenarios: {
    // Scenario 1: 2,000 concurrent dashboard viewers
    dashboard_traffic: {
      executor: 'ramping-vus',
      startVUs: 50,
      stages: [
        { duration: '30s', target: 500 },
        { duration: '1m', target: 2000 },
        { duration: '2m', target: 2000 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
    // Scenario 2: 200 bot actions per minute
    bot_operations: {
      executor: 'constant-arrival-rate',
      rate: 200,
      timeUnit: '1m',
      duration: '4m',
      preAllocatedVUs: 50,
      maxVUs: 150,
    },
  },
  thresholds: {
    // SLO 1: API p95 response time must be under 300 ms
    http_req_duration: ['p(95)<300', 'p(99)<600'],
    // SLO 2: Overall error rate must be under 1%
    'errors': ['rate<0.01'],
    // SLO 3: Dashboard data load under 2,000 ms
    'dashboard_load_ms': ['p(95)<2000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:3000';

export default function () {
  const start = Date.now();

  // 1. Fetch dashboard bot list (cursor-paginated)
  const res = http.get(`${BASE_URL}/api/v1/bots?limit=20`, {
    headers: {
      'Accept': 'application/json',
      'X-Request-ID': `k6-${__VU}-${__ITER}`,
    },
    timeout: '5s',
  });

  const loadDuration = Date.now() - start;
  dashboardLoadTrend.add(loadDuration);

  const success = check(res, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'latency is under 300ms': (r) => r.timings.duration < 300,
  });

  errorRate.add(!success && res.status >= 500);

  // Think time between page interactions
  sleep(1);
}
