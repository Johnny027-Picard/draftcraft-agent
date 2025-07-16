@echo off
REM ProposifyAI Windows Deployment Script

setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=proposifyai
set APP_DIR=C:\opt\%APP_NAME%
set BACKUP_DIR=C:\opt\backups\%APP_NAME%
set LOG_FILE=C:\var\log\%APP_NAME%\deploy.log

REM Create log directory
if not exist "C:\var\log\%APP_NAME%" mkdir "C:\var\log\%APP_NAME%"

REM Logging function
:log
echo [%date% %time%] %~1 >> "%LOG_FILE%"
echo [%date% %time%] %~1
goto :eof

REM Error function
:error
echo [ERROR] %~1 >> "%LOG_FILE%"
echo [ERROR] %~1
exit /b 1

REM Check if .env file exists
if not exist ".env" (
    call :error ".env file not found. Please create it with your configuration."
    exit /b 1
)

call :log "Starting deployment..."

REM Check prerequisites
call :log "Checking prerequisites..."

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    call :error "Docker is required but not installed"
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :error "Docker Compose is required but not installed"
    exit /b 1
)

REM Create necessary directories
call :log "Creating necessary directories..."
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup current deployment
if exist "%APP_DIR%" (
    call :log "Creating backup of current deployment..."
    set backup_name=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set backup_name=!backup_name: =0!
    xcopy "%APP_DIR%" "%BACKUP_DIR%\!backup_name!\" /E /I /H /Y >nul
    call :log "Backup created: %BACKUP_DIR%\!backup_name!"
)

REM Stop current services
call :log "Stopping current services..."
docker-compose down >nul 2>&1

REM Deploy new version
call :log "Deploying new version..."

REM Copy application files
xcopy "." "%APP_DIR%\" /E /I /H /Y >nul

REM Build and start Docker services
call :log "Building and starting Docker services..."
cd /d "%APP_DIR%"
docker-compose build --no-cache
docker-compose up -d

REM Wait for services to be ready
call :log "Waiting for services to be ready..."
timeout /t 30 /nobreak >nul

REM Health check
call :log "Performing health check..."
set max_attempts=30
set attempt=1

:health_check_loop
curl -f http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    call :log "Health check passed"
    goto :health_check_passed
)

if !attempt! geq !max_attempts! (
    call :error "Health check failed after !max_attempts! attempts"
    exit /b 1
)

call :log "Health check attempt !attempt!/!max_attempts! failed, retrying..."
timeout /t 10 /nobreak >nul
set /a attempt+=1
goto :health_check_loop

:health_check_passed

REM Database migration
call :log "Running database migrations..."
docker-compose exec -T web flask db upgrade

REM Test critical functionality
call :log "Testing critical functionality..."

REM Test API health
curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/health | findstr "200" >nul
if not errorlevel 1 (
    call :log "API health check passed"
) else (
    call :log "API health check failed"
)

REM Security checks
call :log "Performing security checks..."

REM Check for exposed secrets
findstr /r /i "sk_live pk_live password secret" "%APP_DIR%" >nul 2>&1
if not errorlevel 1 (
    call :log "WARNING: Potential secrets found in codebase"
)

REM Final health check
call :log "Performing final health check..."
timeout /t 10 /nobreak >nul

curl -f http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    call :log "Deployment completed successfully!"
    call :log "Application is running at: http://localhost:8000"
    call :log "Health check endpoint: http://localhost:8000/health"
) else (
    call :error "Deployment failed - health check failed"
    exit /b 1
)

REM Cleanup old backups (keep last 5)
call :log "Cleaning up old backups..."
cd /d "%BACKUP_DIR%"
for /f "tokens=*" %%i in ('dir /b /o-d') do (
    set /a count+=1
    if !count! gtr 5 del /q "%%i"
)

REM Log deployment completion
call :log "Deployment completed at %date% %time%"
call :log "Log file: %LOG_FILE%"

echo.
echo Deployment completed successfully!
echo Monitor logs: type "%LOG_FILE%"
echo Application: http://localhost:8000
echo.

pause 