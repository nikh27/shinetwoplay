"""
compress_images.py
------------------
Finds all images in shinetwoplay/static/, compresses/resizes them,
and saves them back with the SAME filename (overwrite in place).

Supported formats: PNG, JPG/JPEG, WEBP, GIF (static frames)

Usage:
    python compress_images.py

Optional flags:
    --quality   JPEG/WEBP quality 1-95  (default: 75)
    --max-size  Max width or height px  (default: 1024)
    --dry-run   Show what would happen without touching files
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌  Pillow not installed. Run:  pip install Pillow")
    sys.exit(1)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "shinetwoplay" / "static"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
# ─────────────────────────────────────────────────────────────────────────────


def human_size(n: int) -> str:
    """Convert bytes to a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def compress_image(path: Path, quality: int, max_size: int, dry_run: bool) -> tuple[int, int]:
    """
    Compress a single image file.
    Returns (original_bytes, new_bytes).
    """
    original_size = path.stat().st_size
    ext = path.suffix.lower()

    img = Image.open(path)

    # Convert palette/RGBA to proper mode for JPEG compatibility
    original_mode = img.mode

    # ── Resize if larger than max_size ──────────────────────────────────────
    w, h = img.size
    if w > max_size or h > max_size:
        scale = max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"   ↳ Resized {w}×{h}  →  {new_w}×{new_h}")

    if dry_run:
        return original_size, original_size  # no actual write

    # ── Save with compression ────────────────────────────────────────────────
    save_kwargs = {}

    if ext in (".jpg", ".jpeg"):
        # JPEG doesn't support alpha — convert
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        save_kwargs = {"quality": quality, "optimize": True, "progressive": True}

    elif ext == ".png":
        # PNG is lossless; we can still optimize
        # Convert RGBA→RGB only if there's no actual transparency
        if img.mode == "RGBA":
            # Check if alpha channel is used
            alpha = img.split()[-1]
            if alpha.getextrema() == (255, 255):  # fully opaque
                img = img.convert("RGB")
        save_kwargs = {"optimize": True, "compress_level": 9}

    elif ext == ".webp":
        save_kwargs = {"quality": quality, "method": 6}

    elif ext == ".gif":
        # GIFs: just re-save; keep palette
        save_kwargs = {}

    img.save(path, **save_kwargs)

    new_size = path.stat().st_size
    return original_size, new_size


def main():
    parser = argparse.ArgumentParser(description="Compress static images in place.")
    parser.add_argument("--quality",  type=int, default=75,   help="JPEG/WEBP quality (1-95, default 75)")
    parser.add_argument("--max-size", type=int, default=1024,  help="Max width/height in pixels (default 1024)")
    parser.add_argument("--dry-run",  action="store_true",     help="Preview without saving")
    args = parser.parse_args()

    if not STATIC_DIR.exists():
        print(f"❌  Static folder not found: {STATIC_DIR}")
        sys.exit(1)

    print(f"\n📁  Scanning: {STATIC_DIR}")
    print(f"⚙️   Quality: {args.quality}  |  Max size: {args.max_size}px  |  Dry run: {args.dry_run}\n")

    images = [p for p in STATIC_DIR.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS]

    if not images:
        print("No images found.")
        return

    total_original = 0
    total_new = 0
    skipped = 0
    errors = 0

    for img_path in sorted(images):
        rel = img_path.relative_to(STATIC_DIR)
        print(f"🖼️   {rel}")
        try:
            orig, new = compress_image(img_path, args.quality, args.max_size, args.dry_run)
            total_original += orig
            total_new += new
            saved = orig - new
            pct = (saved / orig * 100) if orig > 0 else 0

            if args.dry_run:
                print(f"   [DRY RUN] {human_size(orig)}")
            elif saved > 0:
                print(f"   ✅  {human_size(orig)}  →  {human_size(new)}  (saved {pct:.1f}%)")
            else:
                print(f"   ➖  {human_size(orig)}  (already optimal)")
                skipped += 1

        except Exception as e:
            print(f"   ❌  Error: {e}")
            errors += 1

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 50)
    print(f"📊  Total images  : {len(images)}")
    if not args.dry_run:
        saved_total = total_original - total_new
        pct_total = (saved_total / total_original * 100) if total_original > 0 else 0
        print(f"📦  Before        : {human_size(total_original)}")
        print(f"📦  After         : {human_size(total_new)}")
        print(f"💾  Total saved   : {human_size(saved_total)}  ({pct_total:.1f}%)")
    if skipped:
        print(f"➖  Already small : {skipped}")
    if errors:
        print(f"❌  Errors        : {errors}")
    print("─" * 50)
    if not args.dry_run:
        print("✅  Done! All images compressed in place.\n")
    else:
        print("ℹ️   Dry run complete — no files were changed.\n")


if __name__ == "__main__":
    main()
