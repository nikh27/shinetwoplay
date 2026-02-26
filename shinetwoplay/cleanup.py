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

def clean_directory(directory_path, empty_files_only=False):
    """Deletes all files and subdirectories inside the given path.
    If empty_files_only is True, files are truncated (emptied) instead of deleted,
    which prevents file-in-use errors (WinError 32) when the server is running."""
    if not directory_path.exists():
        print(f"[*] Directory {directory_path} does not exist. Skipping.")
        return

    print(f"[*] Cleaning directory: {directory_path}...")
    try:
        for item in directory_path.iterdir():
            if item.is_file() or item.is_symlink():
                # Don't delete or empty .gitkeep
                if item.name != '.gitkeep':
                    if empty_files_only:
                        open(item, 'w').close()
                    else:
                        item.unlink()
            elif item.is_dir() and not empty_files_only:
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

    # 3. Clear Logs folder (Empty files instead of deleting to avoid WinError 32)
    clean_directory(LOGS_DIR, empty_files_only=True)
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
