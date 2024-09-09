from fastapi import FastAPI,HTTPException, status, Depends
import models
from schemas import UserBase,UserIn,UserOut,TodoBase,UpdatetTodo, TodoIn,TodoOut,Token
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import PyJWTError
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
from enum import Enum

# create tables from models
# models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)



SECRET_KEY = "c6fbb3ccae2cb7c92208451bddf55da6694b7529b3389b9e13328de16641a94f"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 15

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")

def get_password_hash(password:str):
    return pwd_context.hash(password)

def verify_password(plain_pwd:str,hashed_pwd:str):
    return pwd_context.verify(plain_pwd,hashed_pwd)

token = jwt.encode({"user":1},SECRET_KEY,ALGORITHM)
print(token)



app = FastAPI()


class Token(BaseModel):
    access_token:str
    # refresh_token:str
    token_type:str


oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")

def get_user(db:Session,username:str):
    user_model = db.query(models.User).filter(models.User.username==username).first()
    return user_model

def authenticate_user(username:str,password:str,db:Session):
    user = get_user(db,username)
    if user is None:
        return False
    
    if not verify_password(password,user.password):
        return False
    
    return user

def create_access_token(data:dict, expire_delta:timedelta | None = None):
    to_encode = data.copy()
    if expire_delta:
        expire = datetime.now(timezone.utc) + expire_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp":expire})
    encode_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encode_jwt

async def get_current_user(token:str = Depends(oauth2_schema),db:Session=Depends(get_db)):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username:str = payload.get("sub")
        if username is None:
            raise credential_exception

    except PyJWTError:
        raise credential_exception
    user = get_user(db,username=username)
    
    if user is None:
        raise credential_exception
    return user

@app.post("/user/create/",response_model=Token)
async def create_user(user:UserIn,db:Session = Depends(get_db)):
    check_user = authenticate_user(user.username,user.password,db)
    if check_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exist try to login")
    hashed_password = get_password_hash(user.password)

    user_model = models.User(
        username= user.username,
        password = hashed_password
    )
    db.add(user_model)
    db.commit()
    db.refresh(user_model)

    token_data = {
        "sub":user.username,
    }
    access_token = create_access_token(token_data)
    return {"access_token" :access_token,"token_type":"bearer"}

@app.post("/token/")
async def user_login(form_data:OAuth2PasswordRequestForm = Depends(),db:Session=Depends(get_db)):
    check_user = authenticate_user(form_data.username,form_data.password,db)
    if not check_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login to access the content")
    
    token_data = {
        "sub":form_data.username
    }

    token = create_access_token(token_data)
    return {"access_token" :token,"token_type":"bearer"}

@app.get("/users/list//",response_model = list[UserOut])
async def all_users(db:Session = Depends(get_db),current_user:UserOut = Depends(get_current_user)):
    if current_user.username != "rio":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="You have to be Admin to aceess the content.")
    users = db.query(models.User).all()
    return users

@app.get("/user/view/{user_id}/",response_model=UserOut)
async def user_detail(user_id:int,db:Session=Depends(get_db),current_user:UserOut = Depends(get_current_user)):
    if current_user.username != "rio":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="You have to be Admin to aceess the content.")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"User with ID {user_id} is not available.")
    return user


@app.delete("/user/delete/{user_id}")
async def delete_user(user_id:int,db:Session=Depends(get_db),current_user:UserOut=Depends(get_current_user)):
    if current_user.username != "rio":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="You have to be Admin to aceess the content.")
    user_model = db.query(models.User).filter(models.User.id == user_id).first()
    if user_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"User with ID {user_id} is not available.")
    db.delete(user_model)
    db.commit()
    
    return {"detai":f"User with ID {user_id} deleted successfully"}


@app.get("/user/todos/list/",response_model=list[TodoOut]) 
async def user_todos(current_user:UserOut = Depends(get_current_user),db:Session=Depends(get_db)):
    
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login to access the content")
    user_todos = db.query(models.ToDo).filter(models.ToDo.user_id == current_user.id).all()
    return user_todos

@app.get("/user/todo/view/{todo_id}",response_model=TodoOut)
async def user_view_doto(todo_id:int,current_user:UserOut=Depends(get_current_user),db:Session=Depends(get_db)):
    todo_model = db.query(models.ToDo).filter(models.ToDo.id == todo_id).first()

    if not todo_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Todo with ID {todo_id} is not available.")
    
    return todo_model

@app.post("/user/todo/create/",response_model = TodoOut)
async def create_user_todo(todo:TodoIn,db:Session=Depends(get_db),current_user:UserOut = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login to create a ToDo task.")

    if not todo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Provide information for title, description and completed.")

    todo_model = models.ToDo(
        title = todo.title,
        description = todo.description,
        completed = todo.completed,
        user_id = current_user.id
    )

    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)
    return todo_model


@app.put("/user/todo/update/",response_model=TodoOut)
async def update_todo(todo:UpdatetTodo,current_user:UserOut=Depends(get_current_user),db:Session=Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login to create a ToDo task.")

    to_update = db.query(models.ToDo).filter(models.ToDo.id == todo.id).first()
    if not to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Todo with ID {todo.id} is not available")

    to_update.title = todo.title
    to_update.description = todo.description
    to_update.completed = todo.completed

    db.commit()
    db.refresh(to_update)

    return to_update

@app.delete("/user/todo/delete/{todo_id}")
async def delete_todo(todo_id:int,current_user:UserOut=Depends(get_current_user),db:Session=Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login to create a ToDo task.")

    todo_model = db.query(models.ToDo).filter(models.ToDo.id == todo_id).first()

    if not todo_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Todo with ID {todo_id} is not available")

    db.delete(todo_model)
    db.commit()
    return {"detail": f"Todo with ID {todo_id} deleted successfully."}