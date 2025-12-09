import subprocess
import sys
import os
import signal
import time

def main():
    """
    Cross-platform dev server launcher.
    Starts both frontend (Vite) and backend (LangGraph) servers.
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    backend_dir = os.path.join(root_dir, "backend")

    print(f"🚀 Starting development servers...")
    
    # Define commands based on OS
    is_windows = sys.platform.startswith('win')
    shell = is_windows  # specialized shell handling for windows

    frontend_cmd = "npm run dev"
    backend_cmd = "langgraph dev"

    processes = []
    
    try:
        # Start Frontend
        print(f"📦 Starting Frontend in {frontend_dir}...")
        frontend_proc = subprocess.Popen(
            frontend_cmd, 
            cwd=frontend_dir, 
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if is_windows else 0
        )
        processes.append(frontend_proc)

        # Start Backend
        print(f"🐍 Starting Backend in {backend_dir}...")
        backend_proc = subprocess.Popen(
            backend_cmd, 
            cwd=backend_dir, 
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if is_windows else 0
        )
        processes.append(backend_proc)

        print("\n✅ Servers started! Press Ctrl+C to stop.")
        
        # Keep main process alive to monitor children
        while True:
            time.sleep(1)
            # Check if any process died
            if frontend_proc.poll() is not None:
                print("❌ Frontend server stopped unexpectedly.")
                break
            if backend_proc.poll() is not None:
                print("❌ Backend server stopped unexpectedly.")
                break

    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        for p in processes:
            if p.poll() is None:
                if is_windows:
                     # Windows kill
                     subprocess.run(f"taskkill /F /T /PID {p.pid}", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                else:
                    p.terminate()
        print("👋 execution stopped.")

if __name__ == "__main__":
    main()
