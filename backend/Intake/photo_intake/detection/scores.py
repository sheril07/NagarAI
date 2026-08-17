import open_clip
import torch
from PIL import Image


# Load CLIP
model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32",
    pretrained="openai"
)

tokenizer = open_clip.get_tokenizer("ViT-B-32")


# Your test image
image_path = "photo_intake/input/sample_images/test_image.jpg"

image = Image.open(image_path).convert("RGB")
image = preprocess(image).unsqueeze(0)


# Issues we want to compare
issues = [
    "a photograph of a pothole in a road",
    "a photograph of cracks in a road",
    "a photograph of a damaged road",
    "a photograph of a damaged footpath",
    "a photograph of a broken sidewalk"
]

tokens = tokenizer(issues)


# Calculate embeddings
with torch.no_grad():

    image_features = model.encode_image(image)
    text_features = model.encode_text(tokens)

    image_features /= image_features.norm(
        dim=-1,
        keepdim=True
    )

    text_features /= text_features.norm(
        dim=-1,
        keepdim=True
    )

    scores = image_features @ text_features.T


print("\nCLIP ISSUE SCORES")
print("=================")

for issue, score in zip(issues, scores[0]):

    print(
        f"{issue} → {score.item():.4f}"
    )