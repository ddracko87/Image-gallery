from fastapi import FastAPI, Request, HTTPException, Depends, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import Response
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
import pathlib

# --- KONFIGURASI KEAMANAN (WAJIB ADA) ---
SECRET_KEY = "ganti_dengan_kunci_sangat_rahasia_anda" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # 8 Jam
COOKIE_NAME = "access_token"

app = FastAPI()

ITEMS_PER_PAGE = 50
IMAGE_DIRECTORY = pathlib.Path("E:/picture")
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- LOGIKA TOKEN JWT ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_username(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # Jika tidak ada token, lempar ke halaman login
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

# --- GLOBAL EXCEPTION HANDLER (Untuk Redirect Otomatis ke Login) ---
@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def auth_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")

# --- RUTE AUTENTIKASI ---

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token")
def login_action(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "dracko" and form_data.password == "dracko120287":
        access_token = create_access_token(data={"sub": form_data.username})
        
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        # Simpan ke cookie agar browser otomatis mengirimnya di setiap request
        response.set_cookie(
            key=COOKIE_NAME, 
            value=access_token, 
            httponly=True, 
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
    
    raise HTTPException(status_code=400, detail="Username atau password salah")

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(COOKIE_NAME)
    return response

# --- RUTE APLIKASI (DENGAN PROTEKSI) ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request, username: str = Depends(get_current_username)):
    folders = [d.name for d in IMAGE_DIRECTORY.iterdir() if d.is_dir()]
    return templates.TemplateResponse(
        "list_folders.html",
        {"request": request, "folders": folders, "username": username}
    )

@app.get("/gallery/{folder_name:path}", response_class=HTMLResponse)
def gallery_view(
    request: Request, 
    folder_name: str, 
    username: str = Depends(get_current_username),
    page: int = Query(1, ge=1) 
):
    target_folder = IMAGE_DIRECTORY / folder_name
    if not target_folder.is_dir():
        raise HTTPException(status_code=404)

    subfolders = [d.name for d in target_folder.iterdir() if d.is_dir()]
    all_images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp'):
        all_images.extend(target_folder.glob(ext)) 
        
    total_images = len(all_images)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    images_on_page = all_images[start_index:end_index]

    file_urls = [f"/view/{img.relative_to(IMAGE_DIRECTORY).as_posix()}" for img in images_on_page]

    return templates.TemplateResponse(
        "list_files.html",
        {
            "request": request, 
            "files": file_urls, 
            "folder_name": folder_name, 
            "subfolders": subfolders, 
            "username": username,
            "page": page,
            "has_next": end_index < total_images,
            "has_prev": page > 1,
            "next_url": f"/gallery/{folder_name}?page={page + 1}",
            "prev_url": f"/gallery/{folder_name}?page={page - 1}",
        }
    )

@app.get("/view/{file_path:path}")
def protected_static(file_path: str, username: str = Depends(get_current_username)):
    target_file = IMAGE_DIRECTORY / file_path
    if not target_file.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(target_file)

@app.delete("/files/{file_path:path}", status_code=204)
def delete_file(file_path: str, username: str = Depends(get_current_username)):
    target_file = (IMAGE_DIRECTORY / file_path).resolve()
    if not target_file.is_file() or not target_file.is_relative_to(IMAGE_DIRECTORY):
        raise HTTPException(status_code=404)
    os.remove(target_file)
