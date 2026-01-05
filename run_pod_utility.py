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
                print('Found running pod with imageName nextdiffusionai/comfyui-sageattention:cuda12.8')
                print('Pod ID:', pod.get('id'))
                logger.info(f'Running pod id fetched {pod.get('id')}')
                return pod.get('id')
            
        
        return None
    except Exception as e:
        logger.error(f"Unable to  fetch the runing  pof id  due to {str(e)}")


if __name__ == "__main__":
    running_pod_id=get_running_pod()



    print('pods:', running_pod_id)

