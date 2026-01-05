# comfy_utility.py
import json
import os
import requests
from dotenv import load_dotenv
import random
import logging
logger = logging.getLogger(__name__)

load_dotenv()



# ------------------------------
# JSON Workflow Management
# ------------------------------
def load_workflow(json_path: str = "new_flow_deploy.json"):
    try:
        """Load workflow JSON file."""
        logger.info("Loading workflow JSON | file=%s", json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Unable to Load the workflow: {json_path} due to {str(e)}")
        return None
    
# #  update workflow with prompt and image
def update_workflow(workflow: dict, prompt: str, image_path: str= None, prompt_node_index: int=35, image_node_index: int=None, I2V=False, seed_node_index= None):
    try:
        """Update workflow JSON with prompt and optional image."""
        print("Updating workflow with prompt:", prompt_node_index)
        print("Workflow keys:", workflow[str(prompt_node_index)]["inputs"])
        logger.info(
            "Updating workflow | prompt_node=%s | I2V=%s",
            prompt_node_index,
            I2V,
        )
        if I2V:
            # for I2V
            workflow[str(prompt_node_index)]["inputs"]["value"] = prompt

        else:
            # for  t2v or t2i
            workflow[str(prompt_node_index)]["inputs"]["text"] = prompt

        if image_path:
            
            workflow[str(image_node_index)]["inputs"]["image"] = image_path
            print("Updating workflow with image:", image_node_index)
            logger.info("Image injected into workflow | node=%s", image_node_index)


        print('seed_node_index-->>',seed_node_index)    
        if seed_node_index is not None:
            seed_value = generate_large_seed()
            print("previous seed value:", workflow[str(seed_node_index)]["inputs"]["seed"])
            workflow[str(seed_node_index)]["inputs"]["seed"] = seed_value
            logger.debug("Seed updated | node=%s | seed=%s", seed_node_index, seed_value)

        return workflow
    except Exception as e:
        logger.error(f"Unable to Update  the workflow: due to {str(e)}")
        return None

def send_prompt(workflow_json, COMFY_URL):
    try:
        """Send workflow JSON to ComfyUI"""
        logger.info("Sending workflow to ComfyUI | url=%s", COMFY_URL)

        res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow_json})
        

        if res.status_code != 200:
            return None
        return res.json()
    except Exception as e:
        logger.error(f"Unable to Send prompt due to {str(e)}")
        return None

def get_history(prompt_id, COMFY_URL):
    """Get finished job history"""
    url =f"{COMFY_URL}/history/{prompt_id}"
    logger.info("Fetching ComfyUI history | prompt_id=%s", prompt_id)


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
def upload_image_to_comfy(image_path: str, COMFY_URL):
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

#  updatet the image width and  height
def update_width_height(workflow: dict, node_id: str, width: int, height: int):
    try:
        node_id = str(node_id)
        print('new width: ', width)
        print('new height: ', height)
        print('node_id to update : ', node_id)

        # previous width hegiht
        print("previous width:", workflow[node_id]["inputs"]['width'])
        print("previous height:", workflow[node_id]["inputs"]['height'])

        #  update width height
        workflow[node_id]["inputs"]['width'] = int(width)
        workflow[node_id]["inputs"]['height'] = int(height)

        print('updated worflow:', workflow)

        return workflow
    except Exception as e:
        print('unable to update the work flow due to: ', str(e))
        return workflow
    
# update the widh and height of the mxSlider for the video
def update_slider_width_height(workflow: dict, node_id:str, width:int, height:int):
    try:
        node_id = str(node_id)
        print('new width: ', width)
        print('new height: ', height)
        print('node_id to update : ', node_id)

        # previous width hegiht
        print("previous Xi:", workflow[node_id]["inputs"]['Xi'])
        print("previous Xf:", workflow[node_id]["inputs"]['Xf'])
        print("previous Yi:", workflow[node_id]["inputs"]['Yi'])
        print("previous Yf:", workflow[node_id]["inputs"]['Yf'])

        #  update width height
        workflow[node_id]["inputs"]['Xi'] = int(width)
        workflow[node_id]["inputs"]['Xf'] = int(width)
        workflow[node_id]["inputs"]['Yi'] = int(height)
        workflow[node_id]["inputs"]['Yf'] = int(height)

        print('updated worflow:', workflow)

        return workflow
    except Exception as e:
        print("unable to update the width and height of the slider due to:", e)
        return workflow
    
#  update the the video  length
def update_frame_rate(workflow: dict, node_id:str, duration_in_sec: int):
    try:
        frame_count=(16*int(duration_in_sec))+1
        print(f"frame count for {duration_in_sec} sec is {frame_count}")

        workflow[str(node_id)]['inputs']['length'] = frame_count

        return workflow

    except Exception as e:
        print('unabe to  update the video duration due to:', e )
        return workflow


if __name__ == "__main__":
    # Test loading workflow
    generate_large_seed()