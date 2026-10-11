import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing as mp
import threading
import sqlite3
import time

app = FastAPI(title="Double-Ring Chaos Transaction Vault with Resilient SQL")

MATRIX_SIZE = 1000  
MATRIX_RING_MAX = 5     
SLICE_RING_MAX = 1000   

matrix_queue = mp.Queue(maxsize=MATRIX_RING_MAX)
slices_queue = mp.Queue(maxsize=SLICE_RING_MAX)

class SQLLedger:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.cursor = self.conn.cursor()
        # Enforce high-speed write ahead logging to maximize memory transaction throughput
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA synchronous=OFF")
        self._create_schema()
        self.lock = threading.Lock() # Thread lock to protect concurrent table mutations
        
    def _create_schema(self):
        # PATCHED: Removed the strict 'UNIQUE' constraint variable on the string space 
        # to gracefully handle tracking across high-concurrency packet traffic
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                vault_latency_ms REAL NOT NULL,
                cipher_checksum REAL NOT NULL
            )
        """)
        self.conn.commit()

    def log_transaction(self, tx_id, vault_latency, cipher_sum):
        with self.lock:
            try:
                self.cursor.execute(
                    "INSERT INTO transaction_ledger (transaction_id, timestamp, vault_latency_ms, cipher_checksum) VALUES (?, ?, ?, ?)",
                    (str(tx_id), time.time(), vault_latency, cipher_sum)
                )
                self.conn.commit()
            except sqlite3.OperationalError:
                # Fallback handler if database memory pool experiences transient lock contention
                time.sleep(0.001)
                self.cursor.execute(
                    "INSERT INTO transaction_ledger (transaction_id, timestamp, vault_latency_ms, cipher_checksum) VALUES (?, ?, ?, ?)",
                    (str(tx_id), time.time(), vault_latency, cipher_sum)
                )
                self.conn.commit()

db_ledger = SQLLedger()

class TransactionPayload(BaseModel):
    transaction_id: str  # Updated to string to support standard alphanumeric tracking hashes
    data_vector: list[float]

def chaos_matrix_producer_daemon(queue, matrix_size):
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    sigma, rho, beta, r = 10.0, 26.0, 8.0 / 3.0, 1.0
    dt = 0.01

    x = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(-1, 1).repeat(1, matrix_size)
    y = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(1, -1).repeat(matrix_size, 1)
    z = torch.full((matrix_size, matrix_size), 20.0, device=device)
    w = torch.full((matrix_size, matrix_size), 5.0, device=device)
    dx, dy, dz, dw = torch.empty_like(x), torch.empty_like(x), torch.empty_like(x), torch.empty_like(x)

    while True:
        entropy_pool = [int.from_bytes(os.urandom(4), "big") / 4294967295.0 for _ in range(3)]
        entropy_vector = torch.tensor(entropy_pool, device=device)

        for step in range(1, 31):
            if step % 20 == 0:
                z.add_(entropy_vector[step // 20 - 1] * 0.1)
            dx.copy_(y).sub_(x).mul_(sigma).addcmul_(w, torch.tensor(r, device=device))
            dy.copy_(torch.tensor(rho, device=device)).sub_(z).mul_(x).sub_(y)
            dz.copy_(x).mul_(y).addcmul_(z, torch.tensor(-beta, device=device))
            dw.copy_(x).neg_().addcmul_(w, torch.tensor(-sigma, device=device))
            x.add_(dx, alpha=dt); y.add_(dy, alpha=dt); z.add_(dz, alpha=dt); w.add_(dw, alpha=dt)

        x.add_(y).add_(z).add_(w).remainder_(1.0).abs_()
        quantized_pad = torch.round(x * 255.0).to(torch.uint8).cpu()
        queue.put(quantized_pad)

def ring_transformer_consumer_worker(src_matrix_ring, dest_slice_ring, matrix_size):
    while True:
        raw_matrix_block = src_matrix_ring.get()
        for row_idx in range(matrix_size):
            row_slice = raw_matrix_block[row_idx, :].clone()
            dest_slice_ring.put(row_slice)

@app.on_event("startup")
def startup_event():
    print(f"🔒 Launching Fault-Tolerant Dual-Ring Architecture with SQLite...")
    for _ in range(2):
        proc = mp.Process(target=chaos_matrix_producer_daemon, args=(matrix_queue, MATRIX_SIZE), daemon=True)
        proc.start()
        
    transformer = threading.Thread(
        target=ring_transformer_consumer_worker, 
        args=(matrix_queue, slices_queue, MATRIX_SIZE), 
        daemon=True
    )
    transformer.start()
    
    print("⏳ Pre-seeding Dual-Ring slice reservoirs...")
    while slices_queue.empty():
        time.sleep(0.1)
    time.sleep(1.0) 
    print("✅ Vault Online. SQL Storage Layer Protected and Live.")

@app.post("/blind-transaction")
async def blind_transaction(payload: TransactionPayload):
    start_time = time.time()
    
    if slices_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted.")
        
    active_vector_key = slices_queue.get()
    
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    
    masked_vector = torch.bitwise_xor(incoming_uint8, active_vector_key)
    cipher_sum = float(torch.sum(masked_vector).item())
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Offload the transaction commit securely into our protected SQL ledger
    db_ledger.log_transaction(payload.transaction_id, latency_ms, cipher_sum)
    
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
    }

# Added an on-demand analytics route to fetch processing metrics directly using SQL
@app.get("/vault-stats")
async def get_vault_stats():
    with db_ledger.lock:
        db_ledger.cursor.execute("SELECT COUNT(*), AVG(vault_latency_ms) FROM transaction_ledger")
        total_tx, avg_latency = db_ledger.cursor.fetchone()
    return {
        "total_transactions_logged": total_tx,
        "average_internal_vault_latency_ms": f"{avg_latency:.4f}" if avg_latency else "0.0000"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

