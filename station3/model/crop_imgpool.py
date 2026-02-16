#!/usr/bin/env python3
"""
Reads <prefix>.csv (produced by birdclassify0.py and birdclassify1.py),
and deletes all images in /home/pi/station3/ramdisk that are not meant to be kept.

Rules:
1. Keep images listed in the second field of each CSV line, unless that field is "None".
2. If all CSV entries have "None" in the second field, keep prefix.0.jpg and prefix.2.jpg if they exist.
"""

import sys
import os
import glob

IMG_DIR = "/home/pi/station3/ramdisk"

def main():
    if len(sys.argv) < 2:
        print("Usage: python crop_imgpool.py <filename_prefix>")
        sys.exit(1)

    prefix = sys.argv[1]
    if "/" in prefix:
        print(f"Prefix must not contain '/': {prefix}")
        sys.exit(1)

    csv_path = os.path.join(IMG_DIR, f"{prefix}.csv")
    if not os.path.exists(csv_path):
        print(f"No CSV found for prefix: {prefix}")
        sys.exit(1)

    # --- parse CSV ---
    keep_indices = set()
    all_none = True
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            idx_str = parts[1].strip()
            if idx_str.lower() != "none":
                all_none = False
                keep_indices.add(idx_str)

    # --- determine keep paths ---
    if all_none:
        # fallback: keep prefix.0.jpg and prefix.2.jpg if present
        fallback_files = [f"{prefix}.0.jpg", f"{prefix}.2.jpg"]
        keep_paths = {os.path.join(IMG_DIR, fname) for fname in fallback_files if os.path.exists(os.path.join(IMG_DIR, fname))}
    else:
        keep_paths = {os.path.join(IMG_DIR, f"{prefix}.{idx}.jpg") for idx in keep_indices if os.path.exists(os.path.join(IMG_DIR, f"{prefix}.{idx}.jpg"))}

    # --- delete all others ---
    all_images = glob.glob(os.path.join(IMG_DIR, f"{prefix}.*.jpg"))
    for img_path in all_images:
        if img_path not in keep_paths:
            try:
                os.remove(img_path)
                # optional: print(f"Deleted {img_path}")
            except Exception as e:
                print(f"Failed to delete {img_path}: {e}")

if __name__ == "__main__":
    main()
