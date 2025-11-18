# main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
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



load_dotenv()
# load Stable Diffusion model
model_path = os.getenv("IMG_MODEL")
lora_path = os.getenv("LORA_MODEL")

print("Loading model from:", model_path)
print('Gpu availale:', torch.cuda.is_available())

pipe = StableDiffusionXLPipeline.from_single_file(
    model_path,
    torch_dtype=torch.float16,
    variant="fp16",             # <-- critical
    use_safetensors=True,
    local_files_only=True,
    low_cpu_mem_usage=True,     # <-- prevents double GPU allocation
)

pipe = pipe.to("cuda", torch_dtype=torch.float16)
pipe.enable_xformers_memory_efficient_attention()

# DPM++ SDE (2M) + Karras
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe.scheduler.use_karras_sigmas = True
pipe.scheduler.algorithm_type = "dpmsolver++"   # DPM++
pipe.scheduler.solver_order = 2                 # 2M
pipe.scheduler.config.prediction_type = "v_prediction"   # SGM Uniform




print("Model loaded successfully.")

print("Lora path:", lora_path)
if lora_path and os.path.exists(lora_path):
    print("Applying LoRA from:", lora_path)
    pipe.load_lora_weights(lora_path)
    pipe.fuse_lora(lora_scale=0.8)
    print("LoRA applied successfully.")
else:
    print("⚠ LoRA NOT FOUND:", lora_path)

print("Model + LoRA loaded successfully.")

# Folder to store generated images
os.makedirs("outputs", exist_ok=True)


app = FastAPI()
# Expose static image folder publicly
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# COMFY_URL = "https://vgse6bydhunbzc-8188.proxy.runpod.net/"   # change to RunPod URL if remote


# # load workflow JSON
# def load_workflow(json_path: str="new_flow_deploy.json"):
#     with open(json_path, "r") as f:
#         return json.load(f)
    
# # encode image to base64
# def encode_image_to_base64(image_path: str):
#     with open(image_path, "rb") as img_file:
#         return base64.b64encode(img_file.read()).decode('utf-8')
    

# #  update workflow with prompt and image
# def update_workflow(workflow: dict, prompt: str, image_path: str):
#     workflow["35"]["inputs"]["text"] = prompt    # Example node
#     encoded_image = encode_image_to_base64(image_path)
#     workflow["37"]["inputs"]["image"] = [ {"data": encoded_image} ]  # Example node
#     return workflow

# def wait_for_completion(prompt_id: str):
#     """Waits on WebSocket until ComfyUI reports the job is completed."""
    
#     ws = websocket.WebSocket()
#     ws_url = COMFY_URL.replace("https", "wss") + f"ws?client_id={prompt_id}"
#     ws.connect(ws_url)

#     print("WS connected:", ws_url)

#     while True:
#         message = ws.recv()
#         data = json.loads(message)
#         print('data-->>')

#         if data.get("type") == "executed":
#             node_id = data["data"]["node"]
#             print("Node executed:", node_id)

#         if data.get("type") == "status" and data["data"].get("status") == "completed":
#             print("Render completed.")
#             ws.close()
#             return True



# @app.post("/generate_video")
# def generate_video(prompt: str, file: UploadFile = File(...)):

#     # Save uploaded image
#     input_path = f"inputs/{uuid.uuid4()}_{file.filename}"
#     print("Saving uploaded image to:", input_path)
#     os.makedirs("inputs", exist_ok=True)
#     with open(input_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     # 1. Load your workflow JSON (ComfyUI prompt)
#     workflow = load_workflow("new_flow_deploy.json")

#     print("Workflow loaded.", workflow)
    

#     # 2. Insert prompt into the workflow nodes
#     workflow=  update_workflow(workflow, prompt, input_path)

#     # Unique ID for the request
#     prompt_id = str(uuid.uuid4())

#     # 3. Send workflow to ComfyUI
#     requests.post(
#         f"{COMFY_URL}/prompt",
#         json={"prompt": workflow, "client_id": prompt_id}
#     )

#     print('Prompt sent to ComfyUI with ID:', prompt_id)

#     # get imgae
#     # Wait for WebSocket completion
#     wait_for_completion(prompt_id)

#     # Check /history
#     history = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
#     outputs = history.get(prompt_id, {}).get("outputs", {})

#     video_filename = None
#     for node_id, node_output in outputs.items():
#         if "video" in node_output:
#             video_filename = node_output["video"][0]["filename"]
#             break

#     if video_filename is None:
#         return {"error": "Video not found in workflow output"}

#     # Download video file
#     video_url = f"{COMFY_URL}/view?filename={video_filename}&type=output"
#     video_data = requests.get(video_url).content

#     local_video_path = f"output_{uuid.uuid4()}.mp4"
#     with open(local_video_path, "wb") as out:
#         out.write(video_data)

#     print("Returning video:", local_video_path)
#     return FileResponse(local_video_path, media_type="video/mp4")

class Prompt(BaseModel):
    prompt: str

# generate the image from the prompt
@app.post("/generate_image")
def generate_image_from_prompt(data: Prompt):
    print("Generating image for prompt:", data.prompt)


    result = pipe(
        prompt=data.prompt,
        negative_prompt="",
        num_inference_steps=28,
        guidance_scale=4,
        width=832,
        height=1216,
        clip_skip=2
    )
    print("Image generated successfully.",result)
    img = result.images[0]

    # Save image for future access
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join("outputs", filename)
    img.save(filepath)

    # convert to base64 for API response
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "saved_path": filepath,   # where the image is stored
        "image_base64": encoded   # base64 for immediate API use
    }


