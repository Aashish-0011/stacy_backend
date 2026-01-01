# main.py
from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
import uuid
import os
import shutil
from dotenv import load_dotenv
from pydantic import BaseModel
import os
from fastapi.staticfiles import StaticFiles
from comfy_utility import (load_workflow, update_workflow, send_prompt, get_history, get_node_images, get_node_videos, download_images_list, upload_image_to_comfy, update_width_height,  update_slider_width_height)
from deps import get_db
from tasks import generate_task
from celery.result import AsyncResult
from celery_app import celery_app  # import your configured Celery app
import db_operations
from database import SessionLocal
from run_pod_utility import get_running_pod
from sqlalchemy.orm import Session
from deps import get_db
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

# Load environment variable
model_path = os.getenv("IMG_MODEL")
# COMFY_URL = os.getenv("COMFY_URL")

RUNPOD_ID=get_running_pod()


print('RUNPOD_ID--->>>',RUNPOD_ID)

COMFY_URL=f"https://{RUNPOD_ID}-8188.proxy.runpod.net"

print('COMFY_URL--->>>',COMFY_URL)



# load Stable Diffusion model
print("Loading model from:", model_path)


# Folder to store generated images
os.makedirs("outputs", exist_ok=True)
os.makedirs("inputs", exist_ok=True)


app = FastAPI()
# Expose static image folder publicly
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/inputs", StaticFiles(directory="inputs"), name="inputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allow all origins
    allow_credentials=True,
    allow_methods=["*"],        # allow all HTTP methods
    allow_headers=["*"],        # allow all headers
)

class Prompt(BaseModel):
    prompt: str
    img_type: str = "realistic"  # default type is 'realistic'
    user_id: str = None
    width:str=None
    height:str=None



#  api to genrate image with comfy
@app.post("/api/generate_image")
def generate_image_with_comfy(data: Prompt, db: Session = Depends(get_db)):

    #  check runpod is availabe or not
    if not RUNPOD_ID:
        return JSONResponse(content={"error": "RUNPOD_ID is not available."}, status_code=400)



    img_type = data.img_type
    user_id = data.user_id
    width=data.width
    height=data.height
    print("Generating  image for:", img_type, "User ID:", user_id)
    if not user_id:
        return JSONResponse(content={"error": "user_id is required."}, status_code=400)


    if img_type == "semi_realistic":
        #   workflow for semi-realistic image
        workflow_file = "t2i_semi_realistic2.json"
        prompt_node_index = "3"
        seed_node_index = "12"
    else:
        img_type = "ultra_realistic"
        # workflow for t2i_ultra_realistic2
        workflow_file = "t2i_ultra_realistic2.json"
        prompt_node_index = "3"
        seed_node_index = "12"
    
    # node id of the empty latent image
    laten_image_node='6'
  
    print('generating image with comfyui workflow:', workflow_file)

    #  load the workflow JSON
    workflow = load_workflow(workflow_file)

    #  update the prompt node in the workflow
    workflow=  update_workflow(workflow=workflow, prompt=data.prompt, prompt_node_index=prompt_node_index, seed_node_index=seed_node_index)

    # update width and height if user  provide
    if width and height:
        print('updating width and height.....')
        workflow=update_width_height(workflow=workflow,  node_id=laten_image_node, width=int(width), height=int(height))
        print('width height updated')

    #  Send workflow to ComfyUI
    res=send_prompt(workflow, COMFY_URL)

    if not res:
        return JSONResponse(content={"error": "Failed to  generate image please try again later."}, status_code=500)

    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)

    # Create a task record in the database
    generating_task=db_operations.create_generation_task(
        db,
        prompt_id=response_id,
        user_id=user_id,
        task_type="image",
        generation_style=img_type,
        input_prompt=data.prompt,
    )

    print(f"Created Task: {generating_task.prompt_id}, Status: {generating_task.status}")
    # start the celery task to fetch the images
    task = generate_task.delay(response_id=response_id, video=False)
    
    return JSONResponse(
        content={"task_id": task.id, "response_id": response_id, "message": "Image generation initiated."},status_code=202)


#  api to generate video  with comfy
@app.post("/api/generate_text_video")
def generate_text_video_with_comfy(data: Prompt, db: Session = Depends(get_db)):
    
    #  check runpod is availabe or not
    if not RUNPOD_ID:
        return JSONResponse(content={"error": "RUNPOD_ID is not available."}, status_code=400)
    
    video_style= data.img_type
    user_id = data.user_id
    width=data.width
    height=data.height
    print("Generating  video for:", video_style, "User ID:", user_id)
    if not user_id:
        return JSONResponse(content={"error": "user_id is required."}, status_code=400)

    if video_style == "cartoon":
        #   workflow for semi-realistic image
        workflow_file = "t2v_cartoon_style.json"
        prompt_node_index = "123"
    else:
        # workflow for t2i_ultra_realistic2
        video_style = "smooth"
        workflow_file = "wan22_smooth_workflow_t2v.json"
        prompt_node_index = "123"
    
    # slider node id for update width and  height
    slider_node_id="112"

    print('generating video with comfyui workflow:', workflow_file)

    #  load the workflow JSON
    workflow=load_workflow(workflow_file)

    # update the prompt node in the workflow
    workflow=  update_workflow(workflow=workflow, prompt=data.prompt, prompt_node_index=prompt_node_index)

    if width and height:
        workflow = update_slider_width_height(workflow=workflow, node_id=slider_node_id, width=int(width), height=int(height))
 
    #  Send workflow to ComfyUI
    res=send_prompt(workflow, COMFY_URL)

    if not res:
        return JSONResponse(content={"error": "Failed to  generate video please try again later."}, status_code=500)
    
    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)

    # Create a task record in the database
    generating_task=db_operations.create_generation_task(
        db,
        prompt_id=response_id,
        user_id=user_id,
        task_type="t2v",
        generation_style=video_style,
        input_prompt=data.prompt,
    )

    print(f"Created Task: {generating_task.prompt_id}, Status: {generating_task.status}")

    # start the celery task to fetch the images
    task = generate_task.delay(response_id=response_id, video=True)
    
    return JSONResponse(
        content={"task_id": task.id, "response_id": response_id, "message": "Video generation initiated."},status_code=202)


# api to generate video from image
@app.post("/api/generate_image_video")
def generate_image_video_with_comfy(file: UploadFile = File(...), prompt: str = Form(...), user_id: str = Form(None), width: int = Form(None), height: int = Form(None), db: Session = Depends(get_db)):

    #  check runpod is availabe or not
    if not RUNPOD_ID:
        return JSONResponse(content={"error": "RUNPOD_ID is not available."}, status_code=400)

    if not user_id:
        return JSONResponse(content={"error": "user_id is required."}, status_code=400)

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

    if width and height:
        slider_node_id="97"
        workflow = update_slider_width_height(workflow=workflow, node_id=slider_node_id, width=int(width), height=int(height))
 

    print('=*80\n\n')
    print('\n\n\nUpdated workflow:', workflow) 
    print('\n\n=*80\n\n')

    #  Send workflow to ComfyUI
    res=send_prompt(workflow, COMFY_URL)

    if not res:
        return JSONResponse(content={"error": "Failed to  generate video please try again later."}, status_code=500)

    response_id=res.get("prompt_id")
    print('Response:', res)
    print('Response prompt_id:', response_id)

    video_style= "smooth"

    # Create a task record in the database
    generating_task=db_operations.create_generation_task(
        db,
        prompt_id=response_id,
        user_id=user_id,
        task_type="i2v",
        input_image_url=input_path,
        generation_style=video_style,
        input_prompt=prompt,

    )

    print(f"Created Task: {generating_task.prompt_id}, Status: {generating_task.status}")

    # start the celery task to fetch the images
    task = generate_task.delay(response_id=response_id, video=True)
    
    return JSONResponse(
        content={"task_id": task.id, "response_id": response_id, "message": "Video generation initiated."},status_code=202)

# get all user promt
@app.get("/api/prompts/{user_id}")
def get_user_prompts_api(
    user_id: str,
    db: Session = Depends(get_db),
):
    tasks = db_operations.get_user_prompts(db, user_id)

    data = [
        {
            "prompt_id": t.prompt_id,
            "task_type": t.task_type,
            "input_prompt": t.input_prompt,
            "input_image_url": t.input_image_url,
            "generation_style": t.generation_style,
            "status": t.status,
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
        }
        for t in tasks
    ]

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "count": len(data),
            "data": data,
        },
    )


#get all promt response
@app.get("/api/prompts/{prompt_id}/response")
def get_prompt_response_api(
    prompt_id: str,
    db: Session = Depends(get_db),
):
    task = db_operations.get_task_with_files(db, prompt_id)

    if not task:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Prompt not found",
            },
        )

    files = [
        {
            "file_url": f.file_url,
            "file_type": f.file_type,
            "file_name": f.file_name,
            "file_size_bytes": f.file_size_bytes,
            "width": f.width,
            "height": f.height,
            "duration_seconds": f.duration_seconds,
            "format": f.format,
            "created_at": str(f.created_at),
        }
        for f in task.generated_files
    ]

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "prompt_id": task.prompt_id,
            "task_type": task.task_type,
            "status": task.status,
            "files": files,
        },
    )


#api to update hte run pod  id
@app.post("/api/update_runpod_id")
def update_runpod_id():
    global RUNPOD_ID, COMFY_URL
    RUNPOD_ID = get_running_pod()
    COMFY_URL = f"https://{RUNPOD_ID}-8188.proxy.runpod.net"
    if RUNPOD_ID:
        print("Updated RUNPOD_ID:", RUNPOD_ID)
        print("Updated COMFY_URL:", COMFY_URL)
        return JSONResponse(content={"RUNPOD_ID": RUNPOD_ID, "COMFY_URL": COMFY_URL}, status_code=200)
    
    return JSONResponse(content={"error": "Failed to update RUNPOD_ID."}, status_code=500)


@app.get("/api/task_status/{task_id}")
def task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app) 

    if task.state in ("PENDING", "STARTED"):
        return {"status": "processing"}

    if task.state == "SUCCESS":
        return task.result

    if task.state == "FAILURE":
        return {"status": "failed", "error": str(task.result)}



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


