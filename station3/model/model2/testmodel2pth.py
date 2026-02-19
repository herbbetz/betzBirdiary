'''
Analyse image using pytorch model:
Usage: python testmodel2pth.py --model .\model2\birdiary_v5_mobilenetv3_fine_tuning.pth --image .\test\2.jpg --labels .\model2\labels.txt
'''
#!/usr/bin/env python3
import argparse
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import sys
import torchvision

# PyTorch 2.6+ Security Bypass
torch.serialization.add_safe_globals([
    torchvision.models.mobilenetv3.MobileNetV3,
    torchvision.models.mobilenetv3.InvertedResidual,
    torchvision.ops.misc.Conv2dNormActivation,
    torchvision.ops.misc.SqueezeExcitation,
])

def load_labels(labels_file):
    with open(labels_file, "r") as f:
        return [line.strip() for line in f.readlines()]

def main():
    parser = argparse.ArgumentParser(description="Classify a bird image using a PyTorch MobileNetV3 model.")
    parser.add_argument("-m", "--model", required=True, help="Path to the .pth model file")
    parser.add_argument("-i", "--image", required=True, help="Path to the input image file")
    parser.add_argument("-l", "--labels", required=True, help="Path to the labels.txt file")
    args = parser.parse_args()

    # 1. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2. Load the Model
    try:
        # Loading the entire model object as discovered in your previous step
        model = torch.load(args.model, map_location=device, weights_only=False)
        model.eval()
        print(f"Model loaded: {args.model}")
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    # 3. Load Labels
    try:
        labels = load_labels(args.labels)
        print(f"Loaded {len(labels)} labels.")
    except Exception as e:
        print(f"Error loading labels: {e}")
        sys.exit(1)

    # 4. Prepare Preprocessing
    # MobileNetV3 expects 224x224 images normalized with ImageNet stats
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # 5. Load and Process Image
    try:
        input_image = Image.open(args.image).convert("RGB")
        input_tensor = preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0).to(device) # Create a mini-batch of 1
    except Exception as e:
        print(f"Error processing image: {e}")
        sys.exit(1)

    # 6. Run Inference
    with torch.no_grad():
        output = model(input_batch)
        
    # 7. Get Predictions
    probabilities = F.softmax(output[0], dim=0)
    conf, class_id = torch.max(probabilities, 0)

    # 8. Display Results
    print("\n" + "="*30)
    print(f"PREDICTION: {labels[class_id.item()]}")
    print(f"CONFIDENCE: {conf.item() * 100:.2f}%")
    print("="*30)

if __name__ == "__main__":
    main()