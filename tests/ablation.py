# tests/ablation.py
import os
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

CONFIGURATIONS = [
    {"chunk_size": 256, "top_k": 5},
    {"chunk_size": 512, "top_k": 5},
    {"chunk_size": 256, "top_k": 10},
    {"chunk_size": 512, "top_k": 10},
]

def run_config(config):
    print(f"Testing config: {config}")
    
    # Update .env
    with open(".env", "r") as f:
        env_lines = f.readlines()
    
    with open(".env", "w") as f:
        for line in env_lines:
            if line.startswith("CHUNK_SIZE="):
                f.write(f"CHUNK_SIZE={config['chunk_size']}\n")
            elif line.startswith("TOP_K="):
                f.write(f"TOP_K={config['top_k']}\n")
            else:
                f.write(line)
    
    # Re-index
    subprocess.run(["python", "-m", "scripts.run_ingestion"], capture_output=True)
    
    # Run evaluation
    result = subprocess.run(["python", "tests/evaluate_full.py"], capture_output=True)
    
    return {"config": config, "result": result.stdout}

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(run_config, config) for config in CONFIGURATIONS]
        for future in futures:
            print(future.result())