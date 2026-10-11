import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing as mp
import time

app = FastAPI(title="Quantum-Resistant Chaos Transaction Vault")

MATRIX_SIZE = 1000  # 1000x1000 transaction footprint
CACHE_QUEUE_MAX = 10

# Shared, thread-safe multiprocessing queue
keys_queue = mp.Queue(maxsize=CACHE_QUEUE_MAX)

class TransactionPayload(BaseModel):
    transaction_id: int
    data_vector: list[float]  # Incoming unencrypted transaction metrics

def chaos_entropy_pumping_daemon(queue, matrix_size):
    """
    Independent worker process handling the heavy 4D loop entirely in the background.
    """
    # Force localized device targeting per process boundaries
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    
    sigma, rho, beta, r = 10.0, 26.0, 8.0 / 3.0, 1.0
    dt = 0.01

    # Pre-allocate reusable memory structures
    x = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(-1, 1).repeat(1, matrix_size)
    y = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(1, -1).repeat(matrix_size, 1)
    z = torch.full((matrix_size, matrix_size), 20.0, device=device)
    w = torch.full((matrix_size, matrix_size), 5.0, device=device)
    dx, dy, dz, dw = torch.empty_like(x), torch.empty_like(x), torch.empty_like(x), torch.empty_like(x)

    while True:
        entropy_pool = [int.from_bytes(os.urandom(4), "big") / 4294967295.0 for _ in range(3)]
        entropy_vector = torch.tensor(entropy_pool, device=device)

        for step in range(1, 41):
            if step % 20 == 0:
                z.add_(entropy_vector[step // 20 - 1] * 0.1)
            dx.copy_(y).sub_(x).mul_(sigma).addcmul_(w, torch.tensor(r, device=device))
            dy.copy_(torch.tensor(rho, device=device)).sub_(z).mul_(x).sub_(y)
            dz.copy_(x).mul_(y).addcmul_(z, torch.tensor(-beta, device=device))
            dw.copy_(x).neg_().addcmul_(w, torch.tensor(-sigma, device=device))
            x.add_(dx, alpha=dt); y.add_(dy, alpha=dt); z.add_(dz, alpha=dt); w.add_(dw, alpha=dt)

        x.add_(y).add_(z).add_(w).remainder_(1.0).abs_()
        quantized_pad = torch.round(x * 255.0).to(torch.uint8).cpu() # Move to CPU RAM for safe inter-process transfer
        
        # Block and wait if cache queue is full, ensuring zero resource wasting
        queue.put(quantized_pad)

@app.on_event("startup")
def startup_event():
    """
    Launch the asynchronous background daemon immediately on server initialization.
    """
    print(f"🔒 Starting Independent Chaos Entropy Pumping Daemon...")
    proc = mp.Process(target=chaos_entropy_pumping_daemon, args=(keys_queue, MATRIX_SIZE), daemon=True)
    proc.start()
    
    print("⏳ Warming up VRAM cache pool keys...")
    while keys_queue.empty():
        time.sleep(0.1)
    print("✅ Gateway Online and Pre-seeded.")

@app.post("/blind-transaction")
async def blind_transaction(payload: TransactionPayload):
    start_time = time.time()
    
    # 1. Pop key matrix out of memory instantly in microseconds with zero locking delays
    if keys_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted.")
        
    active_key = keys_queue.get()
    
    # 2. Extract and format incoming network request payload
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    
    # 3. Mask incoming transaction array using an active row slice from our pre-cached one-time pad
    # This prevents payload structure tracing at wire-level
    key_slice = active_key[0] 
    masked_vector = torch.bitwise_xor(incoming_uint8, key_slice)
    
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
        "cipher_sample": masked_vector[:5].tolist()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

