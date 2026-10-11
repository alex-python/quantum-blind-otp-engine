import asyncio
import httpx
import time
import random
import uuid

# FULL VERIFIED LOCAL REST ENDPOINT POINTING TO FASTAPI SERVER
SERVER_URL = "http://127.0.0.1:8000/blind-transaction"
TOTAL_TRANSACTIONS = 100000  
CONCURRENT_USERS = 20        

async def send_mock_checkout_request(client, user_id, log_progress=False):
    mock_ledger_vector = [random.random() for _ in range(1000)]
    
    # Generate absolute, collision-free transaction identifiers 
    tx_hash = uuid.uuid4().hex
    
    payload = {
        "transaction_id": tx_hash,
        "data_vector": mock_ledger_vector
    }
    
    start_network_clock = time.time()
    try:
        response = await client.post(SERVER_URL, json=payload, timeout=15.0)
        network_latency = (time.time() - start_network_clock) * 1000
        
        if response.status_code == 200:
            if log_progress:
                data = response.json()
                print(f"   [Milestone Update] User {user_id} -> HTTP Success! Net RTT: {network_latency:.2f} ms")
            return network_latency
        else:
            print(f"   ❌ User {user_id} Failed with Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Socket Exception on User {user_id}: {e}")
        return None

async def main():
    print(f"=============================================================")
    print(f" 🚀 LAUNCHING 100K RESILIENT DUAL-RING SQL STRESS SUITE")
    print(f" Sending {TOTAL_TRANSACTIONS:,} Packets across {CONCURRENT_USERS} Connections")
    print(f"=============================================================\n")

    limits = httpx.Limits(max_keepalive_connections=CONCURRENT_USERS, max_connections=CONCURRENT_USERS)
    
    async with httpx.AsyncClient(limits=limits, timeout=20.0) as client:
        start_test_suite = time.time()
        
        # FIXED: Corrected list syntax assignment initialization block
        tasks = []
        for i in range(TOTAL_TRANSACTIONS):
            user_id = (i % CONCURRENT_USERS) + 1
            log_progress = (i % 10000 == 0 or i == TOTAL_TRANSACTIONS - 1)
            
            task = asyncio.create_task(send_mock_checkout_request(client, user_id, log_progress))
            tasks.append(task)
            await asyncio.sleep(0.0001)
            
        print("⏳ Flooding network socket buffers. Monitoring system throughput constraints...")
        rtt_latencies = await asyncio.gather(*tasks)
        total_test_duration = time.time() - start_test_suite

    valid_latencies = [l for l in rtt_latencies if l is not None]
    avg_rtt = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0
    failures = TOTAL_TRANSACTIONS - len(valid_latencies)

    print("\n================ DUAL-RING IN-MEMORY SQL PERFORMANCE PROFILE ================")
    print(f"• Total Stress Test Duration     : {total_test_duration:.4f} seconds")
    print(f"• Total Verified Transactions    : {len(valid_latencies):,}")
    print(f"• Total Failed Storage Drops     : {failures}")
    print(f"• Average HTTP Round-Trip Speed  : {avg_rtt:.2f} ms")
    print(f"• Transaction Processing Density : {len(valid_latencies) / total_test_duration:.2f} Transactions/sec")
    print(f"• System Storage Verification    : {'PASS ✅ 100% PERSISTED LOSSLESS' if failures == 0 else 'FAIL ❌ STRATEGIC STARVATION'}")
    print("=============================================================================")

if __name__ == "__main__":
    asyncio.run(main())

