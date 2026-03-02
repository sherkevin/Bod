from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
try:
    from backend.database import Base
except ImportError:
    from database import Base
# Fix for direct run vs package run import issues in some setups
# but usually .database relative import works if run as module.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    workouts = relationship("WorkoutLog", back_populates="user")

class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    audio_path = Column(String, nullable=True)
    image_path = Column(String, nullable=True) # New: Store image path
    transcript = Column(Text, nullable=True)
    
    # Structured Data
    exercise = Column(String, nullable=True)
    weight = Column(Float, nullable=True)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)

    # raw_log: 原始非结构化记录 (e.g., "做了5组深蹲")
    raw_log = Column(Text, nullable=True)
    # feedback: AI 生成建议
    feedback = Column(Text, nullable=True)
    
    status = Column(String, default="completed") # pending, processing, completed, failed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="workouts")

class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal = Column(String) # e.g., "strength", "hypertrophy", "endurance"
    content = Column(Text) # JSON string or markdown of the plan
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="plans")

# Add back_populates to User
User.plans = relationship("TrainingPlan", back_populates="user")
