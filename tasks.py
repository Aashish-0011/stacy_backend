import  time
from celery_app import celery_app
from comfy_utility import  get_history, get_node_images, get_node_videos, download_images_list
import logging
import redis


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


# confugure  basic logging
logging.basicConfig(level=logging.INFO)

@celery_app.task(bind=True, max_retries=30, default_retry_delay=60)
def generate_task(self, response_id: str= None, video = False):
    try:
        retry_delay = 300 if video else 60

        done_key = f"done:{response_id}"

         # 🛑 1️⃣ HARD STOP — NEVER HIT COMFYUI AGAIN
        if redis_client.get(done_key):
            logging.info(f"[TASK EXIT] response_id={response_id} already completed")
            return {
                "status": "completed",
                "cached": True,
                "video": video
            }
        

        # log the start of the task
        logging.info(
                    f"[TASK START] response_id={response_id} video={video} "
                    f"retry={self.request.retries}"
                )

        #  ge the history data
        history = get_history(response_id)

        outputs =history.get(response_id,{}).get('outputs',{})

        # ❌ Not ready → retry
        if not outputs:
            logging.info(
                f"No outputs yet for {response_id}. "
                f"Retrying in {retry_delay} seconds..."
            )
            raise self.retry(countdown=retry_delay)

        logging.info(f"Outputs :{outputs} found for response_id: {response_id}, proceeding with downloadd.")

        # get the number of output nodes
        outputs_nodes= outputs.keys()
        logging.info("Output nodes:", outputs_nodes, f' for response_id: {response_id}')

        #  get the image list from the output nodes
        final_files=[]
        for node_id in outputs_nodes:
            print(f"Processing output node: {node_id}")

            if video:
                file_list = get_node_videos(outputs, node_id)
                logging.info(f"Video  list for node {node_id}: {file_list}")
            
            else:
                file_list = get_node_images(outputs, node_id)
                logging.info(f"Image list for node {node_id}: {file_list}")

            # download the images
            downloaded_files = download_images_list(file_list) 

            logging.info(f"Downloaded files for node: {node_id}, downloaded_files: {downloaded_files} for response_id: {response_id}")
            final_files.extend(downloaded_files)
        
        #  MARK DONE (CRITICAL)
        # redis_client.delete(f"done:{response_id}")
        redis_client.set(done_key, "1", ex=3600)

        logging.info(
            f"[TASK SUCCESS] response_id={response_id} files={final_files}"
        )
        
        return {
            "status": "completed",
            "files": final_files,
            "video": video,
        }
    
    except self.MaxRetriesExceededError:
        logging.error(
            f"[TASK FAILED] Max retries exceeded for response_id={response_id}"
        )
        return {
            "status": "failed",
            "error": "Generation timeout",
            "video": video,
        }

    except Exception as e:
        logging.exception(
            f"[TASK ERROR] response_id={response_id} error={str(e)}"
        )
        raise self.retry(exc=e, countdown=retry_delay)