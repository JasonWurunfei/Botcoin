@echo off
set IMAGE_NAME=botcoin
set ENV_FILE=.env

REM Check if the image already exists
docker images -q %IMAGE_NAME% >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo ⚠️ Image "%IMAGE_NAME%" already exists. Deleting old image...
    docker rmi -f %IMAGE_NAME%
) else (
    echo ✅ No existing image found.
)

REM Build the new Docker image
echo 🛠️ Building Docker image: %IMAGE_NAME%
docker build -t %IMAGE_NAME% .

REM Run the Docker container with environment variables from .env
echo 🚀 Running Docker container with environment variables...
docker run --rm --env-file %ENV_FILE% %IMAGE_NAME%
