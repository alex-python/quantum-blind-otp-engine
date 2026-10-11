import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import multiprocessing as mp
import threading
import time

app = FastAPI(title="Double-Ring Chaos Transaction Vault")

MATRIX_SIZE = 1000  
MATRIX_RING_MAX = 5     # Ring 1: Holds raw multi-megabyte matrix blocks
SLICE_RING_MAX = 1000   # Ring 2: Holds lightweight pre-sliced ready vectors

# Instantiate the two independent processing rings
matrix_queue = mp.Queue(maxsize=MATRIX_RING_MAX)
slices_queue = mp.Queue(maxsize=SLICE_RING_MAX)

class TransactionPayload(BaseModel):
    transaction_id: int
    data_vector: list[float]

def chaos_matrix_producer_daemon(queue, matrix_size):
    """
    RING 1 PRODUCER: Independent heavy worker process calculating 4D hyper-chaos
    matrices on the GPU, dumping completed blocks into the first ring buffer.
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
        quantized_pad = torch.round(x * 255.0).to(torch.uint8).cpu() # Move to shared CPU space
        
        # Ship whole matrix block to Ring 1
        queue.put(quantized_pad)

def ring_transformer_consumer_worker(src_matrix_ring, dest_slice_ring, matrix_size):
    """
    INTERMEDIATE TRANSFORMER: Thread that drains raw matrix blocks from Ring 1,
    slices them on the fly, and floods Ring 2 with ready-to-consume vectors.
    """
    while True:
        # Pull a whole block from Ring 1 (Blocks if Ring 1 is empty)
        raw_matrix_block = src_matrix_ring.get()
        
        # Break down block into individual rows and stream into Ring 2
        for row_idx in range(matrix_size):
            row_slice = raw_matrix_block[row_idx, :].clone()
            # This blocks natively if the consumer slice ring fills up under light load
            dest_slice_ring.put(row_slice)

@app.on_event("startup")
def startup_event():
    print(f"🔒 Launching Dual-Ring Asynchronous Isolation Architecture...")
    
    # 1. Start Multi-Process GPU Producers for Ring 1
    for _ in range(2):
        proc = mp.Process(target=chaos_matrix_producer_daemon, args=(matrix_queue, MATRIX_SIZE), daemon=True)
        proc.start()
        
    # 2. Start Intermediate Thread Consumer to feed Ring 2
    transformer = threading.Thread(
        target=ring_transformer_consumer_worker, 
        args=(matrix_queue, slices_queue, MATRIX_SIZE), 
        daemon=True
    )
    transformer.start()
    
    print("⏳ Pre-seeding Dual-Ring slice reservoirs...")
    while slices_queue.empty():
        time.sleep(0.1)
        
    time.sleep(1.0) # Allow buffer to build initial runway cushion
    print("✅ Vault Online. Dual-Ring pipeline isolated and warm.")

@app.post("/blind-transaction")
async def blind_transaction(payload: TransactionPayload):
    start_time = time.time()
    
    if slices_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted under peak load.")
        
    # Consumer critical path pulls isolated row slices out of Ring 2 instantly
    active_vector_key = slices_queue.get()
    
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    
    masked_vector = torch.bitwise_xor(incoming_uint8, active_vector_key)
    
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

