/**
 * Askra AI — k6 Concurrency Load Test
 * 
 * Simulates multiple concurrent users chatting with Askra.
 * Measures latency under load (P50, P90, P95, P99), throughput (RPS), and failure rate.
 * 
 * Usage:
 *   k6 run benchmarks/k6/load_test.js
 * 
 * Custom options via env:
 *   API_BASE_URL=http://127.0.0.1:8000 k6 run benchmarks/k6/load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const BASE_URL = __ENV.API_BASE_URL || 'http://127.0.0.1:8000';

// Custom Metrics
const chatLatencyTrend = new Trend('chat_endpoint_duration_ms');
const streamTtfbTrend = new Trend('stream_ttfb_waiting_ms');
const streamDurationTrend = new Trend('stream_total_duration_ms');
const errorRate = new Rate('custom_error_rate');
const successfulQueries = new Counter('successful_queries_count');

// Test stages: ramp up -> steady load -> ramp down
export const options = {
  stages: [
    { duration: '10s', target: 5 },   // Ramp up to 5 concurrent users
    { duration: '30s', target: 15 },  // Ramp up to 15 concurrent users
    { duration: '20s', target: 15 },  // Stay at 15 concurrent users
    { duration: '10s', target: 0 },   // Ramp down to 0
  ],
  thresholds: {
    'http_req_failed': ['rate<0.02'],          // Less than 2% errors
    'http_req_duration': ['p(95)<3500'],       // 95% of requests complete under 3.5s
    'stream_ttfb_waiting_ms': ['p(95)<2000'],  // TTFT / TTFB under 2s
    'custom_error_rate': ['rate<0.02'],
  },
};

// Real-world sample queries for simulated users
const SAMPLE_QUERIES = [
  'What is Askra and how does it work?',
  'Hello! Can you help me summarize company policies?',
  'What are the supported user roles in this platform?',
  'How is hybrid retrieval implemented with FAISS and BM25?',
  'Tell me about the 7-layer pipeline architecture.',
  'What security safeguards are in place for user data?',
];

export function setup() {
  console.log(`[k6 Setup] Authenticating benchmark user at ${BASE_URL}...`);

  const loginPayload = JSON.stringify({
    email: 'k6_loadtester@askra.ai',
    password: 'LoadTester123!',
  });

  let loginRes = http.post(`${BASE_URL}/auth/login`, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status !== 200) {
    http.post(`${BASE_URL}/auth/register`, JSON.stringify({
      email: 'k6_loadtester@askra.ai',
      password: 'LoadTester123!',
      full_name: 'k6 Load Tester',
      department: 'engineering',
      role: 'employee',
    }), { headers: { 'Content-Type': 'application/json' } });

    loginRes = http.post(`${BASE_URL}/auth/login`, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const token = loginRes.json('access_token');
  if (!token) {
    throw new Error(`k6 setup failed to authenticate: ${loginRes.body}`);
  }


  console.log('[k6 Setup] Setup completed successfully.');
  return { token };
}

export default function (data) {
  const query = SAMPLE_QUERIES[Math.floor(Math.random() * SAMPLE_QUERIES.length)];
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // Alternates between SSE stream and REST chat
  const useStream = Math.random() > 0.3; // 70% stream, 30% REST

  if (useStream) {
    const encodedQuery = encodeURIComponent(query);
    const streamUrl = `${BASE_URL}/api/chat/stream?query=${encodedQuery}&direct_rag=false`;
    
    const streamRes = http.get(streamUrl, {
      headers: {
        'Authorization': `Bearer ${data.token}`,
        'Accept': 'text/event-stream',
      },
      responseType: 'text',
      timeout: '30s',
    });

    const isSuccess = check(streamRes, {
      'stream status 200': (r) => r.status === 200,
      'stream contains data': (r) => r.body && r.body.includes('data:'),
    });

    if (isSuccess) {
      successfulQueries.add(1);
      errorRate.add(0);
      streamTtfbTrend.add(streamRes.timings.waiting);
      streamDurationTrend.add(streamRes.timings.duration);
    } else {
      errorRate.add(1);
    }
  } else {
    const chatPayload = JSON.stringify({
      query: query,
      direct_rag: false,
    });

    const chatRes = http.post(`${BASE_URL}/api/chat`, chatPayload, {
      headers: headers,
      timeout: '30s',
    });

    const isSuccess = check(chatRes, {
      'chat status 200': (r) => r.status === 200,
      'chat answer returned': (r) => r.json('answer') !== undefined,
    });

    if (isSuccess) {
      successfulQueries.add(1);
      errorRate.add(0);
      chatLatencyTrend.add(chatRes.timings.duration);
    } else {
      errorRate.add(1);
    }
  }

  // Realistic user pacing between queries
  sleep(1.5 + Math.random() * 2);
}
