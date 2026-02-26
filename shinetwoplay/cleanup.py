import os
import shutil
import redis
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / 'media'
LOGS_DIR = BASE_DIR / 'logs'

def clean_redis():
    """Flushes all data from the local Redis instance."""
    print("[*] Connecting to Redis...")
    try:
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        # Verify connection
        r.ping()
        print("[*] Flushing all Redis data...")
        r.flushall()
        print("[+] Redis cleared successfully.")
    except Exception as e:
        print(f"[-] Failed to clear Redis: {e}")

def clean_directory(directory_path, keep_dir=True):
    """Deletes all files and subdirectories inside the given path."""
    if not directory_path.exists():
        print(f"[*] Directory {directory_path} does not exist. Skipping.")
        return

    print(f"[*] Cleaning directory: {directory_path}...")
    try:
        for item in directory_path.iterdir():
            if item.is_file() or item.is_symlink():
                # Don't delete .gitkeep if it exists
                if item.name != '.gitkeep':
                    item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f"[+] Directory {directory_path} cleared successfully.")
    except Exception as e:
        print(f"[-] Failed to clean {directory_path}: {e}")

def main():
    print("========================================")
    print("    ShineTwoPlay Server Cleanup Tool    ")
    print("========================================\n")
    
    # 1. Clear Redis
    clean_redis()
    print("")

    # 2. Clear Media folder (User uploads like voice/images)
    clean_directory(MEDIA_DIR)
    print("")

    # 3. Clear Logs folder
    clean_directory(LOGS_DIR)
    print("")

    print("========================================")
    print("    Cleanup Complete! Server is fresh.  ")
    print("========================================")

if __name__ == "__main__":
    confirm = input("Are you sure you want to WIPE all Redis data, Media, and Logs? (y/N): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("Cleanup aborted.")
