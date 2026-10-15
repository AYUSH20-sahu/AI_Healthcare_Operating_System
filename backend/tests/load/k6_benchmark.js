import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 20 },  // Ramp-up to 20 virtual users
    { duration: '30s', target: 20 },  // Stay at 20 users
    { duration: '5s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    // 95% of non-AI requests must complete within 500ms
    http_req_duration: ['p(95)<500'],
    // Less than 1% failed requests
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000/api/v1';

export default function () {
  // 1. Healthcheck
  const healthRes = http.get(`${BASE_URL}/observability/health`);
  check(healthRes, {
    'healthcheck status is 200': (r) => r.status === 200,
  });

  // 2. Public Doctors Roster & Fee Schedule
  const doctorsRes = http.get(`${BASE_URL}/doctors/public-directory`);
  check(doctorsRes, {
    'doctors directory status is 200': (r) => r.status === 200,
    'doctors array returned': (r) => JSON.parse(r.body).length > 0,
  });

  sleep(1);
}
