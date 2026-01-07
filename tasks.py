from celery_app import celery_app
from comfy_utility import (
    get_history,
    get_node_images,
    get_node_videos,
    download_images_list,
)
import logging
import redis
import os
from PIL import Image

from database import SessionLocal
from models import GenerationTask, GeneratedFile
import db_operations  

from dotenv import load_dotenv
from run_pod_utility import get_running_pod
import os
load_dotenv()





# -------------------------
# Redis (SEPARATE DB)
# -------------------------
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=2,  # <-- separate from Celery broker
    decode_responses=True,
)

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# Constants
# -------------------------------------------------
LOCK_TTL = 3600            # Max time one task may run
DONE_TTL = 24 * 3600       # Keep completion marker
DEFAULT_RETRY = 5
VIDEO_RETRY = 20

# -------------------------
# Celery Task
# -------------------------
@celery_app.task(
    bind=True,
    name="generate.comfy.task",
    max_retries=30,
    default_retry_delay=DEFAULT_RETRY,
)
def generate_task(self, response_id: str, video: bool = False):
    # -------------------------
    # Validate input
    # -------------------------
    if not response_id:
        raise ValueError("response_id is required")


    retry_delay = VIDEO_RETRY if video else DEFAULT_RETRY

    done_key = f"done:{response_id}"
    lock_key = f"lock:{response_id}"


    db = SessionLocal()

    try:
        # Check current status in Redis
        current_status = redis_client.get(done_key)
        print("Current status from Redis:", current_status)

        if current_status == "completed":
            logging.info(
                f"[TASK EXIT] response_id={response_id} already completed"
            )
            return {
                "status": "completed",
                "cached": True,
                "video": video,
            }

        # --------------------------------------------------
        # ATOMIC HARD LOCK (exact-once guarantee)
        # --------------------------------------------------
        # if not redis_client.set(done_key, "processing", nx=True, ex=3600):
        #     logging.info(
        #         f"[TASK EXIT] response_id={response_id} already handled"
        #     )
        #     return {
        #         "status": "completed",
        #         "cached": True,
        #         "video": video,
        #     }
        # -----------------------------------------
        # Acquire HARD execution lock (atomic)
        # -----------------------------------------
        print("Acquiring lock with key:", lock_key)
        print("elf.request.id:", self.request.id)
        acquired = redis_client.set(
            lock_key,
            self.request.id,
            nx=True,
            ex=LOCK_TTL,
        )

        if not acquired:
            owner = redis_client.get(lock_key)
            print('owner--->>', owner)
            print('self.request.id:--->>', self.request.id)
            owner = redis_client.get(lock_key)
            if owner == self.request.id:
                logging.info(
                    f"[TASK RETRY CONTINUE] {response_id} "
                    f"retry={self.request.retries}"
                )

            else:

                # Another worker owns it → exit
                logging.info(
                    f"[TASK EXIT] {response_id} "
                    f"being processed by {owner}"
                )
                return {
                    "status": "processing",
                    "cached": True,
                    "video": video,
                }


        logging.info(
            f"[TASK START] response_id={response_id} "
            f"video={video} retry={self.request.retries}"
        )

        # -------------------------
        # Fetch ComfyUI history
        # -------------------------
        RUNPOD_ID = get_running_pod()
        COMFY_URL=f"https://{RUNPOD_ID}-8188.proxy.runpod.net"
        print("ComfyUI URL in task:", COMFY_URL)
        
        history = get_history(response_id, COMFY_URL)
        if not history:
            raise self.retry(countdown=retry_delay)

        outputs = history.get(response_id, {}).get("outputs", {})

        # -------------------------
        # Not ready → retry later
        # -------------------------
        if not outputs:
            logging.info(
                f"No outputs yet for {response_id}. "
                f"Retrying in {retry_delay}s"
            )
            raise self.retry(countdown=retry_delay)

        logging.info(
            f"Outputs found for response_id={response_id}"
        )

        # -------------------------
        # Process output nodes
        # -------------------------
        final_files = []

        for node_id in outputs.keys():
            logging.info(
                f"Processing output node={node_id} "
                f"for response_id={response_id}"
            )

            if video:
                file_list = get_node_videos(outputs, node_id)
            else:
                file_list = get_node_images(outputs, node_id)

            logging.info(
                f"Files from node {node_id}: {file_list}"
            )

            downloaded = download_images_list(file_list, COMFY_URL)
            final_files.extend(downloaded)

        # -------------------------
        # No files → retry
        # -------------------------
        if not final_files:
            logging.warning(
                f"No files downloaded for {response_id}, retrying"
            )
            raise self.retry(countdown=retry_delay)
        
        #----------------------------
        # prepare metadata and store in DB
        #-------------------------
        files_metadata = []

        for file_path in final_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            width = height = duration = None
            file_format = None

            if not video:
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        file_format = img.format
                except Exception as e:
                    logging.warning(f"Failed to read image metadata for {file_path}: {e}")

            files_metadata.append({
                "url": file_path,  # Change to public URL if needed
                "file_name": file_name,
                "file_size_bytes": file_size,
                "width": width,
                "height": height,
                "duration_seconds": duration,
                "format": file_format,
            })

        # Insert generated files metadata into DB
        db_operations.add_generated_files(db=db, prompt_id=response_id, files=files_metadata, video=video)

        # Update task status to completed
        db_operations.update_task_status(db, response_id, "completed")

        # -------------------------
        # MARK COMPLETED
        # -------------------------
        redis_client.set(done_key, "completed", ex=60)
        redis_client.delete(lock_key)

        logging.info(
            f"[TASK SUCCESS] response_id={response_id} "
            f"files={final_files}"
        )

        return {
            "status": "completed",
            "files": final_files,
            "video": video,
        }

    # -------------------------
    # Max retries hit
    # -------------------------
    except self.MaxRetriesExceededError:
        redis_client.set(done_key, "failed", ex=3600)
        redis_client.delete(lock_key)   

        db_operations.update_task_status(db, response_id, "failed")
        logging.error(
            f"[TASK FAILED] Max retries exceeded "
            f"for response_id={response_id}"
        )
        return {
            "status": "failed",
            "error": "Generation timeout",
            "video": video,
        }

    # -------------------------
    # Any other error → retry
    # -------------------------
    except Exception as e:
        logging.exception(
            f"[TASK ERROR] response_id={response_id} error={e}"
        )
        # db_operations.update_task_status(db, response_id, "failed")

        # raise self.retry(exc=e, countdown=retry_delay)
    
    finally:
        db.close()
    
