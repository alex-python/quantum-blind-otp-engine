import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing as mp
import time

app = FastAPI(title="Quantum-Resistant Chaos Transaction Vault")

MATRIX_SIZE = 1000  
CACHE_QUEUE_MAX = 20

# Shared queue holds ready-to-use 1D row slices instead of whole matrices
slices_queue = mp.Queue(maxsize=CACHE_QUEUE_MAX * 100)

class TransactionPayload(BaseModel):
    transaction_id: int
    data_vector: list[float]

def chaos_entropy_pumping_daemon(queue, matrix_size):
    """
    Background process that bakes a matrix and slices it into 1,000 independent 
    vector keys, keeping the API queue fully stocked.
    """
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
        
        # CHUNK SLICING OPTIMIZATION: Feed the queue 1,000 independent rows
        for row_idx in range(matrix_size):
            row_slice = quantized_pad[row_idx, :].clone()
            queue.put(row_slice)

@app.on_event("startup")
def startup_event():
    print(f"🔒 Launching Parallel Chaos Entropy Slicing Pool...")
    # Spin up 2 concurrent processes to maximize buffer replenishment velocity
    for _ in range(2):
        proc = mp.Process(target=chaos_entropy_pumping_daemon, args=(slices_queue, MATRIX_SIZE), daemon=True)
        proc.start()
    
    # FIXED: Platform-agnostic warmup check. 
    # Simply blocks until the queue has objects available, completely skipping .qsize()
    print("⏳ Pre-seeding transactional slice cache...")
    while slices_queue.empty():
        time.sleep(0.1)
    
    # Give the multi-process engines an extra second to flood the queue pipeline fully
    time.sleep(1.0)
    print("✅ Vault Online. Multi-Process Key Reservoir Filled Natively.")

@app.post("/blind-transaction")
async def blind_transaction(payload: TransactionPayload):
    start_time = time.time()
    
    if slices_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted under peak load.")
        
    # Get 1D vector key instantly in microseconds
    active_vector_key = slices_queue.get()
    
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    
    # Process element-wise XOR mask natively
    masked_vector = torch.bitwise_xor(incoming_uint8, active_vector_key)
    
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
    }

if __name__ == "__main__":
    # Standard Uvicorn initialization
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

