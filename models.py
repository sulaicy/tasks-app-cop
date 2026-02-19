# models.py
from sqlalchemy import (Column, Integer, String, Float, Boolean, Date, DateTime,
                        ForeignKey, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, date

Base = declarative_base()

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    group = relationship('Group')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    is_global = Column(Boolean, default=False)
    points_per_unit = Column(Float, default=1.0)
    unit_name = Column(String(50), nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    due_date = Column(Date, nullable=True)

class TaskInstance(Base):
    __tablename__ = 'task_instances'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    date = Column(Date, nullable=False)
    target_value = Column(Float, default=0.0)
    completed_value = Column(Float, default=0.0)
    completed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    status = Column(String(20), default='pending')
    points_awarded = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# DB helper
def get_engine(db_url):
    return create_engine(db_url, connect_args={"check_same_thread": False})

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()