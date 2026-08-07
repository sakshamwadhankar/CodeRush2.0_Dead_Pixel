import subprocess
import sys
import time
import os

def check_docker():
    try:
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    print("Initializing Aegis Research OS...")
    
    # 1. Check Docker
    if not check_docker():
        print("CRITICAL ERROR: Docker daemon is not running.")
        print("Please start Docker Desktop or the Docker daemon and try again.")
        sys.exit(1)
    
    print("Docker is running.")
    
    processes = []
    
    try:
        # 2. Start FastAPI Sandbox/Scrape API
        print("Starting FastAPI Sandbox Microservice on port 8000...")
        fastapi_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.security.api:app", "--port", "8000"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(fastapi_proc)
        
        # Give API a second to boot
        time.sleep(2)
        
        # 3. Start Streamlit UI
        print("Starting Streamlit Dashboard on port 8501...")
        streamlit_proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "src/ui/app.py", "--server.port", "8501"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(streamlit_proc)
        
        print("System successfully booted. Press CTRL+C to shut down.")
        
        # Keep alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down Aegis Research OS...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
