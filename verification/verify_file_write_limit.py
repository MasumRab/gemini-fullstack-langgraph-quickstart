import asyncio
import os
import sys
from pathlib import Path

# Ensure backend/src is in pythonpath
backend_src = Path(__file__).resolve().parent.parent / "backend" / "src"
sys.path.append(str(backend_src))

from agent.mcp_server import FilesystemMCPServer, MAX_FILE_SIZE

async def main():
    print(f"🔒 Checking File Write Limit (Max: {MAX_FILE_SIZE} bytes)...")

    # Setup workspace
    workspace = Path("verification_workspace")
    workspace.mkdir(exist_ok=True)

    server = FilesystemMCPServer([str(workspace)])

    # Create content larger than MAX_FILE_SIZE
    large_content = "A" * (MAX_FILE_SIZE + 100)
    target_file = str(workspace / "large_file.txt")

    print(f"📝 Attempting to write {len(large_content)} bytes to {target_file}...")

    result = await server.write_file(target_file, large_content)

    # Cleanup
    if os.path.exists(target_file):
        os.remove(target_file)
    workspace.rmdir()

    if result.success:
        print("❌ VULNERABILITY DETECTED: Write succeeded despite exceeding size limit!")
        print(f"Bytes written: {result.data.get('bytes_written')}")
        sys.exit(1)
    else:
        if "Content too large" in str(result.error) or "limit" in str(result.error).lower():
            print("✅ SUCCESS: Write blocked as expected.")
            print(f"Error message: {result.error}")
            sys.exit(0)
        else:
            print(f"❓ Write failed but with unexpected error: {result.error}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
