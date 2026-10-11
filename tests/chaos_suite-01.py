import os
import time
import torch

def parallel_hyper_chaos_engine(matrix_size, device, iterations=60, reseed_every=20):
    """
    4D Hyper-chaotic Lorenz-Stenflo Engine running in parallel 
    on the GPU using scaled fixed-point quantization mechanics.
    """
    sigma, rho, beta, r = 10.0, 26.0, 8.0 / 3.0, 1.0
    dt = 0.01
    
    x = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(-1, 1).repeat(1, matrix_size)
    y = torch.linspace(-15.0, 15.0, matrix_size, device=device).view(1, -1).repeat(matrix_size, 1)
    z = torch.full((matrix_size, matrix_size), 20.0, device=device)
    w = torch.full((matrix_size, matrix_size), 5.0, device=device)

    scaling_factor = 1e5
    x = torch.round(x * scaling_factor) / scaling_factor
    y = torch.round(y * scaling_factor) / scaling_factor

    for step in range(1, iterations + 1):
        if step % reseed_every == 0:
            hw_entropy = int.from_bytes(os.urandom(4), "big") / 4294967295.0
            z = z + (hw_entropy * 0.1)

        dx = sigma * (y - x) + r * w
        dy = x * (rho - z) - y
        dz = x * y - beta * z
        dw = -x - sigma * w

        x = x + dx * dt
        y = y + dy * dt
        z = z + dz * dt
        w = w + dw * dt

    chaos_field = torch.abs((x + y + z + w) % 1.0)
    return chaos_field

def apply_spatiotemporal_diffusion(matrix, device):
    """
    Shuffles memory addresses across the tensor topology using 
    indexes calculated from a secondary chaotic framework.
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

def calculate_shannon_entropy(tensor, bins=256):
    """
    Calculates the Shannon Entropy score of a matrix block.
    """
    if tensor.dtype == torch.uint8:
        quantized = tensor.long()
    else:
        quantized = torch.clamp((tensor * bins).long(), 0, bins - 1)
        
    hist = torch.bincount(quantized.flatten(), minlength=bins).float()
    probs = hist / tensor.numel()
    probs = probs[probs > 0]
    return -torch.sum(probs * torch.log2(probs)).item()

def run_cryptographic_pipeline(matrix_size=2000):
    print(f"=============================================================")
    print(f" EXPERIMENT: FULLY ENHANCED CHAOS SUITE WITH ANALYSIS & CRYPTO")
    print(f" Matrix Dimensions: {matrix_size} x {matrix_size} ({matrix_size**2:,} nodes)")
    print(f"=============================================================\n")

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Active Hardware Platform: Apple Silicon M1 {device.type.upper()}\n")

    # -------------------------------------------------------------
    # PHASE 1: GENERATE RAW CHAOS FIELD & METRIC EVALUATION
    # -------------------------------------------------------------
    print("🌀 Step 1: Spawning 4D Lorenz-Stenflo hyper-chaotic keys...")
    raw_chaos = parallel_hyper_chaos_engine(matrix_size, device, iterations=60)
    if device.type == "mps": torch.mps.synchronize()
    
    entropy_raw = calculate_shannon_entropy(raw_chaos)
    print(f"   -> Raw Chaos Field Shannon Entropy: {entropy_raw:.4f} bits")

    # -------------------------------------------------------------
    # PHASE 2: SPATIOTEMPORAL SCRAMBLING & ACCELERATED ANALYSIS
    # -------------------------------------------------------------
    print("\n🔀 Step 2: Running address diffusion scrambling via Logistic indexes...")
    diffused_chaos = apply_spatiotemporal_diffusion(raw_chaos, device)
    if device.type == "mps": torch.mps.synchronize()
    
    entropy_diffused = calculate_shannon_entropy(diffused_chaos)
    print(f"   -> Post-Diffusion Matrix Shannon Entropy: {entropy_diffused:.4f} bits")

    # -------------------------------------------------------------
    # PHASE 3: CRYPTOGRAPHIC ONE-TIME PAD PIPELINE
    # -------------------------------------------------------------
    print("\n🔒 Step 3: Starting Functional Cryptographic Task...")
    
    # Create the original payload pattern
    secret_payload = torch.zeros((matrix_size, matrix_size), device=device)
    secret_payload[::4, ::4] = 1.0 
    secret_payload[1::4, 1::4] = 0.5
    
    # Convert safely to native uint8 storage space BEFORE calculating checksum metrics
    payload_uint8 = torch.round(secret_payload * 255.0).to(torch.uint8)
    chaos_uint8 = torch.round(diffused_chaos * 255.0).to(torch.uint8)
    
    orig_checksum = torch.sum(payload_uint8.float()).item()
    print(f"   -> Constructing secret payload array (Native Checksum: {orig_checksum:.2f})")

    print("   -> Blurring secret data using Symmetric Bitwise XOR (Encryption)...")
    start_encrypt = time.time()
    
    encrypted_payload = torch.bitwise_xor(payload_uint8, chaos_uint8)
    
    if device.type == "mps": torch.mps.synchronize()
    print(f"   -> Encryption completed in {(time.time() - start_encrypt)*1000:.2f} ms")
    
    entropy_cipher = calculate_shannon_entropy(encrypted_payload)
    print(f"   -> Ciphertext Payload Shannon Entropy: {entropy_cipher:.4f} bits")

    # -------------------------------------------------------------
    # PHASE 4: TRANSMISSION SIMULATION
    # -------------------------------------------------------------
    print("\n📡 Step 4: Simulating raw data stream transmission intercept...")
    interception_sample = encrypted_payload[0:5, 0:5].cpu().numpy() / 255.0
    print("   -> Intercepted Cryptographic Matrix Snippet (First 5x5 Blocks):")
    for row in interception_sample:
        print("      " + " ".join([f"{val:.3f}" for val in row]))

    # -------------------------------------------------------------
    # PHASE 5: DECRYPTION STAGE
    # -------------------------------------------------------------
    print("\n🔓 Step 5: Applying inverse hyper-chaos keys via symmetric bitwise XOR...")
    start_decrypt = time.time()
    
    # Core cryptographic XOR operation
    decrypted_uint8 = torch.bitwise_xor(encrypted_payload, chaos_uint8)
    
    if device.type == "mps": torch.mps.synchronize()
    print(f"   -> Decryption completed in {(time.time() - start_decrypt)*1000:.2f} ms")

    # -------------------------------------------------------------
    # VALIDATION RUN DOWN
    # -------------------------------------------------------------
    dec_checksum = torch.sum(decrypted_uint8.float()).item()
    integrity_error = abs(orig_checksum - dec_checksum)
    is_bit_perfect = torch.equal(payload_uint8, decrypted_uint8)

    print("\n================ FINAL ARCHITECTURE PIPELINE REPORT ================")
    print(f"Initial Checksum Payload Value : {orig_checksum:.2f}")
    print(f"Decrypted Checksum Return Value: {dec_checksum:.2f}")
    print(f"Accumulated Processing Drift   : {integrity_error:.6f}")
    print(f"Bit-Perfect Signal Restored?   : {'YES ✅ (100% Lossless Verification)' if is_bit_perfect else 'NO ❌'}")
    print("=====================================================================")

if __name__ == "__main__":
    run_cryptographic_pipeline(matrix_size=2000)

