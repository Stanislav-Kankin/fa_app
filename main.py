from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models import User, SessionLocal
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

app = FastAPI()

# Настройки
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="templates")

# Зависимости
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функции для работы с паролями и токенами
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    return user

# Маршруты
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        return templates.TemplateResponse("welcome.html", {"request": request, "username": current_user.username})
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        error = "Неверное имя пользователя или пароль"
        return templates.TemplateResponse("login.html", {"request": request, "error": error})
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = templates.TemplateResponse("welcome.html", {
        "request": request,
        "username": user.username
    })
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Проверка существующего пользователя
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        error = "Пользователь с таким именем или email уже существует"
        return templates.TemplateResponse("register.html", {"request": request, "error": error})
    
    # Создание нового пользователя
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "success": "Регистрация прошла успешно. Теперь вы можете войти."
    })

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = templates.TemplateResponse("index.html", {"request": request})
    response.delete_cookie("access_token")
    return response

@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "username": current_user.username,
        "message": "Это страница галереи"
    })

@app.get("/notes", response_class=HTMLResponse)
async def notes(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "username": current_user.username,
        "message": "Это страница заметок"
    })

@app.get("/calendar", response_class=HTMLResponse)
async def calendar(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("welcome.html", {
        "request": request,
        "username": current_user.username,
        "message": "Это страница календаря"
    })