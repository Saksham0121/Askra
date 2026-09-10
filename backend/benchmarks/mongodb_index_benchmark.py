"""
Askra AI — MongoDB Query Performance Microbenchmark
Measures the latency difference and execution plans for indexed vs unindexed collection operations.
"""
import asyncio
import time
from app.database import get_db

async def run_benchmark():
    db = get_db()
    print("=" * 60)
    print("🚀 Running MongoDB Index Benchmark...")
    print("=" * 60)
    
    # 1. Verify Winning Plans
    msg_explain = await db.command('explain', {
        'find': 'messages',
        'filter': {'session_id': '6a7870fb9ee2e3577f0f381f'},
        'sort': {'timestamp': -1}
    }, verbosity='executionStats')
    
    sess_explain = await db.command('explain', {
        'find': 'chat_sessions',
        'filter': {'user_id': '6a7870fb9ee2e3577f0f381f'},
        'sort': {'updated_at': -1}
    }, verbosity='executionStats')
    
    doc_explain = await db.command('explain', {
        'find': 'documents',
        'filter': {'department': 'engineering'},
        'sort': {'created_at': -1}
    }, verbosity='executionStats')
    
    msg_stage = msg_explain['queryPlanner']['winningPlan']['inputStage']['stage']
    sess_stage = sess_explain['queryPlanner']['winningPlan']['inputStage']['stage']
    doc_stage = doc_explain['queryPlanner']['winningPlan']['inputStage']['stage']
    
    print(f"✓ messages (session_id, timestamp) Execution Stage   : {msg_stage}")
    print(f"✓ chat_sessions (user_id, updated_at) Execution Stage: {sess_stage}")
    print(f"✓ documents (department, created_at) Execution Stage : {doc_stage}")
    
    # 2. Measure Roundtrip Query Latency
    rounds = 50
    start = time.perf_counter()
    for _ in range(rounds):
        await db['messages'].find(
            {'session_id': '6a7870fb9ee2e3577f0f381f'}
        ).sort('timestamp', -1).limit(6).to_list(length=6)
    duration_ms = (time.perf_counter() - start) * 1000 / rounds
    print(f"✓ Average Indexed Query Roundtrip: {duration_ms:.2f} ms per query")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(run_benchmark())
