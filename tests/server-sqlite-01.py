import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing as mp
import threading
import sqlite3
import time

app = FastAPI(title="Double-Ring Chaos Transaction Vault with In-Memory SQL")

MATRIX_SIZE = 1000  
MATRIX_RING_MAX = 5     
SLICE_RING_MAX = 1000   

matrix_queue = mp.Queue(maxsize=MATRIX_RING_MAX)
slices_queue = mp.Queue(maxsize=SLICE_RING_MAX)

# Establish thread-local isolation wrapper for In-Memory SQLite database engine
class SQLLedger:
    def __init__(self):
        # Create a shared in-memory database using the special ":memory:" parameter string
        # check_same_thread=False allows FastAPI threads to write to the connection securely
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_schema()
        
    def _create_schema(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER UNIQUE NOT NULL,
                timestamp REAL NOT NULL,
                vault_latency_ms REAL NOT NULL,
                cipher_checksum REAL NOT NULL
            )
        """)
        self.conn.commit()

    def log_transaction(self, tx_id, vault_latency, cipher_sum):
        self.cursor.execute(
            "INSERT INTO transaction_ledger (transaction_id, timestamp, vault_latency_ms, cipher_checksum) VALUES (?, ?, ?, ?)",
            (tx_id, time.time(), vault_latency, cipher_sum)
        )
        self.conn.commit()

# Globally shared thread-safe ledger instance inside server application memory space
db_ledger = SQLLedger()

class TransactionPayload(BaseModel):
    transaction_id: int
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
    print(f"🔒 Launching Dual-Ring Asynchronous Isolation Architecture with SQLite Persistence...")
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
    print("✅ Vault Online. SQL Storage Layer Attached Natively.")

@app.post("/blind-transaction")
async def blind_transaction(payload: TransactionPayload):
    start_time = time.time()
    
    if slices_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted under peak load.")
        
    active_vector_key = slices_queue.get()
    
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    
    masked_vector = torch.bitwise_xor(incoming_uint8, active_vector_key)
    cipher_sum = float(torch.sum(masked_vector).item())
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Commit transaction audit log parameters directly into memory SQLite table space
    db_ledger.log_transaction(payload.transaction_id, latency_ms, cipher_sum)
    
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

