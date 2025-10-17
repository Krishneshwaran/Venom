import os
import requests

def download_file(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"File downloaded successfully: {save_path}")
    else:
        print(f"Failed to download file from {url}")

# Create 'models' directory if it doesn't exist
os.makedirs('models', exist_ok=True)

# URLs of the files to download
urls = [
    "https://huggingface.co/Ultralytics/YOLOv8/resolve/main/yolov8n.pt",
    "https://huggingface.co/Ultralytics/YOLOv8/resolve/8a9e1a55f987a77f9966c2ac3f80aa8aa37b3c1a/yolov8m.pt"
]

# Save paths for the downloaded files inside the 'models' directory
save_paths = [
    os.path.join('models', 'yolov8n.pt'),
    os.path.join('models', 'yolov8m.pt')
]

# Download each file
for url, save_path in zip(urls, save_paths):
    download_file(url, save_path)
