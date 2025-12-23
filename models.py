from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func

class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    prompt_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(String(100), index=True, nullable=True)
    task_type = Column(String(20))
    generation_style = Column(String(50))
    input_prompt = Column(Text)
    input_image_url = Column(String(500), nullable=True)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    generated_files = relationship("GeneratedFile", back_populates="task", cascade="all, delete-orphan")


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(String(100), ForeignKey("generation_tasks.prompt_id"), index=True)
    file_url = Column(String(500))
    file_type = Column(String(20))  # e.g. 'image' or 'video'

    # Metadata fields
    file_name = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)       # for images/videos
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)  # for videos, nullable for images
    format = Column(String(50), nullable=True)       # e.g. 'png', 'mp4', etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("GenerationTask", back_populates="generated_files")
