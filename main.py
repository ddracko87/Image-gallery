# main.py (Kode Lengkap dan Benar)
from fastapi import FastAPI, Request, HTTPException, Depends, Query,Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import Response
import os
import pathlib
import secrets

app = FastAPI()
security = HTTPBasic()

ITEMS_PER_PAGE = 50 # pagination halaman yg ditampilkan
IMAGE_DIRECTORY = pathlib.Path("E:/picture") # root foldernya
templates = Jinja2Templates(directory="templates")

# app.mount("/view", StaticFiles(directory=IMAGE_DIRECTORY), name="view")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "dracko")
    correct_password = secrets.compare_digest(credentials.password, "dracko120287")

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- RUTE DENGAN AUTENTIKASI ---

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
    
    if not target_folder.is_dir() or not target_folder.is_relative_to(IMAGE_DIRECTORY):
        raise HTTPException(status_code=404, detail="Folder not found or invalid path")

    subfolders = [d.name for d in target_folder.iterdir() if d.is_dir()]
    
    image_extensions = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp')
    all_images = [] # Menggunakan nama all_images untuk konsistensi
    
    for ext in image_extensions:
        all_images.extend(target_folder.glob(ext)) 
        
    # --- LOGIKA PAGINATION ---
    total_images = len(all_images)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    
    images_on_page = all_images[start_index:end_index]

    file_urls = []
    for image_path in images_on_page:
        relative_path = image_path.relative_to(IMAGE_DIRECTORY).as_posix()
        file_urls.append(f"/view/{relative_path}") 

    # Cek apakah ada halaman berikutnya atau sebelumnya
    has_next_page = end_index < total_images
    has_prev_page = page > 1
    next_page_url = f"/gallery/{folder_name}?page={page + 1}" if has_next_page else None
    prev_page_url = f"/gallery/{folder_name}?page={page - 1}" if has_prev_page else None

    # --- HANYA ADA SATU PERNYATAAN RETURN UNTUK FUNGSI INI ---
    return templates.TemplateResponse(
        "list_files.html",
        {
            "request": request, 
            "files": file_urls, 
            "folder_name": folder_name, 
            "subfolders": subfolders, 
            "username": username,
            "page": page,
            "has_next": has_next_page,
            "has_prev": has_prev_page,
            "next_url": next_page_url,
            "prev_url": prev_page_url,
        }
    )


@app.get("/view/{file_path:path}")
def protected_static(file_path: str, username: str = Depends(get_current_username)):
    target_file = IMAGE_DIRECTORY / file_path
    
    if not target_file.is_file() or not target_file.is_relative_to(IMAGE_DIRECTORY):
        raise HTTPException(status_code=404, detail="File not found or invalid path")
    
    return FileResponse(target_file)

@app.get("/logout")
def logout():
    response = Response(content="Logged out. Close your browser tab.", status_code=401)
    response.headers["WWW-Authenticate"] = "Basic realm=\"Access restricted\", charset=\"UTF-8\""
    return response

@app.delete("/files/{file_path:path}", status_code=204)
def delete_file(file_path: str):
    import urllib.parse
    clean_path = urllib.parse.unquote(file_path)
    target_file = (IMAGE_DIRECTORY / file_path).resolve()

    if not target_file.is_file() or not target_file.is_relative_to(IMAGE_DIRECTORY):
        raise HTTPException(status_code=404, detail="File not found or invalid path")
    
    os.remove(target_file)
