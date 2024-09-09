from pydantic import BaseModel,EmailStr

# schemas are Pydantic models

class UserBase(BaseModel):
    username:str
    # email:EmailStr

    class Config:
        orm_mode=True
    

class UserIn(UserBase):
    password:str


class UserOut(UserBase):
    id:int
    

class TodoBase(BaseModel):
    title:str
    description:str
    completed:bool = False

    class Config:
        orm_mode=True


class TodoIn(TodoBase):
    pass

class TodoOut(TodoBase):
    id:int
    user_id:int

class UpdatetTodo(TodoBase):
    id:int

class Token(BaseModel):
    access_token:str
    token_type:str
    
