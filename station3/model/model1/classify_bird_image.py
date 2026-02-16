#!/usr/bin/env python3
"""
=============================================================================
  LogChirpy Bird Image Classifier — Full Diagnostic Script
=============================================================================

  Classifies a bird photo using the LogChirpy MobileNetV2 image model
  (bird_classifier_metadata.tflite — 400 species).

  Created in response to Issue #1:
  https://github.com/mklemmingen/LogChirpy/issues/1

  IMPORTANT CONTEXT:
  ------------------
  LogChirpy ships TWO completely independent ML models:

    1) IMAGE model (this script uses it):
       - File: bird_classifier_metadata.tflite (17 MB, MobileNetV2)
       - Input: 224x224 RGB photo, normalized to [-1, 1]
       - Output: 400 bird species (English common names)
       - Labels: assets/models/birds_mobilenetv2/labels.txt

    2) AUDIO model (NOT used by this script):
       - File: BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite (50 MB)
       - Input: 3 seconds of raw audio at 48 kHz
       - Output: 6,522 bird species (scientific + common names)
       - Labels: assets/model_labels_whoBird/labels_de.txt (and 37 languages)

  The labels_de.txt (6,522 entries) belongs ONLY to the audio model.
  Do NOT use it with the image model (400 classes). That mismatch was
  the root cause of the confusion described in Issue #1.

  Requirements:
      pip install tflite-runtime Pillow numpy
      (Python 3.9, 3.10, or 3.11 — tflite-runtime does not support 3.12+)

  Usage:
      python3 classify_bird_image.py photo.jpg
      python3 classify_bird_image.py photo.jpg --top 10 --verbose
      python3 classify_bird_image.py photo.jpg --model path/to/model.tflite --labels path/to/labels.txt

=============================================================================
"""

import argparse
import os
import sys
import time
import json
import zipfile
import re

# ---------------------------------------------------------------------------
#  Dependency checks
# ---------------------------------------------------------------------------

def check_dependencies():
    """Check that required packages are installed and print helpful errors."""
    missing = []

    try:
        import numpy as np
    except ImportError:
        missing.append("numpy")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        missing.append("tflite-runtime")

    if missing:
        print("=" * 70)
        print("  MISSING DEPENDENCIES")
        print("=" * 70)
        print()
        print(f"  The following Python packages are required but not installed:")
        print(f"    {', '.join(missing)}")
        print()
        print(f"  Install them with:")
        print(f"    pip install {' '.join(missing)}")
        print()
        print(f"  NOTE: tflite-runtime requires Python 3.9, 3.10, or 3.11.")
        print(f"  It does NOT work on Python 3.12 or 3.13.")
        print(f"  Your Python version: {sys.version.split()[0]}")
        print()
        v = sys.version_info
        if v.major == 3 and v.minor >= 12:
            print(f"  *** You are running Python {v.major}.{v.minor} which is NOT supported. ***")
            print(f"  Please use Python 3.11 or earlier.")
            print(f"  On Windows with WSL: sudo apt install python3.11 python3.11-venv")
            print()
        print("=" * 70)
        sys.exit(1)

    return np, Image, tflite


# ---------------------------------------------------------------------------
#  Label loading
# ---------------------------------------------------------------------------

def load_labels_from_file(path):
    """Load labels from a plain text file (one label per line)."""
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_labels_from_tflite(model_path):
    """Extract embedded labels from a TFLite file with metadata (ZIP overlay)."""
    try:
        with zipfile.ZipFile(model_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".txt"):
                    content = z.read(name).decode("utf-8")
                    labels = [line.strip() for line in content.split("\n") if line.strip()]
                    # Strip numeric prefixes if present (legacy bug)
                    cleaned = []
                    for label in labels:
                        match = re.match(r"^\d+\s+(.+)$", label)
                        cleaned.append(match.group(1) if match else label)
                    return cleaned
    except zipfile.BadZipFile:
        pass
    return []


def load_labels(labels_path, model_path):
    """Load labels, preferring standalone file, falling back to model metadata."""
    if labels_path and os.path.exists(labels_path):
        labels = load_labels_from_file(labels_path)
        source = f"standalone file: {os.path.basename(labels_path)}"
    else:
        labels = load_labels_from_tflite(model_path)
        source = "embedded in .tflite metadata"
        if not labels:
            source = "NONE FOUND"

    return labels, source


# ---------------------------------------------------------------------------
#  Image preprocessing
# ---------------------------------------------------------------------------

def preprocess_image(np, Image, image_path, input_size=224, verbose=False):
    """
    Load and preprocess an image for MobileNetV2 inference.

    MobileNetV2 expects:
      - RGB image resized to 224 x 224
      - Float32 values normalized to [-1, 1]
      - Normalization formula: (pixel - 127.5) / 127.5
    """
    img = Image.open(image_path)
    original_size = img.size  # (width, height)
    original_mode = img.mode

    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize to model input size
    img_resized = img.resize((input_size, input_size), Image.LANCZOS)

    # Convert to numpy array and normalize
    img_array = np.array(img_resized, dtype=np.float32)

    # MobileNetV2 normalization: maps [0, 255] -> [-1.0, +1.0]
    img_normalized = (img_array - 127.5) / 127.5

    # Add batch dimension: (224, 224, 3) -> (1, 224, 224, 3)
    input_tensor = np.expand_dims(img_normalized, axis=0)

    diagnostics = {
        "original_size": f"{original_size[0]} x {original_size[1]}",
        "original_mode": original_mode,
        "resized_to": f"{input_size} x {input_size}",
        "pixel_range_before": f"[{img_array.min():.1f}, {img_array.max():.1f}]",
        "pixel_range_after": f"[{img_normalized.min():.4f}, {img_normalized.max():.4f}]",
        "tensor_shape": str(input_tensor.shape),
        "tensor_dtype": str(input_tensor.dtype),
    }

    return input_tensor, diagnostics


# ---------------------------------------------------------------------------
#  Model inspection
# ---------------------------------------------------------------------------

def inspect_model(tflite, model_path):
    """Load the TFLite model and return interpreter + metadata."""
    # For metadata-enriched models, tflite_runtime can load them directly
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    inp = input_details[0]
    out = output_details[0]

    model_info = {
        "file": os.path.basename(model_path),
        "file_size_mb": f"{os.path.getsize(model_path) / (1024*1024):.1f}",
        "input_name": inp["name"],
        "input_shape": str(inp["shape"].tolist()),
        "input_dtype": str(inp["dtype"]),
        "output_name": out["name"],
        "output_shape": str(out["shape"].tolist()),
        "output_dtype": str(out["dtype"]),
        "num_classes": int(out["shape"][-1]),
    }

    return interpreter, input_details, output_details, model_info


# ---------------------------------------------------------------------------
#  Inference
# ---------------------------------------------------------------------------

def run_inference(interpreter, input_details, output_details, input_tensor):
    """Run the model and return raw output probabilities."""
    interpreter.set_tensor(input_details[0]["index"], input_tensor)
    start = time.perf_counter()
    interpreter.invoke()
    elapsed = time.perf_counter() - start
    output_data = interpreter.get_tensor(output_details[0]["index"])[0]
    return output_data, elapsed


# ---------------------------------------------------------------------------
#  Output formatting
# ---------------------------------------------------------------------------

def format_results(output_data, labels, top_k, np):
    """Format classification results into a structured list."""
    num_classes = len(output_data)
    top_indices = np.argsort(output_data)[::-1][:top_k]

    results = []
    for rank, idx in enumerate(top_indices, 1):
        label = labels[idx] if idx < len(labels) else f"[Unknown class {idx}]"
        confidence = float(output_data[idx])
        results.append({
            "rank": rank,
            "index": int(idx),
            "label": label,
            "confidence": confidence,
            "confidence_pct": f"{confidence * 100:.2f}%",
        })

    return results


def print_header(title):
    """Print a section header."""
    width = 70
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_kv(key, value, indent=2):
    """Print a key-value pair."""
    print(f"{' ' * indent}{key:<30s} {value}")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    # Resolve paths relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))

    default_model = os.path.join(
        repo_root, "assets", "models", "birds_mobilenetv2",
        "bird_classifier_metadata.tflite"
    )
    default_labels = os.path.join(
        repo_root, "assets", "models", "birds_mobilenetv2", "labels.txt"
    )

    parser = argparse.ArgumentParser(
        description="LogChirpy Bird Image Classifier — Full Diagnostic Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 classify_bird_image.py sparrow.jpg
  python3 classify_bird_image.py sparrow.jpg --top 10
  python3 classify_bird_image.py sparrow.jpg --verbose
  python3 classify_bird_image.py sparrow.jpg --json

Note: Requires Python 3.9-3.11 and tflite-runtime.
        """,
    )
    parser.add_argument("image", help="Path to bird image (JPG, PNG, BMP, etc.)")
    parser.add_argument("--model", "-m", default=default_model,
                        help="Path to .tflite model file")
    parser.add_argument("--labels", "-l", default=default_labels,
                        help="Path to labels.txt file")
    parser.add_argument("--top", "-k", type=int, default=10,
                        help="Number of top predictions to display (default: 10)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show additional technical diagnostics")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output results as JSON (for programmatic use)")
    parser.add_argument("--search", "-s", type=str, default=None,
                        help="Search for a specific species in all 400 results (e.g. 'sparrow')")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    #  Dependency check
    # ------------------------------------------------------------------
    np, Image, tflite = check_dependencies()

    # ------------------------------------------------------------------
    #  Validate inputs
    # ------------------------------------------------------------------
    if not os.path.exists(args.image):
        print(f"ERROR: Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.model):
        print(f"ERROR: Model file not found: {args.model}", file=sys.stderr)
        print(f"Expected at: {args.model}", file=sys.stderr)
        print(f"Make sure you are running this from the Issue/ folder or specify --model", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    #  Load model
    # ------------------------------------------------------------------
    if not args.json:
        print_header("MODEL INFORMATION")

    interpreter, input_details, output_details, model_info = inspect_model(tflite, args.model)

    if not args.json:
        print_kv("Model file:", model_info["file"])
        print_kv("File size:", f"{model_info['file_size_mb']} MB")
        print_kv("Architecture:", "MobileNetV2 (image classifier)")
        print_kv("Input tensor:", f"{model_info['input_shape']} {model_info['input_dtype']}")
        print_kv("Input description:", "224x224 RGB image, Float32")
        print_kv("Normalization:", "(pixel - 127.5) / 127.5 => [-1, +1]")
        print_kv("Output tensor:", f"{model_info['output_shape']} {model_info['output_dtype']}")
        print_kv("Number of classes:", str(model_info["num_classes"]))

    # ------------------------------------------------------------------
    #  Load labels
    # ------------------------------------------------------------------
    labels, label_source = load_labels(args.labels, args.model)

    if not args.json:
        print()
        print_kv("Labels loaded:", str(len(labels)))
        print_kv("Label source:", label_source)

        if len(labels) != model_info["num_classes"]:
            print()
            print(f"  *** WARNING: Label count ({len(labels)}) does not match")
            print(f"      model output classes ({model_info['num_classes']})!")
            print(f"      Make sure you are using the correct labels file.")
            print(f"      The image model uses labels.txt (400 entries),")
            print(f"      NOT labels_de.txt (6,522 entries for the audio model).")

    # ------------------------------------------------------------------
    #  Preprocess image
    # ------------------------------------------------------------------
    if not args.json:
        print_header("IMAGE PREPROCESSING")

    input_tensor, diagnostics = preprocess_image(np, Image, args.image, verbose=args.verbose)

    if not args.json:
        print_kv("Input image:", os.path.basename(args.image))
        print_kv("Original size:", diagnostics["original_size"])
        print_kv("Original mode:", diagnostics["original_mode"])
        print_kv("Resized to:", diagnostics["resized_to"])
        print_kv("Pixel range (raw):", diagnostics["pixel_range_before"])
        print_kv("Pixel range (normalized):", diagnostics["pixel_range_after"])
        print_kv("Tensor shape:", diagnostics["tensor_shape"])
        print_kv("Tensor dtype:", diagnostics["tensor_dtype"])

    # ------------------------------------------------------------------
    #  Run inference
    # ------------------------------------------------------------------
    output_data, elapsed_s = run_inference(interpreter, input_details, output_details, input_tensor)

    if not args.json:
        print_header("INFERENCE RESULTS")
        print_kv("Inference time:", f"{elapsed_s * 1000:.1f} ms")
        print_kv("Output range:", f"[{output_data.min():.4f}, {output_data.max():.4f}]")
        print_kv("Output sum:", f"{output_data.sum():.4f} (should be ~1.0 for softmax)")
        print()

    # ------------------------------------------------------------------
    #  Top-K results
    # ------------------------------------------------------------------
    results = format_results(output_data, labels, args.top, np)

    if args.json:
        json_output = {
            "model": model_info,
            "image": {
                "path": args.image,
                "diagnostics": diagnostics,
            },
            "inference_time_ms": round(elapsed_s * 1000, 1),
            "labels": {
                "count": len(labels),
                "source": label_source,
            },
            "predictions": results,
        }
        if args.search:
            search_lower = args.search.lower()
            matches = []
            for i, label in enumerate(labels):
                if search_lower in label.lower():
                    matches.append({
                        "index": i,
                        "label": label,
                        "confidence": float(output_data[i]),
                        "confidence_pct": f"{float(output_data[i]) * 100:.2f}%",
                    })
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            json_output["search"] = {
                "query": args.search,
                "matches": matches,
            }
        print(json.dumps(json_output, indent=2, ensure_ascii=False))
        return

    # Print table
    header = f"  {'Rank':<6}{'Species':<40}{'Confidence':<14}{'Index'}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for r in results:
        conf_bar = "#" * int(r["confidence"] * 30)
        print(f"  {r['rank']:<6}{r['label']:<40}{r['confidence_pct']:<14}[{r['index']}]")
        if args.verbose:
            print(f"        {conf_bar}")

    # ------------------------------------------------------------------
    #  Species search
    # ------------------------------------------------------------------
    if args.search:
        search_lower = args.search.lower()
        matches = []
        for i, label in enumerate(labels):
            if search_lower in label.lower():
                matches.append((i, label, float(output_data[i])))

        print_header(f"SEARCH RESULTS FOR '{args.search}'")
        if matches:
            matches.sort(key=lambda x: x[2], reverse=True)
            for idx, label, conf in matches:
                print(f"  Index {idx:<5} {label:<40} {conf*100:.2f}%")
        else:
            print(f"  No species matching '{args.search}' found in the 400-class label set.")
            print(f"  This model only covers 400 species with English common names.")

    # ------------------------------------------------------------------
    #  Summary & tips
    # ------------------------------------------------------------------
    top1 = results[0]
    print_header("SUMMARY")
    print(f"  Top prediction: {top1['label']} ({top1['confidence_pct']})")
    print()

    if top1["confidence"] < 0.3:
        print("  NOTE: Low confidence. Possible reasons:")
        print("    - The bird species may not be in the 400-class model")
        print("    - The photo may be low quality, too far away, or occluded")
        print("    - The photo may contain multiple birds or non-bird subjects")
        print()

    if args.verbose:
        print_header("TECHNICAL NOTES")
        print("  Model architecture details:")
        print(f"    - Input tensor name:  {model_info['input_name']}")
        print(f"    - Output tensor name: {model_info['output_name']}")
        print(f"    - Input normalization: mean=127.5, std=127.5")
        print(f"    - Output activation: softmax (probabilities sum to ~1.0)")
        print()
        print("  LogChirpy model ecosystem:")
        print("    - This IMAGE model:  400 species, MobileNetV2, 17 MB")
        print("    - BirdNET AUDIO model: 6,522 species, EfficientNet, 50 MB")
        print("    - labels_de.txt (6,522 lines) belongs to the AUDIO model only")
        print("    - labels.txt (400 lines) belongs to THIS image model")
        print()
        print("  Python compatibility:")
        print(f"    - Your Python: {sys.version}")
        print(f"    - tflite-runtime supports: Python 3.9, 3.10, 3.11")
        print(f"    - tflite_support.metadata requires: Python <= 3.11")


if __name__ == "__main__":
    main()
