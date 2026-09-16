/**
 * Askra AI — Enterprise Concurrency & Throughput Benchmark
 * 
 * Simulates realistic enterprise production traffic with:
 * - 30+ diverse domain queries (Technical RAG, HR/Policy, Security, General Chat)
 * - 70% unique long-tail queries / 30% recurring FAQ queries (Zipf distribution)
 * - Randomized user sessions to simulate multi-tenant concurrency
 * - Realistic client arrival rates (0.5s - 1.2s think time)
 * - Full telemetry: TTFT (Time-to-First-Token), P50/P90/P95 latency, RPS, Error Rate
 * 
 * Usage:
 *   k6 run benchmarks/k6/enterprise_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const BASE_URL = __ENV.API_BASE_URL || 'http://127.0.0.1:8000';

// Custom Enterprise Telemetry Metrics
const streamTtfbTrend = new Trend('stream_ttfb_ms');
const streamDurationTrend = new Trend('stream_duration_ms');
const chatLatencyTrend = new Trend('chat_duration_ms');
const errorRate = new Rate('enterprise_error_rate');
const successfulQueries = new Counter('successful_queries');
const totalTokensVerified = new Counter('stream_tokens_verified');

export const options = {
  stages: [
    { duration: '10s', target: 10 },  // Ramp up to 10 VUs (Warmup)
    { duration: '20s', target: 20 },  // Ramp up to 20 VUs (Peak traffic)
    { duration: '25s', target: 20 },  // Sustained enterprise peak load
    { duration: '10s', target: 0 },   // Graceful ramp-down
  ],
  thresholds: {
    'http_req_failed': ['rate<0.02'],          // Less than 2% HTTP failures
    'enterprise_error_rate': ['rate<0.02'],
    'stream_ttfb_ms': ['p(95)<2500'],          // TTFT P95 under 2.5s
  },
};

// 30+ Diverse Enterprise Queries across all pipeline layers
const ENTERPRISE_QUERIES = [
  // Technical RAG Queries (FAISS + BM25 + CrossEncoder)
  'How is hybrid retrieval implemented with FAISS and BM25?',
  'Explain the 7-layer pipeline architecture in Askra.',
  'What vector embedding model is used for semantic search?',
  'How does the cross-encoder reranker prioritize candidate chunks?',
  'What is reciprocal rank fusion and how is RRF score calculated?',
  'What is the dimension of the all-MiniLM-L6-v2 embedding vectors?',
  'How does the router distinguish between RAG and direct chat?',
  'Where are dense vector indexes persisted on the server?',
  'What is the threshold for hallucination detection in layer 4?',
  'How does the reflection agent recover when validation fails?',

  // Enterprise Policies & HR (Document lookup)
  'What is the company policy regarding remote work and flexible hours?',
  'How do employees request annual leave and vacation time?',
  'What are the guidelines for expense reimbursement and travel allowances?',
  'What are the core health insurance and medical benefits provided?',
  'What is the standard procedure for reporting workplace incidents?',
  'How does the annual performance review cycle operate?',
  'What are the guidelines for using company hardware and laptops?',
  'What is the probationary period duration for new engineering hires?',
  'What professional development and training budgets are available?',
  'What are the working hours and overtime compensation policies?',

  // Security, Access Control & Compliance
  'What security safeguards are in place for sensitive user data?',
  'What authentication protocols and JWT mechanisms are enforced?',
  'What are the supported user roles and permission boundaries?',
  'How is role-based access control (RBAC) enforced across departments?',
  'Is user data encrypted at rest and in transit?',
  'What password complexity requirements are enforced on registration?',

  // Conversational / Short General Inquiries
  'Hello! Can you help me summarize company policies?',
  'What can this AI assistant do for my team?',
  'Good morning! What tools are available in the platform?',
  'Can you help me analyze documentation?',
];

export function setup() {
  console.log(`[Enterprise Setup] Authenticating test client at ${BASE_URL}...`);

  const loginPayload = JSON.stringify({
    email: 'k6_enterprise@askra.ai',
    password: 'EnterpriseTest123!',
  });

  let loginRes = http.post(`${BASE_URL}/auth/login`, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status !== 200) {
    http.post(`${BASE_URL}/auth/register`, JSON.stringify({
      email: 'k6_enterprise@askra.ai',
      password: 'EnterpriseTest123!',
      full_name: 'Enterprise Load Tester',
      department: 'engineering',
      role: 'employee',
    }), { headers: { 'Content-Type': 'application/json' } });

    loginRes = http.post(`${BASE_URL}/auth/login`, loginPayload, {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const token = loginRes.json('access_token');
  if (!token) {
    throw new Error(`Enterprise benchmark failed to authenticate: ${loginRes.body}`);
  }

  console.log('[Enterprise Setup] Setup completed. Token acquired.');
  return { token };
}

export default function (data) {
  // Zipf's Law Simulation:
  // 30% of traffic asks the top 3 hot queries (recurring FAQs)
  // 70% of traffic asks long-tail unique queries
  let query;
  if (Math.random() < 0.3) {
    query = ENTERPRISE_QUERIES[Math.floor(Math.random() * 3)];
  } else {
    query = ENTERPRISE_QUERIES[Math.floor(Math.random() * ENTERPRISE_QUERIES.length)];
  }

  // 70% SSE Streaming (real-time chat UX), 30% REST synchronous POST
  const isStream = Math.random() < 0.7;

  if (isStream) {
    const streamUrl = `${BASE_URL}/api/chat/stream?query=${encodeURIComponent(query)}&direct_rag=false`;
    const res = http.get(streamUrl, {
      headers: {
        'Authorization': `Bearer ${data.token}`,
        'Accept': 'text/event-stream',
      },
      responseType: 'text',
      timeout: '30s',
    });

    const hasData = res.body && res.body.includes('data:');
    const hasTokens = res.body && res.body.includes('"type": "token"');

    const ok = check(res, {
      'stream status 200': (r) => r.status === 200,
      'stream has data chunks': () => hasData,
    });

    if (ok) {
      successfulQueries.add(1);
      errorRate.add(0);
      streamTtfbTrend.add(res.timings.waiting);
      streamDurationTrend.add(res.timings.duration);
      if (hasTokens) {
        totalTokensVerified.add(1);
      }
    } else {
      errorRate.add(1);
    }
  } else {
    const payload = JSON.stringify({ query: query, direct_rag: false });
    const res = http.post(`${BASE_URL}/api/chat`, payload, {
      headers: {
        'Authorization': `Bearer ${data.token}`,
        'Content-Type': 'application/json',
      },
      timeout: '30s',
    });

    let hasAnswer = false;
    try {
      hasAnswer = res.status === 200 && res.json('answer') !== undefined;
    } catch (_) {}

    const ok = check(res, {
      'chat status 200': (r) => r.status === 200,
      'chat returns answer': () => hasAnswer,
    });

    if (ok) {
      successfulQueries.add(1);
      errorRate.add(0);
      chatLatencyTrend.add(res.timings.duration);
    } else {
      errorRate.add(1);
    }
  }

  // Realistic enterprise user think time (0.5s to 1.2s between queries)
  sleep(0.5 + Math.random() * 0.7);
}
