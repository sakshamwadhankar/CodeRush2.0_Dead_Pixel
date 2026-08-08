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
        print("WARNING: Docker daemon is not running.")
        print("Sandbox execution will operate in fail-closed mode, but API and Streamlit UI will start.")
    else:
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
        
        # 4. Start Landing Page Server
        print("Starting Landing Page on port 3000...")
        landing_proc = subprocess.Popen(
            [sys.executable, "landing/server.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(landing_proc)
        
        print("\n=======================================================")
        print("🚀 System successfully booted!")
        print(" - Landing Page: http://localhost:3000")
        print(" - FastAPI Sandbox: http://localhost:8000")
        print(" - Streamlit Agent Dashboard: http://localhost:8501")
        print("=======================================================")
        print("Press CTRL+C to shut down all services.")
        
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
