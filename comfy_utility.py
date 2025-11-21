# comfy_utility.py
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
COMFY_URL = os.getenv("COMFY_URL").rstrip("/")

print("ComfyUI URL:", COMFY_URL)


# ------------------------------
# JSON Workflow Management
# ------------------------------
def load_workflow(json_path: str = "new_flow_deploy.json"):
    """Load workflow JSON file."""
    with open(json_path, "r") as f:
        return json.load(f)
    
# #  update workflow with prompt and image
def update_workflow(workflow: dict, prompt: str, image_path: str= None, prompt_node_index: int=35):
    workflow[str(prompt_node_index)]["inputs"]["text"] = prompt
    return workflow

def send_prompt(workflow_json, prompt_id):
    """Send workflow JSON to ComfyUI"""
    res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow_json, "client_id": prompt_id})

    if res.status_code != 200:
        return None
    return res.json()

def get_history(prompt_id):
    """Get finished job history"""
    url =f"{COMFY_URL}/history/{prompt_id}"

    print('hstory url', url )
    res = requests.get(url )

    print("res--->>",res)
    if res.status_code != 200:
        return None
    return res.json()


# single image to downlaod
def download_image(filename, img_type):
    """Download image file from ComfyUI output"""
    url = f"{COMFY_URL}/view?filename={filename}&type={img_type}"
    local_path = f"./outputs/{filename}"

    os.makedirs("outputs", exist_ok=True)

    res = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(res.content)

    return local_path


#  list of the images in the node
def download_images_list(image_list):
    downloaded_files = []
    for img in image_list:
        filename = img["filename"]
        img_type = img["type"]
        print("Downloading filename:", filename)
        print("Image type:", img_type)

        #  function to download image
        local_path = download_image(filename, img_type)
        downloaded_files.append(local_path)
    return downloaded_files

def get_node_images(history_data, node_id: str):
        return (
            history_data.get(node_id, {})
                       .get("images", {})
        )