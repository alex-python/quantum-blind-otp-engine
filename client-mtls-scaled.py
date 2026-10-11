import asyncio
import httpx
import time
import random
import uuid
import ssl
import csv

SERVER_URL = "https://127.0.0.1:8000"
TOTAL_TRANSACTIONS = 10000  # SCALED TO 10,000 PROLONGED REQUESTS
CONCURRENT_USERS = 20       # INTENSIFIED THREAD SATURATION WORKLOAD

async def send_mock_checkout_request(client, user_id, session_id, task_idx, results_list):
    mock_ledger_vector = [random.random() for _ in range(1000)]
    tx_hash = uuid.uuid4().hex
    
    payload = {
        "session_id": session_id,
        "transaction_id": tx_hash,
        "data_vector": mock_ledger_vector
    }
    
    # Track metrics log details periodically to keep console processing fast
    log_progress = (task_idx % 1000 == 0 or task_idx == TOTAL_TRANSACTIONS)
    
    start_network_clock = time.time()
    try:
        response = await client.post(f"{SERVER_URL}/blind-transaction", json=payload, timeout=10.0)
        network_latency = (time.time() - start_network_clock) * 1000
        
        if response.status_code == 200:
            data = response.json()
            vault_lat = float(data['vault_latency_ms'])
            
            # Store metrics into thread-safe list memory wrapper
            results_list.append([task_idx, f"{network_latency:.4f}", f"{vault_lat:.4f}"])
            
            if log_progress:
                inv = data['inventory_record']
                print(f"   [Milestone {task_idx}/{TOTAL_TRANSACTIONS}] Net RTT: {network_latency:.2f} ms | Vault: {vault_lat:.4f} ms | SKU: {inv['sku_item']} (${inv['unit_price']})")
            return True
        else:
            print(f"   ❌ Packet {task_idx} dropped with error status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Socket Exception on Transaction {task_idx}: {e}")
        return False

async def main():
    print(f"=============================================================")
    print(f" 🔥 STARTING PROLONGED 10K DUAL-RING SECURE mTLS STRESS TEST")
    print(f" System Parameters: {TOTAL_TRANSACTIONS:,} Packets | {CONCURRENT_USERS} Connections")
    print(f"=============================================================\n")

    client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_ssl_context.load_verify_locations(cafile="ssl_context/ca.crt")
    client_ssl_context.load_cert_chain(certfile="ssl_context/client.crt", keyfile="ssl_context/client.key")
    client_ssl_context.check_hostname = False # Loopback matching check bypass

    metrics_accumulator = [] # Master storage array for CSV writing
    limits = httpx.Limits(max_keepalive_connections=CONCURRENT_USERS, max_connections=CONCURRENT_USERS)
    
    async with httpx.AsyncClient(limits=limits, verify=client_ssl_context, timeout=15.0) as client:
        print("🤝 Phase 1: Negotiating Ephemeral Session Handshake over mTLS...")
        handshake_resp = await client.post(f"{SERVER_URL}/handshake")
        if handshake_resp.status_code != 200:
            print("❌ Critical Handshake Failure. Aborting pipeline execution.")
            return
            
        handshake_data = handshake_resp.json()
        session_id = handshake_data["session_id"]
        print(f"   -> Session Handshake Bound. Sync Pointer ID: {session_id}\n")
        
        print(f"⚡ Phase 2: Flooding pipeline with {TOTAL_TRANSACTIONS:,} requests...")
        start_test_suite = time.time()
        
        tasks = []
        for i in range(TOTAL_TRANSACTIONS):
            task = asyncio.create_task(
                send_mock_checkout_request(client, (i % CONCURRENT_USERS) + 1, session_id, i + 1, metrics_accumulator)
            )
            tasks.append(task)
            await asyncio.sleep(0.0001) # Ultra-tight pacing delay
            
        print("   -> Sockets flooded. Processing continuous data streams...")
        execution_results = await asyncio.gather(*tasks)
        total_test_duration = time.time() - start_test_suite

    # -------------------------------------------------------------
    # FILE GENERATION: WRITE PERFORMANCE_METRICS.CSV TO DISK
    # -------------------------------------------------------------
    print("\n📝 Phase 3: Exporting latency data to file system...")
    csv_filename = "performance_metrics.csv"
    with open(csv_filename, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        # Write headers
        writer.writerow(["Transaction_Index", "Network_RTT_ms", "Internal_Vault_Latency_ms"])
        # Bulk write matrix values
        writer.writerows(metrics_accumulator)

    # Calculate system totals
    success_count = sum(1 for r in execution_results if r)
    failures = TOTAL_TRANSACTIONS - success_count
    
    rtts = [float(row[1]) for row in metrics_accumulator]
    vaults = [float(row[2]) for row in metrics_accumulator]
    avg_rtt = sum(rtts) / len(rtts) if rtts else 0
    avg_vault = sum(vaults) / len(vaults) if vaults else 0

    print("\n================ SYSTEM HIGH-VOLUME PROLONGED WORKLOAD PROFILE ================")
    print(f"• Total Stress Test Duration     : {total_test_duration:.4f} seconds")
    print(f"• Total Completed Transactions   : {success_count:,}")
    print(f"• Total Failed Requests (503s)   : {failures} (Double-Ring Starvation Check)")
    print(f"• Average HTTP Round-Trip Speed  : {avg_rtt:.2f} ms")
    print(f"• Average Internal Vault Latency : {avg_vault:.4f} ms")
    print(f"• Transaction Processing Density : {success_count / total_test_duration:.2f} Transactions/sec")
    print(f"• Metrics Log Export Status      : SUCCESS ✅ [./{csv_filename}]")
    print(f"• System Stability Verification  : {'PASS 🌟 (Zero Packet Degradation)' if failures == 0 else 'FAIL ❌ QUEUE COLLAPSED'}")
    print("===============================================================================")

if __name__ == "__main__":
    asyncio.run(main())

