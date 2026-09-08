/**
 * Askra AI — k6 Smoke Test
 * 
 * Verifies system sanity and endpoint functionality with minimal load.
 * 
 * Run command:
 *   k6 run benchmarks/k6/smoke_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const BASE_URL = __ENV.API_BASE_URL || 'http://127.0.0.1:8000';

// Custom metrics
const ttfbTrend = new Trend('chat_stream_ttfb_ms');
const streamSuccessRate = new Rate('stream_success_rate');

export const options = {
  vus: 1,
  duration: '15s',
  thresholds: {
    http_req_failed: ['rate<0.01'],         // Less than 1% failed requests
    http_req_duration: ['p(95)<3000'],      // 95% of requests under 3s
    'checks': ['rate>0.99'],                 // 99%+ checks passed
  },
};

export function setup() {
  console.log(`Setting up benchmark against ${BASE_URL}...`);

  // 1. Ensure benchmark user is registered
  const userPayload = JSON.stringify({
    email: 'k6_benchmark@askra.ai',
    password: 'BenchmarkPassword123!',
    full_name: 'k6 Runner',
    department: 'engineering',
    role: 'employee',
  });

  http.post(`${BASE_URL}/auth/register`, userPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  // 2. Authenticate
  const loginRes = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    email: 'k6_benchmark@askra.ai',
    password: 'BenchmarkPassword123!',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  const token = loginRes.json('access_token');
  if (!token) {
    throw new Error(`Authentication failed during setup: ${loginRes.body}`);
  }

  console.log('Setup complete: JWT token obtained successfully.');
  return { token };
}

export default function (data) {
  const authHeaders = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // 1. Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status 200': (r) => r.status === 200,
  });

  // 2. Chat REST endpoint (synchronous pipeline query)
  const chatPayload = JSON.stringify({
    query: 'What is Askra?',
    direct_rag: false,
  });
  const chatRes = http.post(`${BASE_URL}/api/chat`, chatPayload, { headers: authHeaders });
  check(chatRes, {
    'chat POST status 200': (r) => r.status === 200,
    'chat has answer': (r) => r.json('answer') !== undefined && r.json('answer').length > 0,
  });

  // 3. Chat SSE Streaming endpoint
  const streamUrl = `${BASE_URL}/api/chat/stream?query=Hello+from+k6&direct_rag=false`;
  const streamRes = http.get(streamUrl, {
    headers: {
      'Authorization': `Bearer ${data.token}`,
      'Accept': 'text/event-stream',
    },
    responseType: 'text',
  });

  const streamOk = check(streamRes, {
    'stream GET status 200': (r) => r.status === 200,
    'stream has data chunks': (r) => r.body && r.body.includes('data:'),
  });

  streamSuccessRate.add(streamOk);
  ttfbTrend.add(streamRes.timings.waiting);

  sleep(1);
}
