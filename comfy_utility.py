# comfy_utility.py
import json
import os
import requests
from dotenv import load_dotenv
import random

load_dotenv()



# ------------------------------
# JSON Workflow Management
# ------------------------------
def load_workflow(json_path: str = "new_flow_deploy.json"):
    """Load workflow JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
# #  update workflow with prompt and image
def update_workflow(workflow: dict, prompt: str, image_path: str= None, prompt_node_index: int=35, image_node_index: int=None, I2V=False, seed_node_index= None):
    """Update workflow JSON with prompt and optional image."""
    print("Updating workflow with prompt:", prompt_node_index)
    print("Workflow keys:", workflow[str(prompt_node_index)]["inputs"])
    if I2V:
        # for I2V
        workflow[str(prompt_node_index)]["inputs"]["value"] = prompt

    else:
        # for  t2v or t2i
        workflow[str(prompt_node_index)]["inputs"]["text"] = prompt

    if image_path:
         
         workflow[str(image_node_index)]["inputs"]["image"] = image_path
         print("Updating workflow with image:", image_node_index)

    print('seed_node_index-->>',seed_node_index)    
    if seed_node_index is not None:
        seed_value = generate_large_seed()
        print("previous seed value:", workflow[str(seed_node_index)]["inputs"]["seed"])
        workflow[str(seed_node_index)]["inputs"]["seed"] = seed_value
         

    return workflow

def send_prompt(workflow_json, COMFY_URL):
    """Send workflow JSON to ComfyUI"""
    res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow_json})

    if res.status_code != 200:
        return None
    return res.json()

def get_history(prompt_id, COMFY_URL):
    """Get finished job history"""
    url =f"{COMFY_URL}/history/{prompt_id}"

    print('hstory url', url )
    res = requests.get(url )

    print("res--->>",res)
    if res.status_code != 200:
        return None
    return res.json()


# single image to downlaod
def download_image_video(filename, img_type, COMFY_URL, subfolder=None, format=None, frame_rate=None):
    """Download image file from ComfyUI output"""
    url = f"{COMFY_URL}/view?filename={filename}&type={img_type}"
    local_path = f"outputs/{filename}"

    if subfolder:
        url += f"&subfolder={subfolder}"
    if format:
        url += f"&format={format}"
    if frame_rate:
        url += f"&frame_rate={frame_rate}"
    
    print("Download URL:", url)


    os.makedirs("outputs", exist_ok=True)

    res = requests.get(url)
    with open(local_path, "wb") as f:
        f.write(res.content)

    return local_path


#  list of the images in the node
def download_images_list(image_list, COMFY_URL):
    downloaded_files = []
    for img in image_list:
        filename = img["filename"]
        img_type = img["type"]
        subfolder = img.get("subfolder") 
        format = img.get("format")
        frame_rate = img.get("frame_rate")

        print("Downloading filename:", filename)
        print("Image type:", img_type)

        #  function to download image
        local_path = download_image_video(filename, img_type,COMFY_URL, subfolder, format, frame_rate)
        downloaded_files.append(local_path)
    return downloaded_files

def get_node_images(history_data, node_id: str):
        return (
            history_data.get(node_id, {})
                       .get("images", {})
        )

#  get node videos
def get_node_videos(history_data, node_id: str):
        return (
            history_data.get(node_id, {})
                       .get("gifs", {})
        )

# upload image to the comfy
def upload_image_to_comfy(image_path: str):
    """Upload image to ComfyUI server."""
    url = f"{COMFY_URL}/upload/image"

    print("Uploading image to URL:", url)
    print("Image path:", image_path)

    filename = os.path.basename(image_path)
    print("\n\nFilename:", filename)
    with open(image_path, "rb") as f:
        files = {
            "image": (filename, f, "image/jpeg")
        }
        res = requests.post(url, files=files)



    if res.status_code != 200:
        return None
    
    print("Upload response:", res.json())
    uploaded_file = res.json().get("name")
    return uploaded_file


def generate_large_seed():
    """Generate a large random seed."""
    seed = random.randint(10**14, 10**15 - 1)
    print(seed, type(seed))
    return seed

if __name__ == "__main__":
    # Test loading workflow
    generate_large_seed()