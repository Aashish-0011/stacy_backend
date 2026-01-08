import os
from dotenv import load_dotenv
import requests
import runpod
load_dotenv()
import logging
logger = logging.getLogger(__name__)

# Load environment variables
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")

runpod.api_key = RUNPOD_API_KEY

# funtion to get running pod
def get_running_pod():
    try:

        pods = runpod.get_pods() 
        logger.info('fetching the runnig pod id')

        # Filter pods with desiredStatus 'RUNNING'
        running_pods = [pod for pod in pods if pod['desiredStatus'] == 'RUNNING']



        # get the id of the running pod  on which sage attention configure
        for pod in running_pods:
            print('running pod:', pod)
            if (pod.get('imageName') == 'nextdiffusionai/comfyui-sageattention:cuda12.8') or (pod.get('imageName') == 'nextdiffusionai/comfyui-sageattention:cuda12.8-new'):
                gpuCount=pod.get('gpuCount')
                print('Found running pod with imageName nextdiffusionai/comfyui-sageattention:cuda12.8')
                print('Pod ID:', pod.get('id'))
                logger.info(f'Running pod id fetched {pod.get('id')}')
                return pod.get('id'), gpuCount
            
        
        return None, None
    except Exception as e:
        logger.error(f"Unable to  fetch the runing  pof id  due to {str(e)}")
        return None, None


#  finctioon to  map with ip , port and worflow
def map_ip_workflow(gpu_count: int = 1, RUNPOD_ID: str= None):
    INITIAL_PORT=8188
    WORKFLOW_IP={}
    RUNPOD_ID=str(RUNPOD_ID)

    if gpu_count == 1:
       WORKFLOW_IP= {
           't2i': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
           't2v': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
           'i2v': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
        }
    
    elif gpu_count ==2:
        WORKFLOW_IP= {
           't2i': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
           't2v': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
           'i2v': f"https://{RUNPOD_ID}-8189.proxy.runpod.net",
        }
    
    else:
        WORKFLOW_IP= {
           't2i': f"https://{RUNPOD_ID}-8188.proxy.runpod.net",
           't2v': f"https://{RUNPOD_ID}-8189.proxy.runpod.net",
           'i2v': f"https://{RUNPOD_ID}-8190.proxy.runpod.net",
        }
    return WORKFLOW_IP



if __name__ == "__main__":
    running_pod_id, gpuCount=get_running_pod()

    print('pods:', running_pod_id)
    print('gpuCount:', gpuCount)

    comfy_url=map_ip_workflow(gpu_count=gpuCount, RUNPOD_ID=running_pod_id)

    print('comfy_url--->>>',comfy_url)

