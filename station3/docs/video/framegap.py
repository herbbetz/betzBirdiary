import os
import shutil
import re

# Source and destination directories
src_dir = '.'
dst_dir = './renamed'

# Ensure destination exists
os.makedirs(dst_dir, exist_ok=True)

# Regex for expected filename format
pattern = re.compile(r'^frame(\d{5})\.jpg$')

# Gather and sort files by their number
frames = []
for fname in os.listdir(src_dir):
    match = pattern.match(fname)
    if match:
        frame_number = int(match.group(1)) # in group(0) is 'frame00042.jpg', in group(1) is '00042'
        frames.append((frame_number, fname))

frames.sort()  # Sort by frame number

# Copy and rename files with continuous numbering
for idx, (orig_num, orig_fname) in enumerate(frames, start=1):
    new_fname = f'frame{idx:05d}.jpg'
    src_path = os.path.join(src_dir, orig_fname)
    dst_path = os.path.join(dst_dir, new_fname)
    shutil.copy2(src_path, dst_path)
    print(f"Copied {orig_fname} -> {new_fname}")