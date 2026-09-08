# 🚀 Askra AI — k6 Performance & Load Testing Suite

This directory contains automated **Grafana k6** load testing scripts to benchmark Askra's backend latency, concurrency capacity, and Server-Sent Events (SSE) streaming performance.

---

## 📋 Available Test Suites

| Script | Purpose | VUs (Virtual Users) | Duration |
| :--- | :--- | :--- | :--- |
| [`smoke_test.js`](./smoke_test.js) | Rapid sanity check for API & auth endpoints | 1 VU | 15s |
| [`load_test.js`](./load_test.js) | Concurrency load test measuring P50, P95, RPS under pressure | Up to 15 VUs | ~70s |

---

## ⚙️ How to Run

### 1. Ensure Askra Backend is Running
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

### 2. Run the Smoke Test
```bash
k6 run benchmarks/k6/smoke_test.js
```

### 3. Run the Full Load Test
```bash
k6 run benchmarks/k6/load_test.js
```

---

## 📊 How to Translate k6 Output into Resume Metrics

When k6 finishes, it outputs a summary table. Here is how to map those fields to strong resume bullet points:

| k6 Terminal Metric | Meaning | Example Resume Citation |
| :--- | :--- | :--- |
| `stream_ttfb_waiting_ms (p95)` | **Time-To-First-Token (TTFT)** | *"Reduced Time-To-First-Token (TTFT) from ~3.2s to 125ms via true chunked SSE streaming."* |
| `http_req_duration (p95)` | **P95 Latency** | *"Cut P95 response latency from 4.8s to 640ms across 7-layer pipeline."* |
| `http_reqs / s` | **Throughput (RPS)** | *"Scaled sustained throughput by 3.5× to 28+ RPS under concurrent user load."* |
| `checks_succeeded (100%)` | **Reliability** | *"Achieved 99.9% uptime and zero request dropouts during stress testing with Grafana k6."* |
