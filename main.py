from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import bcrypt
from passlib.context import CryptContext
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv

load_dotenv()

db_username = os.getenv('DB_USERNAME')
db_user_password = os.getenv('DB_USER_PASSWORD')
db_ip = os.getenv('DB_IP')



# Создание объекта FastAPI
app = FastAPI()

# Настройка базы данных MySQL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{db_username}:{db_user_password}@{db_ip}/{db_username}"

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Определение модели SQLAlchemy для пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), index=True)
    email = Column(String(100), unique=True, index=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(100))
    disabled = Column(Boolean, default=False)
    refresh_token = Column(String(250))

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Определение Pydantic модели для пользователя
class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    password: str | None = None
    disabled: bool | None = None    



class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    disabled: bool | None = None
    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=404, detail="Users not found")
    return users

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(username,db)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta*600
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# Получение текущего пользователя по токену
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Токен пользователя не валидный")
    user = get_user(username=token_data.username, db=db)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user




# ROUTES

# GET REQUESTS
@app.get("/", response_class=HTMLResponse)
async def get_client():
    with open("./static/index.html", "r") as file:
        return file.read()

@app.get("/users/me", response_model=UserResponse)
async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    print(current_user)
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return current_user

# Маршрут для получения пользователя по ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(username: str, db: Session = Depends(get_db)):
    print(2)
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/", response_model=list[UserResponse])
def get_users(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=404, detail="Пользователи не найдены")
    return users

@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}


# POST REQUESTS
@app.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    refresh_token = request.cookies.get('refresh_token')
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register/", response_model=UserResponse)
def register_user(response: Response, user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    refresh_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires    
    )

    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    print(refresh_token)

    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        refresh_token=refresh_token
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or Email already registered")

@app.post('/refresh')
def refresh(Authorize: Annotated[str, Depends(oauth2_scheme)]):
    print(Authorize)
    # Authorize.jwt_refresh_token_required()
    # current_user = Authorize.get_jwt_subject()
    # new_access_token = Authorize.create_access_token(subject=current_user)
    # return {"access_token": new_access_token}
    
# PUT REQUESTS
# Маршрут для обновления пользователя
@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(token: Annotated[str, Depends(oauth2_scheme)], user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.username:
        user.username = user_update.username
    if user_update.email:
        user.email = user_update.email
    if user_update.full_name:
        user.full_name = user_update.full_name
    if user_update.password:
        user.hashed_password = hash_password(user_update.password)
    if user_update.disabled is not None:
        user.disabled = user_update.disabled
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    
# DELETE REQUESTS
# Маршрут для удаления пользователя по ID
@app.delete("/users/{user_id}", response_model=UserResponse)
def delete_user(token: Annotated[str, Depends(oauth2_scheme)], user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
    json_compatible_user_data = jsonable_encoder(user)
    json_compatible_user_data['Delete'] = 'Пользователь удалён.'
    
    return JSONResponse(content=json_compatible_user_data, status_code=201)


origins = [
"http://localhost.tiangolo.com",
"https://localhost.tiangolo.com",
"http://localhost",
"http://localhost:8080",
]
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# def fake_decode_token(token: str, db: Session):
#     user = get_user_by_username(db, token)
#     return user

# def fake_hash_password(password: str):
#     return "fakehashed" + password

# Маршрут для обновления пользователя
# @app.put("/users/{user_id}", response_model=UserResponse)
# def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     if user_update.username:
#         user.username = user_update.username
#     if user_update.email:
#         user.email = user_update.email
#     if user_update.full_name:
#         user.full_name = user_update.full_name
#     if user_update.password:
#         user.hashed_password = fake_hash_password(user_update.password)
#     if user_update.disabled is not None:
#         user.disabled = user_update.disabled
#     try:
#         db.commit()
#         db.refresh(user)
#         return user
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=400, detail="Username or Email already registered")