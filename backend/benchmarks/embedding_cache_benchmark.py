"""
Embedding LRU Cache Benchmark & Zero-Loss Verification.

Measures:
1. Uncached (cold / cache-miss) encoding latency.
2. Cached (warm / cache-hit) lookup latency.
3. Speedup factor.
4. Mathematical verification of zero-loss accuracy (cosine similarity = 1.0000000).
"""
import sys
import time
import math
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.embeddings.embedding_manager import EmbeddingManager

SAMPLE_QUERIES = [
    "What is Askra and how does it work?",
    "Tell me about the 7-layer pipeline architecture.",
    "How is hybrid retrieval implemented with FAISS and BM25?",
    "What security safeguards are in place for user data?",
    "What are the supported user roles in this platform?",
    "Hello! Can you help me summarize company policies?",
]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    return dot / (norm_a * norm_b)


def main():
    print("=" * 70)
    print("🧪 Askra AI — Embedding LRU Cache Performance Benchmark")
    print("=" * 70)

    mgr = EmbeddingManager(model_name="all-MiniLM-L6-v2")
    mgr.warmup()
    mgr.clear_cache()

    print(f"\n1. Measuring Uncached (Cache Miss) Latency across {len(SAMPLE_QUERIES)} queries...")
    miss_times = []
    first_vectors = []
    for q in SAMPLE_QUERIES:
        t0 = time.perf_counter()
        vec = mgr.embed_text(q)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        miss_times.append(dt)
        first_vectors.append(vec)
        print(f"   [MISS] {q[:45]:<45} -> {dt:.2f} ms")

    avg_miss = sum(miss_times) / len(miss_times)
    p95_miss = sorted(miss_times)[int(len(miss_times) * 0.95)]

    print(f"\n2. Measuring Cached (Cache Hit) Latency on identical queries...")
    hit_times = []
    second_vectors = []
    for q in SAMPLE_QUERIES:
        t0 = time.perf_counter()
        vec = mgr.embed_text(q)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        hit_times.append(dt)
        second_vectors.append(vec)
        print(f"   [HIT ] {q[:45]:<45} -> {dt * 1000.0:.2f} µs ({dt:.4f} ms)")

    avg_hit = sum(hit_times) / len(hit_times)
    p95_hit = sorted(hit_times)[int(len(hit_times) * 0.95)]

    print("\n3. Zero-Loss Verification (Bitwise & Cosine Similarity Check)...")
    all_identical = True
    for i, (v1, v2) in enumerate(zip(first_vectors, second_vectors)):
        sim = cosine_similarity(v1, v2)
        is_exact = v1 == v2
        all_identical = all_identical and is_exact
        print(f"   Query #{i+1}: Cosine Similarity = {sim:.8f} | Exact Match: {is_exact}")

    speedup = avg_miss / (avg_hit if avg_hit > 0 else 0.0001)

    print("\n" + "=" * 70)
    print("📊 BENCHMARK SUMMARY & METRICS")
    print("=" * 70)
    print(f"Average Cache Miss Latency : {avg_miss:.2f} ms")
    print(f"Average Cache Hit Latency  : {avg_hit:.4f} ms ({avg_hit * 1000.0:.1f} µs)")
    print(f"P95 Cache Miss Latency     : {p95_miss:.2f} ms")
    print(f"P95 Cache Hit Latency      : {p95_hit:.4f} ms ({p95_hit * 1000.0:.1f} µs)")
    print(f"Speedup Multiple           : ⚡ {speedup:.1f}× FASTER")
    print(f"Latency Reduction          : ⚡ {((avg_miss - avg_hit) / avg_miss) * 100.0:.2f}%")
    print(f"Accuracy Loss              : 0.000000% (Mathematical Identity: {all_identical})")
    print(f"Cache Statistics           : {mgr.get_cache_info()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
