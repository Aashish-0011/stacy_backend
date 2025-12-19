# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
import torch
from io import BytesIO
import requests
import time
import uuid
import os
import json
import base64
import shutil
# import websocket
from dotenv import load_dotenv
from pydantic import BaseModel
import os
from fastapi.staticfiles import StaticFiles
from comfy_utility import (load_workflow, update_workflow, send_prompt, get_history, get_node_images, get_node_videos, download_images_list, upload_image_to_comfy)


load_dotenv()

# Load environment variables
model_path = os.getenv("IMG_MODEL")
COMFY_URL = os.getenv("COMFY_URL")


# load Stable Diffusion model
print("Loading model from:", model_path)
print('Gpu availale:', torch.cuda.is_available())


# Folder to store generated images
os.makedirs("outputs", exist_ok=True)


app = FastAPI()
# Expose static image folder publicly
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

class Prompt(BaseModel):
    prompt: str
    img_type: str = "realistic"  # default type is 'realistic'


# generate the image from the prompt
# @app.post("/generate_image_comfy")
# def geneerate_image_comfy(data: Prompt):
#     print("Endpoint /generate_image_comfy called.")
#     print("Generating image for prompt via ComfyUI:", data.prompt)

#     #  load the workflow JSON
#     workflow = load_workflow("civit_ai_flow.json")

#     # 2. Insert prompt into the workflow nodes
#     workflow=  update_workflow(workflow=workflow, prompt=data.prompt, prompt_node_index=10)

#     # Unique ID for the request
#     prompt_id = str(uuid.uuid4())

#     # 3. Send workflow to ComfyUI
#     res=send_prompt(workflow, prompt_id)
#     response_id=res.get("prompt_id")
#     print('Response:', res)
#     print('Response prompt_id:', response_id)
    

#     # 2. Wait for image to be generated
#     max_retries = 60  # 2s x 60 = 120 seconds max wait

#     for _ in range(max_retries):
#         time.sleep(2)
#         history = get_history(response_id)
#         print('history--->>,', history)
#         outputs =history.get(response_id,{}).get('outputs',{})
#         print('\n\noutput--????', outputs )
#         if outputs:
#             print("Received output from ComfyUI.")
#             break

#     else:
#         return JSONResponse(
#             content={"error": "Timed out waiting for image generation."},
#             status_code=504
#         )

#     # 3. Extract filename frm node 13 and 23
#     # output_node13 = history.get(response_id,{}).get('outputs',{}).get('13',{}).get('images',{})
#     # output_node23 = history.get(response_id,{}).get('outputs',{}).get('23',{}).get('images',{})
#     node13_images = get_node_images(outputs, "13")
#     node23_images = get_node_images(outputs, "23")
#     print("Node 13 images:", node13_images)
#     print("Node 23 images:", node23_images)


#     # Download images
#     downloaded_13 = download_images_list(node13_images)
#     downloaded_23 = download_images_list(node23_images)
#     print("Downloaded files node 13:", downloaded_13)
#     print("Downloaded files node 23:", downloaded_23)

#     final_files = downloaded_13 + downloaded_23
#     print("Final output:", final_files)

#     return JSONResponse(content={'files': final_files}, status_code=200)


#  api to genrate image with comfy
@app.post("/api/generate_image")
def generate_image_with_comfy(data: Prompt):


    img_type = data.img_type
    print("Generating  image for:", img_type)


    if img_type == "semi_realistic":
        #   workflow for semi-realistic image
        workflow_file = "t2i_semi_realistic2.json"
        prompt_node_index = "3"
    else:
        # workflow for t2i_ultra_realistic2
        workflow_file = "t2i_ultra_realistic2.json"
        prompt_node_index = "3"
  
    print('generating image with comfyui workflow:', workflow_file)

    #  load the workflow JSON
    workflow = load_workflow(workflow_file)

    #  update the prompt node in the workflow
    workflow=  update_workflow(workflow=workflow, prompt=data.prompt, prompt_node_index=prompt_node_index)

    # Unique ID for the request
    prompt_id = str(uuid.uuid4())

    #  Send workflow to ComfyUI
    res=send_prompt(workflow, prompt_id)

    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)
    #  Wait for image to be generated
    max_retries = 60  # 2s x 60 = 120 seconds max wait

    for _ in range(max_retries):
        time.sleep(2)
        history = get_history(response_id)
        print('history--->>,', history)
        outputs =history.get(response_id,{}).get('outputs',{})
        print('\n\noutput--????', outputs )
        if outputs:
            print("Received output from ComfyUI.")
            break

    else:
        return JSONResponse(
            content={"error": "Timed out waiting for image generation."},
            status_code=504
        ) 

    # get the number of output nodes
    outputs_nodes= outputs.keys()

    print("Output nodes:", outputs_nodes)
    
    #  get the image list from the output nodes
    final_files=[]
    for node_id in outputs_nodes:
        print(f"Processing output node: {node_id}")
        image_list = get_node_images(outputs, node_id)
        print(f"Image list for node {node_id}:", image_list)

        # download the images
        downloaded_files = download_images_list(image_list) 

        print(f"Downloaded files for node {node_id}:", downloaded_files)
        final_files.extend(downloaded_files)

    # final_files = downloaded_13 + downloaded_23
    print("Final output:", final_files)

    return JSONResponse(content={'files': final_files}, status_code=200)

#  api to generate video  with comfy
@app.post("/api/generate_text_video")
def generate_text_video_with_comfy(data: Prompt):
    video_style= data.img_type
    print("Generating video with style:", video_style)

    if video_style == "cartoon":
        #   workflow for semi-realistic image
        workflow_file = "t2v_cartoon_style.json"
        prompt_node_index = "123"
    else:
        # workflow for t2i_ultra_realistic2
        workflow_file = "wan22_smooth_workflow_t2v.json"
        prompt_node_index = "123"

    print('generating video with comfyui workflow:', workflow_file)

    #  load the workflow JSON
    workflow=load_workflow(workflow_file)

    # update the prompt node in the workflow
    workflow=  update_workflow(workflow=workflow, prompt=data.prompt, prompt_node_index=prompt_node_index)

    # Unique ID for the request
    prompt_id = str(uuid.uuid4())   
    #  Send workflow to ComfyUI
    res=send_prompt(workflow, prompt_id)

    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)
    #  Wait for image to be generated
    max_retries = 60  # 2s x 60 = 120 seconds max wait

    for _ in range(max_retries):
        time.sleep(2)
        history = get_history(response_id)
        print('history--->>,', history)
        outputs =history.get(response_id,{}).get('outputs',{})
        print('\n\noutput--????', outputs )
        if outputs:
            print("Received output from ComfyUI.")
            break

    else:
        return JSONResponse(
            content={"error": "Timed out waiting for image generation."},
            status_code=504
        ) 

    # get the number of output nodes
    outputs_nodes= outputs.keys()

    print("Output nodes:", outputs_nodes)
    
    #  get the image list from the output nodes
    final_files=[]
    for node_id in outputs_nodes:
        print(f"Processing output node: {node_id}")
        image_list = get_node_videos(outputs, node_id)
        print(f"Image list for node {node_id}:", image_list)

        # download the images
        downloaded_files = download_images_list(image_list) 

        print(f"Downloaded files for node {node_id}:", downloaded_files)
        final_files.extend(downloaded_files)

    # final_files = downloaded_13 + downloaded_23
    print("Final output:", final_files)

    return JSONResponse(content={'files': final_files}, status_code=200)


# api to generate video from image
@app.post("/api/generate_image_video")
def generate_image_video_with_comfy(file: UploadFile = File(...), prompt: str = Form(...)):

    # Save uploaded image
    input_path = f"inputs/{uuid.uuid4()}_{file.filename}"
    print("Saving uploaded image to:", input_path)
    os.makedirs("inputs", exist_ok=True)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    #  upload image to comfyui server
    comfy_image_path = upload_image_to_comfy(input_path)
    print("Uploaded image to ComfyUI:", comfy_image_path)

    # workflow for smooth video
    workflow_file = "WAN22_Smooth_Workflow_v2_I2V.json"
    prompt_node_index = "88"
    image_node_index = "52"

    print('generating video with comfyui workflow:', workflow_file)

    #  load the workflow JSON
    workflow=load_workflow(workflow_file)

    print('prompt:', prompt)

    # update the prompt node in the workflow
    workflow =  update_workflow(workflow=workflow, prompt=prompt, prompt_node_index=prompt_node_index, I2V=True, image_path=comfy_image_path, image_node_index=image_node_index)

    print('=*80\n\n')
    print('\n\n\nUpdated workflow:', workflow) 
    print('\n\n=*80\n\n')

    # Unique ID for the request
    prompt_id = str(uuid.uuid4())   
    #  Send workflow to ComfyUI
    res=send_prompt(workflow, prompt_id)

    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)
    return JSONResponse(content={'message': 'Video generation initiated.'}, status_code=200)



if __name__ == "__main__":

    #  download the history from comfyui
    # cortoon type
    # url="https://lq2907idlvwrna-8188.proxy.runpod.net/history/963e783c-6c33-4384-85c3-ef95513c0f44"
    # response_id = "963e783c-6c33-4384-85c3-ef95513c0f44"
    # response_id = "dd5e427f-a355-4f22-9de5-702ca6b48d1a"
    # img
    # response_id = "02ea8aab-84ed-40ae-8f5e-3c4a5d01686b"

    # video
    # response_id="c455821d-ac72-425c-8a74-eb6fef27d443"
    # response_id="5bcff9a8-b069-4449-963c-5040dba2d7c5"

    # normal
    # response_id='9d66c8d6-9472-4d82-a420-810b6aba1d0b'

    # i2v
    response_id='83441b89-dcbc-48be-975a-fa7973385e73'

    print('Fetching history for prompt_id:', response_id)

    history = get_history(response_id)
    print('history--->>,', history)
    outputs =history.get(response_id,{}).get('outputs',{})
    print('\n\noutput--????', outputs )

     # get the number of output nodes
    outputs_nodes= outputs.keys()

    print("Output nodes:", outputs_nodes)
    
    #  get the image list from the output nodes
    final_files=[]
    for node_id in outputs_nodes:
        print(f"Processing output node: {node_id}")
        image_list = get_node_videos(outputs, node_id)
        # image_list = get_node_images(outputs, node_id)
        print(f"Image list for node {node_id}:", image_list)

        # download the images
        downloaded_files = download_images_list(image_list) 

        print(f"Downloaded files for node {node_id}:", downloaded_files)
        final_files.extend(downloaded_files)

    # final_files = downloaded_13 + downloaded_23
    print("Final output:", final_files)


