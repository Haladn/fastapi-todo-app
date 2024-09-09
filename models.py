from database import Base
from sqlalchemy import String, Column, Integer,Boolean,ForeignKey,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime


class User(Base):
    __tablename__="users"
    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True, index=True,nullable=False)
    # email = Column(String,unique=True, index=True,nullable=False)
    password = Column(String,nullable=False)
    created_at = Column(DateTime,default=datetime.now)

    todo = relationship("ToDo",back_populates="user")


class ToDo(Base):
    __tablename__ = "todo"
    id = Column(Integer,primary_key=True,index=True)
    user_id = Column(Integer,ForeignKey("users.id"))
    title = Column(String,nullable=False)
    description = Column(String,nullable=False)
    completed = Column(Boolean,default=False)
    created_at = Column(DateTime,default=datetime.now)

    user = relationship("User",back_populates="todo")