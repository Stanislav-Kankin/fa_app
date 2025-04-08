import os
from datetime import datetime, timedelta, date
from fastapi import FastAPI, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models import User, Note, Media, SessionLocal
from passlib.context import CryptContext
from jose import jwt
import shutil

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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

# Маршруты для галереи
@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(
    request: Request, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    media_items = db.query(Media).filter(Media.owner_id == current_user.id).all()
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "username": current_user.username,
        "media_items": media_items
    })

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    # Определяем тип файла
    content_type = file.content_type
    if content_type.startswith('image'):
        media_type = 'image'
    elif content_type.startswith('video'):
        media_type = 'video'
    else:
        return templates.TemplateResponse("gallery.html", {
            "request": request,
            "username": current_user.username,
            "error": "Неподдерживаемый тип файла"
        })
    
    # Сохраняем файл
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Сохраняем в БД
    new_media = Media(
        filename=file.filename,
        filepath=file_path,
        media_type=media_type,
        owner_id=current_user.id
    )
    db.add(new_media)
    db.commit()
    
    return RedirectResponse("/gallery", status_code=303)

@app.post("/delete_media/{media_id}", response_class=HTMLResponse)
async def delete_media(
    request: Request,
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    media = db.query(Media).filter(
        Media.id == media_id,
        Media.owner_id == current_user.id
    ).first()
    
    if media:
        # Удаляем файл
        if os.path.exists(media.filepath):
            os.remove(media.filepath)
        # Удаляем запись из БД
        db.delete(media)
        db.commit()
    
    return RedirectResponse("/gallery", status_code=303)

# Маршруты для заметок
@app.get("/notes", response_class=HTMLResponse)
async def notes_page(
    request: Request, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    notes = db.query(Note).filter(Note.owner_id == current_user.id).order_by(Note.updated_at.desc()).all()
    return templates.TemplateResponse("notes.html", {
        "request": request,
        "username": current_user.username,
        "notes": notes,
        "today": date.today()
    })

@app.get("/notes/{note_id}", response_class=HTMLResponse)
async def view_note(
    request: Request,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == current_user.id
    ).first()
    
    if not note:
        return RedirectResponse("/notes")
    
    return templates.TemplateResponse("note_detail.html", {
        "request": request,
        "username": current_user.username,
        "note": note
    })

@app.post("/notes/create", response_class=HTMLResponse)
async def create_note(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    note_date: date = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    new_note = Note(
        title=title,
        content=content,
        note_date=note_date if note_date else date.today(),
        owner_id=current_user.id
    )
    db.add(new_note)
    db.commit()
    
    return RedirectResponse("/notes", status_code=303)

@app.post("/notes/update/{note_id}", response_class=HTMLResponse)
async def update_note(
    request: Request,
    note_id: int,
    title: str = Form(...),
    content: str = Form(...),
    note_date: date = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == current_user.id
    ).first()
    
    if note:
        note.title = title
        note.content = content
        note.note_date = note_date if note_date else note.note_date
        db.commit()
    
    return RedirectResponse(f"/notes/{note_id}", status_code=303)

@app.post("/notes/delete/{note_id}", response_class=HTMLResponse)
async def delete_note(
    request: Request,
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == current_user.id
    ).first()
    
    if note:
        db.delete(note)
        db.commit()
    
    return RedirectResponse("/notes", status_code=303)

# Маршруты для календаря
@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    today = date.today()
    current_year = year if year else today.year
    current_month = month if month else today.month
    
    # Получаем первый день месяца и количество дней в месяце
    first_day = date(current_year, current_month, 1)
    if current_month == 12:
        next_month = date(current_year + 1, 1, 1)
    else:
        next_month = date(current_year, current_month + 1, 1)
    last_day = next_month - timedelta(days=1)
    
    # Получаем заметки для этого месяца
    notes = db.query(Note).filter(
        Note.owner_id == current_user.id,
        Note.note_date >= first_day,
        Note.note_date <= last_day
    ).all()
    
    # Создаем словарь с днями, в которые есть заметки
    notes_days = {note.note_date.day: True for note in notes}
    
    # Генерируем календарь
    calendar_data = []
    week = []
    
    # Заполняем пустые дни в начале месяца
    for _ in range(first_day.weekday()):
        week.append({"day": None, "has_notes": False})
    
    # Заполняем дни месяца
    for day in range(1, last_day.day + 1):
        current_date = date(current_year, current_month, day)
        week.append({
            "day": day,
            "date": current_date,
            "is_today": current_date == today,
            "has_notes": day in notes_days
        })
        
        if len(week) == 7:
            calendar_data.append(week)
            week = []
    
    # Заполняем пустые дни в конце месяца
    if week:
        for _ in range(7 - len(week)):
            week.append({"day": None, "has_notes": False})
        calendar_data.append(week)
    
    # Определяем предыдущий и следующий месяц
    if current_month == 1:
        prev_month = (current_year - 1, 12)
    else:
        prev_month = (current_year, current_month - 1)
    
    if current_month == 12:
        next_month = (current_year + 1, 1)
    else:
        next_month = (current_year, current_month + 1)
    
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "username": current_user.username,
        "calendar": calendar_data,
        "current_year": current_year,
        "current_month": current_month,
        "month_name": first_day.strftime("%B %Y"),
        "prev_month": prev_month,
        "next_month": next_month,
        "today": today
    })

@app.get("/calendar/day/{day_date}", response_class=HTMLResponse)
async def day_notes(
    request: Request,
    day_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse("/login")
    
    notes = db.query(Note).filter(
        Note.owner_id == current_user.id,
        Note.note_date == day_date
    ).order_by(Note.created_at.desc()).all()
    
    return templates.TemplateResponse("day_notes.html", {
        "request": request,
        "username": current_user.username,
        "notes": notes,
        "day_date": day_date
    })