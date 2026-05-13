import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    http_req_failed:   ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const res = http.get('https://reqres.in/api/users?page=1');
  check(res, {
    'status is 200':     (r) => r.status === 200,
    'has data':          (r) => JSON.parse(r.body).data.length > 0,
    'under 1s':          (r) => r.timings.duration < 1000,
  });
  sleep(1);
}
