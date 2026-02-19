#!/usr/bin/env python3
'''
Analyzer for pth pytorch models
pip install torch torchvision
'''
import sys
import torch
import torchvision.models as models
from collections import Counter
import torch.nn as nn

# This tells PyTorch 2.6+ that these specific classes are safe to load
import torchvision
torch.serialization.add_safe_globals([
    torchvision.models.mobilenetv3.MobileNetV3,
    torchvision.models.mobilenetv3.InvertedResidual,
    torchvision.ops.misc.Conv2dNormActivation,
    torchvision.ops.misc.SqueezeExcitation,
    torchvision.models.mobilenet.MobileNetV3 # Some versions use this path
])

def get_layer_type(module: nn.Module) -> str:
    if isinstance(module, nn.Conv2d):
        if module.groups == module.in_channels and module.in_channels == module.out_channels:
            return "DepthwiseConv"
        return "Conv2D"
    if isinstance(module, nn.Linear):
        return "Linear/Dense"
    if isinstance(module, (nn.MaxPool2d, nn.AvgPool2d, nn.AdaptiveAvgPool2d)):
        return "Pooling"
    if isinstance(module, (nn.ReLU, nn.ReLU6, nn.Hardswish, nn.Sigmoid)):
        return "Activation"
    if isinstance(module, nn.BatchNorm2d):
        return "BatchNorm"
    return "Other"

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_pth.py <model.pth>")
        sys.exit(1)

    model_path = sys.argv[1]
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    try:
        # Since your error proved the file IS the model, we load it directly
        # weights_only=False is required because the file contains the Class structure
        model = torch.load(model_path, map_location=device, weights_only=False)
        model.eval()
        print(f"\nSuccessfully loaded entire model object from {model_path}\n")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # -------- Summary Counter --------
    counter = Counter()
    for module in model.modules():
        if len(list(module.children())) == 0:
            layer_type = get_layer_type(module)
            counter[layer_type] += 1

    print("=== Layer Summary ===\n")
    print(f"{'Layer Type':<20}Count")
    print("-" * 30)
    for layer, count in sorted(counter.items()):
        print(f"{layer:<20}{count}")

    # -------- Output Classes --------
    # Look for the last Linear layer in the classifier
    num_classes = "Unknown"
    if hasattr(model, 'classifier'):
        for m in reversed(model.classifier):
            if isinstance(m, nn.Linear):
                num_classes = m.out_features
                break
    
    print(f"\nDetected Output Classes: {num_classes}")

    # -------- Parameter Info --------
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total Parameters: {total_params:,}")

if __name__ == "__main__":
    main()