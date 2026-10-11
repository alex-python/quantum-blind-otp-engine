import time
import torch

def run_standard_gpu_benchmark(matrix_size=8000, trials=5):
    print(f"=============================================================")
    print(f" ⚡ STARTING STANDARD GPU MATRIX MATH PERFORMANCE BENCHMARK")
    print(f" Matrix Dimensions : {matrix_size} x {matrix_size}")
    print(f" Total Floating-Ops: {2 * (matrix_size**3):,} Operations (O(N^3))")
    print(f"=============================================================\n")

    # Target Apple Silicon GPU via Metal Performance Shaders (MPS)
    if not torch.backends.mps.is_available():
        print("MPS Backend is not available. Falling back to CPU.")
        device = torch.device("cpu")
    else:
        device = torch.device("mps")
        print(f"Hardware Infrastructure: Apple Silicon M1 {device.type.upper()}")

    # 1. Allocate Matrices directly in GPU Memory Space
    print("\nAllocating matrices in unified memory pool...")
    A = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)
    B = torch.randn(matrix_size, matrix_size, device=device, dtype=torch.float32)
    
    # 2. Hardware Warm-up Pass
    # Compiles Metal compute shaders and initializes physical execution blocks
    print("Executing hardware warm-up pass...")
    _ = torch.mm(A, B)
    if device.type == "mps": torch.mps.synchronize()

    # 3. Execution Trial Loop
    print(f"\nRunning {trials} timed trials of pure matrix multiplication...")
    execution_times = []
    
    for i in range(trials):
        start_time = time.time()
        
        # Execute hardware-accelerated block matrix multiplication
        C = torch.mm(A, B)
        
        # STRICT REQUIREMENT: Enforce hardware synchronization barrier.
        # GPU tasks are asynchronous. We must force Python to wait until the 
        # actual silicon finishing writing the memory before stopping the clock.
        if device.type == "mps": 
            torch.mps.synchronize()
            
        end_time = time.time()
        trial_duration = end_time - start_time
        execution_times.append(trial_duration)
        print(f"   -> Trial {i+1}/{trials}: {trial_duration:.4f} seconds")

    # -------------------------------------------------------------
    # HIGH-PERFORMANCE METRICS ANALYSIS
    # -------------------------------------------------------------
    avg_latency = sum(execution_times) / trials
    
    # Total mathematical ops for Gemm: 2 * N^3
    total_ops = 2 * (matrix_size ** 3)
    tflops_sustained = (total_ops / avg_latency) / 1e12
    
    # Standard GEMM reads 2 input matrices and writes 1 output matrix
    # Float32 = 4 bytes per element
    bytes_moved = (matrix_size * matrix_size * 4) * 3 
    vram_velocity = (bytes_moved / 1e9) / avg_latency

    print("\n================ STANDARD GEMM PERFORMANCE PROFILE ================")
    print(f"• Total Combined Pipeline Latency : {avg_latency:.4f} seconds (Average)")
    print(f"• VRAM Data Velocity Sustained    : {vram_velocity:.2f} GB/sec")
    print(f"• Compute Engine Throughput       : {tflops_sustained:.2f} TFLOPS (Teraflops)")
    print("====================================================================")

if __name__ == "__main__":
    run_standard_gpu_benchmark(matrix_size=8000, trials=5)

