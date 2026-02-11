batch
@echo off
title FastAPI Image Server
echo Menjalankan Image Server...

:: 1. Cek dan Masuk ke Virtual Environment
IF NOT EXIST venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment venv tidak ditemukan!
    echo Menyiapkan venv baru...
    python -m venv venv
)

:: 2. Aktifkan venv
call venv\Scripts\activate.bat

:: 3. Pastikan Uvicorn & FastAPI terinstal di dalam venv
echo Memeriksa dependensi...
pip install uvicorn fastapi

:: 4. Jalankan Uvicorn Server
echo venv berhasil diaktifkan. Memulai Uvicorn di http://0.0.0.0:7896
:: Gunakan 'python -m uvicorn' untuk menghindari error "command not found" di beberapa sistem Windows
python -m uvicorn main:app --host 0.0.0.0 --port 7896 --reload

pause