#!/bin/bash

# Script to resize all .jpg and .png images in place (backup!) in the current directory
# that are larger than 500KB, down to under 500KB while keeping aspect ratio.
# Requires ffmpeg.

for img in *.jpg *.png; do
  [ -e "$img" ] || continue  # Skip if no such files
  size_kb=$(du -k "$img" | cut -f1)
  # if [ "$size_kb" -gt 1000 ]; then # pictures 500-1000 will remain over 500
  if [ "$size_kb" -gt 500 ]; then
    # Create a temp output file name
    out="resized_$img"
    # Try reducing quality and size iteratively
    # Set initial quality and scale factor
    quality=90
    scale=1.0
    while true; do
      # Calculate scaled width (keep aspect ratio)
      width=$(ffprobe -v error -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$img")
      new_width=$(awk "BEGIN{printf \"%d\", $width*$scale}")
      # Use ffmpeg to resize and reduce quality
      ffmpeg -y -i "$img" -vf "scale=$new_width:-1" -qscale:v $((100-quality)) "$out" -loglevel error
      out_size_kb=$(du -k "$out" | cut -f1)
      if [ "$out_size_kb" -le 500 ]; then
      # if [ "$out_size_kb" -le 500 ] || [ "$quality" -le 50 ]; then # only reduce till quality too low
        mv "$out" "$img"
        echo "Resized $img to ${out_size_kb}KB"
        break
      else
        quality=$((quality-10))
        scale=$(awk "BEGIN{print $scale*0.95}")
      fi
    done
  fi
done