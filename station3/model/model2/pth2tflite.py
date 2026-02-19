'''
Convert .pth model to .tflite float, as this should not entail quality loss
usage: python3 pht2tflite.py (WSL Debian 12 with python 3.11 in (herbvenv)), all paths hardcoded
pip install torch==2.5.1 torchvision==0.20.1 litert-torch torchao==0.12.0 # all older versions
'''
import torch
import litert_torch

# 1. Load your existing model object
device = torch.device("cpu")
model = torch.load("birdiary_v5_mobilenetv3_fine_tuning.pth", map_location=device, weights_only=False)
model.eval()

# 2. Create dummy input (Matches your 224x224 preprocessing)
sample_input = (torch.randn(1, 3, 224, 224),)

# 3. Convert to LiteRT (TFLite) format
# This uses Float32 by default = No quality loss
edge_model = litert_torch.convert(model, sample_input)

# 4. Save the file
edge_model.export("birdiary_v5_mobilenetv3.tflite")
print("Successfully converted to TFLite!")