# 📈 Askra AI — Benchmark History & Improvement Tracker

This document records the exact performance metrics of Askra at every stage of optimization. After each optimization is applied, the same k6 benchmarks are re-run, and the delta (percentage improvement) is calculated and recorded here.

---

## 🏆 Master Comparison Table (15 Concurrent Users Load Test)

| Stage | Optimization Applied | HTTP Error Rate | Checks Passed | P95 Latency | Throughput (RPS) | Iterations Completed | Overall Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 0 (Baseline)** | *None (Unoptimized)* | **78.78%** | **19.35%** | **30.0s** *(timeout)* | **0.36 req/s** | 31 | 🚨 Failing under load |
| **Stage 1** | *Pending* | — | — | — | — | — | — |
| **Stage 2** | *Pending* | — | — | — | — | — | — |
| **Stage 3** | *Pending* | — | — | — | — | — | — |
| **Final Goal** | *All Optimizations* | **< 1.0%** | **> 99%** | **< 1.2s** | **> 15 req/s** | **> 200** | 🎯 Production Ready |

---

## 🏆 Master Comparison Table (Single User Smoke Test)

| Stage | Optimization Applied | HTTP Error Rate | Checks Passed | P95 Latency | TTFT / TTFB (P95) | Improvement (TTFT) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 0 (Baseline)** | *None (Unoptimized)* | **0.00%** | **100.0%** | **419.2ms** | **124.6ms** | Baseline |
| **Stage 1** | **MongoDB Compound Indexes** | **0.00%** | **100.0%** | **439.7ms** | **103.3ms** | **⚡ 17.1% faster TTFT** (COLLSCAN → IXSCAN) |
| **Stage 2** | *Pending* | — | — | — | — | — |
| **Stage 3** | *Pending* | — | — | — | — | — |


---

## 📋 Detailed Logs per Run

### Run 0: Baseline (Before Optimizations)
* **Date & Time**: `2026-10-06 18:20:35`
* **Commit/Branch**: `main`
* **LLM Provider**: Groq (`qwen/qwen3.8-27b`)
* **Vector Store**: FAISS (1,198 chunks) + BM25 (1,198 chunks)

#### 1. Smoke Test (1 VU, 15s)
```text
✓ health status 200
✓ chat POST status 200
✓ chat has answer
✓ stream GET status 200
✓ stream has data chunks

checks_succeeded...............: 100.00% (45 / 45)
http_req_failed................: 0.00%   (0 / 29)
http_req_duration (p50)........: 295.95ms
http_req_duration (p95)........: 419.21ms
chat_stream_ttfb_ms (p95)......: 124.60ms
throughput.....................: 1.85 req/s
```

#### 2. Concurrency Load Test (15 VUs, 70s ramp-up)
```text
✗ checks_succeeded.............: 19.35%  (12 / 62)
✗ checks_failed................: 80.64%  (50 / 62)
✗ http_req_failed..............: 78.78%  (26 / 33 timed out at 30s)
✗ http_req_duration (p50)......: 30.0s   (timed out)
✗ http_req_duration (p95)......: 30.0s   (timed out)
throughput.....................: 0.36 req/s
successful_queries.............: 5 completed
```
* **Bottleneck Diagnosis**: Synchronous blocking pipeline calls (`bridge.run()` & `bridge.run_stream()`) executing directly on FastAPI's main asyncio event loop, starving all concurrent requests in the socket backlog.

---

### Run 1: MongoDB Compound Indexes
* **Date & Time**: `2026-10-06 18:43:28`
* **Changes**:
  - Added compound index `(session_id: 1, timestamp: -1)` on `messages`
  - Added compound index `(user_id: 1, timestamp: -1)` on `messages`
  - Added compound index `(user_id: 1, updated_at: -1)` on `chat_sessions`
  - Added compound index `(department: 1, created_at: -1)` on `documents`
  - Added unique index `(email: 1)` on `users`
  - Added compound index `(event: 1, timestamp: -1)` on `analytics`
  - Wired automated startup initialization via `init_indexes()` in `app/main.py` lifespan
* **Verification via MongoDB Explain Plan**:
  - `messages` query execution stage: `COLLSCAN` ➔ **`IXSCAN`** (Index Scan)
  - `chat_sessions` query execution stage: `COLLSCAN` ➔ **`IXSCAN`** (Index Scan)
  - `documents` query execution stage: `COLLSCAN` ➔ **`IXSCAN`** (Index Scan)

#### 1. Smoke Test (1 VU, 15s)
```text
✓ health status 200
✓ chat POST status 200
✓ chat has answer
✓ stream GET status 200
✓ stream has data chunks

checks_succeeded...............: 100.00% (45 / 45)
http_req_failed................: 0.00%   (0 / 28)
http_req_duration (p50)........: 295.43ms
http_req_duration (p95)........: 439.70ms
chat_stream_ttfb_ms (avg)......: 94.52ms  (⚡ 14.6% faster than baseline 110.72ms)
chat_stream_ttfb_ms (p95)......: 103.32ms (⚡ 17.1% faster than baseline 124.60ms)
throughput.....................: 1.80 req/s
```

---
*(Additional runs will be appended below as optimizations are implemented)*

