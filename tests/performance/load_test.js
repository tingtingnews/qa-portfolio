import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 0  },
  ],
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    errors:            ['rate<0.05'],
  },
};

export default function () {
  const responses = http.batch([
    ['GET', 'https://reqres.in/api/users?page=1'],
    ['GET', 'https://reqres.in/api/users/2'],
  ]);
  responses.forEach((res) => {
    errorRate.add(!check(res, { 'status 200': (r) => r.status === 200 }));
  });
  sleep(1);
}
