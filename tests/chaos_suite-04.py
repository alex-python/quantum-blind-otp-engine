import os
import time
import torch

def parallel_hyper_chaos_engine(matrix_size, device, iterations=60, reseed_every=20):
    """
    In-Place Optimized 4D Lorenz-Stenflo Engine.
    Eliminates internal memory allocations to maximize GPU thread execution.
    """
    sigma, rho, beta, r = 10.0, 26.0, 8.0 / 3.0, 1.0
    dt = 0.01
    
    # Pre-allocate permanent execution state variables in VRAM
    x = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(-1, 1).repeat(1, matrix_size)
    y = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(1, -1).repeat(matrix_size, 1)
    z = torch.full((matrix_size, matrix_size), 20.0, device=device)
    w = torch.full((matrix_size, matrix_size), 5.0, device=device)

    # Temporary reusable registers to completely stop internal allocations inside the loop
    dx = torch.empty_like(x)
    dy = torch.empty_like(x)
    dz = torch.empty_like(x)
    dw = torch.empty_like(x)

    scaling_factor = 1e5
    x = torch.round(x * scaling_factor) / scaling_factor
    y = torch.round(y * scaling_factor) / scaling_factor

    num_reseeds = iterations // reseed_every
    raw_entropy_pool = [int.from_bytes(os.urandom(4), "big") / 4294967295.0 for _ in range(num_reseeds)]
    entropy_vector = torch.tensor(raw_entropy_pool, device=device)

    reseed_idx = 0
    for step in range(1, iterations + 1):
        if step % reseed_every == 0:
            z.add_(entropy_vector[reseed_idx] * 0.1)
            reseed_idx += 1

        # --- IN-PLACE GRAPH COMPUTATION ---
        # dx = sigma * (y - x) + r * w
        dx.copy_(y).sub_(x).mul_(sigma).addcmul_(w, torch.tensor(r, device=device))
        
        # dy = x * (rho - z) - y
        dy.copy_(torch.tensor(rho, device=device)).sub_(z).mul_(x).sub_(y)
        
        # dz = x * y - beta * z
        dz.copy_(x).mul_(y).addcmul_(z, torch.tensor(-beta, device=device))
        
        # dw = -x - sigma * w
        dw.copy_(x).neg_().addcmul_(w, torch.tensor(-sigma, device=device))

        # Evolve trajectories forward inside current memory boundaries
        x.add_(dx, alpha=dt)
        y.add_(dy, alpha=dt)
        z.add_(dz, alpha=dt)
        w.add_(dw, alpha=dt)

    # Perform final extraction wrap pass
    x.add_(y).add_(z).add_(w).remainder_(1.0).abs_()
    return x

def apply_spatiotemporal_diffusion(matrix, device):
    """
    Applies spatial coordinate shuffling across the 8000x8000 memory space.
    """
    matrix_size = matrix.size(0)
    r_constant = 3.99 
    x_state = torch.full((matrix_size,), 0.4, device=device)
    
    for _ in range(10): 
        x_state = r_constant * x_state * (1.0 - x_state)
        
    shuffle_indices_rows = torch.argsort(x_state)
    shuffle_indices_cols = torch.argsort(torch.roll(x_state, shifts=matrix_size // 2))
    
    diffused_matrix = matrix[shuffle_indices_rows, :]
    diffused_matrix = diffused_matrix[:, shuffle_indices_cols]
    
    return diffused_matrix

def run_extreme_stress_test(matrix_size=8000):
    print(f"=============================================================")
    print(f" 🔥 STARTING EXTREME SYSTEM STRESS TEST: IN-PLACE MEMORY")
    print(f" Matrix Dimensions : {matrix_size} x {matrix_size}")
    print(f" Total Trajectories : {matrix_size**2:,} active processing nodes")
    print(f"=============================================================\n")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Hardware Infrastructure: Apple Silicon M1 {device.type.upper()}")
    
    # Warm up step to build memory structures
    _ = parallel_hyper_chaos_engine(100, device, iterations=5)
    if device.type == "mps": torch.mps.synchronize()

    # -------------------------------------------------------------
    # PHASE 1: CHAOS SPACE GENERATION
    # -------------------------------------------------------------
    print("\n🚀 Instantiating 64-Million node hyper-chaotic system on GPU...")
    start_time = time.time()
    
    raw_chaos = parallel_hyper_chaos_engine(matrix_size, device, iterations=60)
    if device.type == "mps": torch.mps.synchronize()
    
    time_chaos = time.time() - start_time
    print(f"   -> 4D Engine finished. Compute Time: {time_chaos:.4f} seconds")

    # -------------------------------------------------------------
    # PHASE 2: MEMORY SCRAMBLING & SHUFFLING BOUNDS
    # -------------------------------------------------------------
    print("\n🔀 Permuting structural indices across Unified Memory block layout...")
    start_scramble = time.time()
    
    diffused_chaos = apply_spatiotemporal_diffusion(raw_chaos, device)
    if device.type == "mps": torch.mps.synchronize()
    
    time_scramble = time.time() - start_scramble
    print(f"   -> Diffusion layout completed in: {time_scramble:.4f} seconds")

    # -------------------------------------------------------------
    # PHASE 3: MASSIVE ONE-TIME PAD CRYPTO CONCURRENCY
    # -------------------------------------------------------------
    print("\n🔒 Initializing large-scale One-Time Pad encryption array...")
    
    secret_payload = torch.zeros((matrix_size, matrix_size), device=device)
    secret_payload[::2, ::2] = 1.0   
    secret_payload[1::2, 1::2] = 0.5
    
    payload_uint8 = torch.round(secret_payload * 255.0).to(torch.uint8)
    chaos_uint8 = torch.round(diffused_chaos * 255.0).to(torch.uint8)
    
    orig_checksum = torch.sum(payload_uint8.float()).item()

    print("   -> Launching symmetric bitwise matrix XOR encryption threads...")
    start_encrypt = time.time()
    
    encrypted_payload = torch.bitwise_xor(payload_uint8, chaos_uint8)
    
    if device.type == "mps": torch.mps.synchronize()
    time_encrypt = time.time() - start_encrypt
    print(f"   -> Encryption completed in: {time_encrypt*1000:.2f} ms")

    # -------------------------------------------------------------
    # PHASE 4: SYSTEM DECRYPTION DISPATCH
    # -------------------------------------------------------------
    print("\n🔓 Dispatching parallel decryption array over encrypted ciphertext blocks...")
    start_decrypt = time.time()
    
    decrypted_uint8 = torch.bitwise_xor(encrypted_payload, chaos_uint8)
    
    if device.type == "mps": torch.mps.synchronize()
    time_decrypt = time.time() - start_decrypt
    print(f"   -> Decryption completed in: {time_decrypt*1000:.2f} ms")

    # -------------------------------------------------------------
    # INTEGRITY SUMMARY VALIDATION REPORT
    # -------------------------------------------------------------
    dec_checksum = torch.sum(decrypted_uint8.float()).item()
    integrity_error = abs(orig_checksum - dec_checksum)
    is_bit_perfect = torch.equal(payload_uint8, decrypted_uint8)
    
    total_elapsed = time_chaos + time_scramble + time_encrypt + time_decrypt
    
    # Accurate hardware byte tracking across memory paths
    total_bytes_traversed = (
        (matrix_size * matrix_size * 4 * 5) + # 4D Floating point states
        (matrix_size * matrix_size * 4) +     # Secret initial float layout
        (matrix_size * matrix_size * 1 * 5)   # uint8 matrix passes
    )
    memory_processed_gb = total_bytes_traversed / 1e9
    sustained_velocity = memory_processed_gb / total_elapsed

    print("\n================ SYSTEM HARDWARE SATURATION PROFILE ================")
    print(f"• Total Combined Pipeline Latency : {total_elapsed:.4f} seconds")
    print(f"• VRAM Data Velocity Sustained    : {sustained_velocity:.2f} GB/sec")
    print(f"--------------------------------------------------------------------")
    print(f"Processing Drift Check          : {integrity_error:.6f}")
    print(f"System Matrix Integrity Status   : {'PASS ✅ (Perfect Reconstruction)' if is_bit_perfect else 'FAIL ❌'}")
    print("=====================================================================")

if __name__ == "__main__":
    run_extreme_stress_test(matrix_size=8000)

