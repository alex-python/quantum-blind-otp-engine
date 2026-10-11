import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import multiprocessing as mp
import threading
import ssl
import time

MATRIX_SIZE = 1000  
MATRIX_RING_MAX = 5     
SLICE_RING_MAX = 1000   

matrix_queue = mp.Queue(maxsize=MATRIX_RING_MAX)
slices_queue = mp.Queue(maxsize=SLICE_RING_MAX)
session_indices = {}

class HandshakeResponse(BaseModel):
    session_id: str
    initial_seed_index: int

class SecuredPayload(BaseModel):
    session_id: str
    transaction_id: str
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

# FIXED: Modern platform-agnostic context manager lifespan lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🔒 [Lifespan Startup] Initializing Isolated Dual-Ring Architecture...")
    
    # FIXED: Properly initialized list assignment block to register process tracking
    producers = []
    for _ in range(2):
        proc = mp.Process(target=chaos_matrix_producer_daemon, args=(matrix_queue, MATRIX_SIZE), daemon=True)
        proc.start()
        producers.append(proc)
        
    # Start Intermediate Thread Consumer to feed Ring 2
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
    print("✅ Vault Online. Dual-Ring pipelines safe and isolated.")
    yield
    print("🛑 [Lifespan Shutdown] Cleaning up active daemons...")
    for proc in producers:
        proc.terminate()

app = FastAPI(title="mTLS Chaos Double-Ring Vault", lifespan=lifespan)

@app.post("/handshake", response_model=HandshakeResponse)
async def execute_secure_handshake():
    session_id = os.urandom(16).hex()
    synchronized_start_index = int(int.from_bytes(os.urandom(2), "big") % MATRIX_SIZE)
    session_indices[session_id] = synchronized_start_index
    return {"session_id": session_id, "initial_seed_index": synchronized_start_index}

@app.post("/blind-transaction")
async def blind_transaction(payload: SecuredPayload):
    start_time = time.time()
    if payload.session_id not in session_indices:
        raise HTTPException(status_code=403, detail="Unauthorized session context.")
    if slices_queue.empty():
        raise HTTPException(status_code=503, detail="Entropy reservoir depleted.")
        
    active_vector = slices_queue.get()
    synchronized_key_vector = active_vector.clone()
    
    current_idx = session_indices[payload.session_id]
    session_indices[payload.session_id] = (current_idx + 1) % MATRIX_SIZE
    
    incoming_data = torch.tensor(payload.data_vector)
    incoming_uint8 = torch.round(incoming_data * 255.0).to(torch.uint8)
    masked_vector = torch.bitwise_xor(incoming_uint8, synchronized_key_vector)
    
    latency_ms = (time.time() - start_time) * 1000
    return {
        "status": "AUTHORIZED",
        "transaction_id": payload.transaction_id,
        "vault_latency_ms": f"{latency_ms:.4f}",
    }

if __name__ == "__main__":
    # Launch Uvicorn server passing configuration variables directly 
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_level="warning",
        ssl_certfile="ssl_context/server.crt",
        ssl_keyfile="ssl_context/server.key",
        ssl_ca_certs="ssl_context/ca.crt",
        ssl_cert_reqs=ssl.CERT_REQUIRED
    )

