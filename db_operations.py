# db_operations.py

from sqlalchemy.orm import Session
from models import GenerationTask, GeneratedFile
from typing import List, Optional, Dict

def create_generation_task(
    db: Session,
    prompt_id: str,
    user_id: Optional[str],
    task_type: str,
    generation_style: str,
    input_prompt: str,
    input_image_url: Optional[str] = None,
) -> GenerationTask:
    """
    Create a new generation task record.
    """
    task = GenerationTask(
        prompt_id=prompt_id,
        user_id=user_id,
        task_type=task_type,
        generation_style=generation_style,
        input_prompt=input_prompt,
        input_image_url=input_image_url,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task_status(
    db: Session,
    prompt_id: str,
    status: str,
) -> Optional[GenerationTask]:
    """
    Update the status of an existing task.
    """
    task = db.query(GenerationTask).filter(GenerationTask.prompt_id == prompt_id).first()
    if not task:
        return None
    task.status = status
    db.commit()
    db.refresh(task)
    return task


def add_generated_files(
    db: Session,
    prompt_id: str,
    files: List[Dict],
    video: bool = False,
) -> List[GeneratedFile]:
    """
    Add generated files with metadata linked to a prompt_id.
    `files` is a list of dicts with keys like:
    url, file_name, file_size_bytes, width, height, duration_seconds, format
    """
    generated_files = []
    for file_data in files:
        gen_file = GeneratedFile(
            prompt_id=prompt_id,
            file_url=file_data.get("url"),
            file_type="video" if video else "image",
            file_name=file_data.get("file_name"),
            file_size_bytes=file_data.get("file_size_bytes"),
            width=file_data.get("width"),
            height=file_data.get("height"),
            duration_seconds=file_data.get("duration_seconds"),
            format=file_data.get("format"),
        )
        db.add(gen_file)
        generated_files.append(gen_file)
    db.commit()
    return generated_files


def get_task_with_files(
    db: Session,
    prompt_id: str,
) -> Optional[GenerationTask]:
    """
    Fetch task and all generated files by prompt_id.
    """
    task = (
        db.query(GenerationTask)
        .filter(GenerationTask.prompt_id == prompt_id)
        .first()
    )
    return task


if __name__=='__main__':
    # Example usage (requires a valid DB session)
    from database import SessionLocal

    db = SessionLocal()

    # Create a task
    # task = create_generation_task(
    #     db,
    #     prompt_id="example123",
    #     user_id="user456",
    #     task_type="image",
    #     input_prompt="A beautiful sunset over the mountains",
    # )
    # print(f"Created Task: {task.prompt_id}, Status: {task.status}")

    # # Update task status
    # updated_task = update_task_status(db, prompt_id="example123", status="in_progress")
    # print(f"Updated Task: {updated_task.prompt_id}, Status: {updated_task.status}")

    # # Add generated files
    # files_data = [
    #     {
    #         "url": "http://example.com/image1.png",
    #         "file_name": "image1.png",
    #         "file_size_bytes": 204800,
    #         "width": 1024,
    #         "height": 768,
    #         "format": "png",
    #     }
    # ]
    # generated_files = add_generated_files(db, prompt_id="example123", files=files_data)
    # for gf in generated_files:
    #     print(f"Added Generated File: {gf.file_url}, Type: {gf.file_type}")

    # # Fetch task with files
    fetched_task = get_task_with_files(db, prompt_id="example123")
    if fetched_task:
        print(f"Fetched Task: {fetched_task.prompt_id}, Status: {fetched_task.status}")
        for gf in fetched_task.generated_files:
            print(f" - File URL: {gf.file_url}, Type: {gf.file_type}")