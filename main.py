from fastapi import FastAPI, Request, HTTPException, Depends, Query, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
import pathlib

# --- KONFIGURASI KEAMANAN ---
SECRET_KEY = "ganti_dengan_kunci_sangat_rahasia_anda" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 
COOKIE_NAME = "access_token"

app = FastAPI()
ITEMS_PER_PAGE = 50
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- UTILITY JWT ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        path: str = payload.get("path")
        if username is None or path is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"username": username, "path": pathlib.Path(path)}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def auth_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")

# --- RUTE AUTENTIKASI ---

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/token")
def login_action(
    form_data: OAuth2PasswordRequestForm = Depends(),
    folder_path: str = Form(...) # Field ini harus ada di login.html
):
    path_obj = pathlib.Path(folder_path)
    if not path_obj.is_dir():
        # Anda bisa menggunakan [FastAPI HTTPException](https://fastapi.tiangolo.com) untuk detail error
        raise HTTPException(status_code=400, detail="Path direktori tidak ditemukan di server")

    if form_data.username == "admin" and form_data.password == "admin":
        access_token = create_access_token(data={"sub": form_data.username, "path": str(path_obj)})
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
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

# --- RUTE APLIKASI ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(get_current_user)):
    img_dir = user["path"]
    folders = [d.name for d in img_dir.iterdir() if d.is_dir()]
    return templates.TemplateResponse(
        "list_folders.html",
        {"request": request, "folders": folders, "username": user["username"]}
    )

@app.get("/gallery/{folder_name:path}", response_class=HTMLResponse)
def gallery_view(
    request: Request, 
    folder_name: str, 
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1) 
):
    base_dir = user["path"]
    target_folder = base_dir / folder_name
    
    if not target_folder.is_dir():
        raise HTTPException(status_code=404)

    subfolders = [d.name for d in target_folder.iterdir() if d.is_dir()]
    all_images = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp'):
        all_images.extend(target_folder.glob(ext)) 
        
    total_images = len(all_images)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    images_on_page = sorted(all_images)[start_index:end_index]

    # Gunakan relative_to agar URL tetap bersih
    file_urls = [f"/view/{img.relative_to(base_dir).as_posix()}" for img in images_on_page]

    return templates.TemplateResponse(
        "list_files.html",
        {
            "request": request, 
            "files": file_urls, 
            "folder_name": folder_name, 
            "subfolders": subfolders, 
            "username": user["username"],
            "page": page,
            "has_next": end_index < total_images,
            "has_prev": page > 1,
            "next_url": f"/gallery/{folder_name}?page={page + 1}",
            "prev_url": f"/gallery/{folder_name}?page={page - 1}",
        }
    )

@app.get("/view/{file_path:path}")
def protected_static(file_path: str, user: dict = Depends(get_current_user)):
    target_file = user["path"] / file_path
    if not target_file.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(target_file)

@app.delete("/files/{file_path:path}", status_code=204)
def delete_file(file_path: str, user: dict = Depends(get_current_user)):
    # Gunakan [Path.resolve](https://docs.python.org) untuk keamanan extra
    target_file = (user["path"] / file_path).resolve()
    if not target_file.is_file() or not target_file.is_relative_to(user["path"].resolve()):
        raise HTTPException(status_code=403, detail="Akses ditolak atau file tidak ditemukan")
    os.remove(target_file)
