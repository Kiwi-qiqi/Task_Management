@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM ======== CONFIGURATION SECTION - EDIT THESE VALUES AS NEEDED ================
REM =============================================================================

:: Main project configuration
set "PROJECT_DIR=%~dp0"
set "VERSION=0.17"
set "MAIN_OUTPUT_NAME=Mahle_Generic_Diagnostic"
set "ENCRYPTOR_OUTPUT_NAME=HEX_Encryptor_Tool"
set "ICON_PATH=%PROJECT_DIR%img\mahle_logo.ico"
set "VENV_NAME=package_env"
set "MAIN_SCRIPT=Mahle_Generic_Diagnostic.py"
set "ENCRYPTOR_SCRIPT=gui\encryptor_gui.py"
set "CONFIG_FILE=config.ini"

:: Signing configuration
set "SIGN_PASS_WORD=pass"
set "CERT_NAME=MAHLE_Certificate"
set "SIGN_TOOLS_DIR=%PROJECT_DIR%sign_tools"

:: Output directory configuration
set "RELEASE_DIR=%PROJECT_DIR%release"
set "TARGET_DIR=%RELEASE_DIR%\version_%VERSION%"

REM =============================================================================
REM ======== INITIALIZATION SECTION ============================================
REM =============================================================================

echo.
echo ============================================================
echo   MAHLE Packaging Tool v%VERSION% - Dual Build + Signing
echo ============================================================
echo   Building: 1. Generic Diagnostic Tool
echo             2. HEX Encryptor Tool
echo   Then signing the executables
echo   Start Time: %date% %time%
echo ============================================================
echo.

REM =============================================================================
REM ======== PRE-CHECK SECTION =================================================
REM =============================================================================

echo [1/8] Pre-flight Checks
echo ----------------------------------------

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    goto :error_exit
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VER=%%i"
echo [OK] %PYTHON_VER%

:: Check main diagnostic script
if not exist "%PROJECT_DIR%%MAIN_SCRIPT%" (
    echo [ERROR] Main script not found: %MAIN_SCRIPT%
    goto :error_exit
)
echo [OK] Main diagnostic script found: %MAIN_SCRIPT%

:: Check encryptor script
if not exist "%PROJECT_DIR%%ENCRYPTOR_SCRIPT%" (
    echo [ERROR] Encryptor script not found: %ENCRYPTOR_SCRIPT%
    goto :error_exit
)
echo [OK] Encryptor script found: %ENCRYPTOR_SCRIPT%

:: Check hex_encryptor module
if not exist "%PROJECT_DIR%utils\hex_encryptor.py" (
    echo [ERROR] hex_encryptor.py not found in utils folder
    goto :error_exit
)
echo [OK] Encryptor module found: utils\hex_encryptor.py

:: Check requirements.txt
if not exist "%PROJECT_DIR%requirements.txt" (
    echo [ERROR] requirements.txt not found
    goto :error_exit
)
echo [OK] requirements.txt found

:: Check config.ini
set "CONFIG_EXISTS=0"
if exist "%PROJECT_DIR%%CONFIG_FILE%" (
    echo [OK] Config file found: %CONFIG_FILE%
    set "CONFIG_EXISTS=1"
) else (
    echo [WARN] Config file not found - will skip: %CONFIG_FILE%
)

:: Check icon
set "ICON_EXISTS=0"
if exist "%ICON_PATH%" (
    echo [OK] Icon file found
    set "ICON_EXISTS=1"
) else (
    echo [WARN] Icon file not found - will use default
)

:: Check signing tools
set "SIGN_AVAILABLE=0"
if exist "%SIGN_TOOLS_DIR%\signtool.exe" (
    if exist "%SIGN_TOOLS_DIR%\makecert.exe" (
        if exist "%SIGN_TOOLS_DIR%\cert2spc.exe" (
            if exist "%SIGN_TOOLS_DIR%\pvk2pfx.exe" (
                echo [OK] Signing tools found
                set "SIGN_AVAILABLE=1"
            )
        )
    )
)

if "%SIGN_AVAILABLE%"=="0" (
    echo [WARN] Signing tools not found in %SIGN_TOOLS_DIR%
    echo [WARN] Executables will be built without digital signature
)

echo.

REM =============================================================================
REM ======== ENVIRONMENT SETUP SECTION =========================================
REM =============================================================================

echo [2/8] Virtual Environment Setup
echo ----------------------------------------

:: Create or reuse virtual environment
if not exist "%PROJECT_DIR%%VENV_NAME%\" (
    echo [INFO] Creating virtual environment: %VENV_NAME%
    python -m venv "%PROJECT_DIR%%VENV_NAME%" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Virtual environment creation failed
        goto :error_exit
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Using existing virtual environment: %VENV_NAME%
)

:: Activate virtual environment
call "%PROJECT_DIR%%VENV_NAME%\Scripts\activate" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    goto :error_exit
)
echo [OK] Virtual environment activated

echo.

REM =============================================================================
REM ======== DEPENDENCY CHECK SECTION ==========================================
REM =============================================================================

echo [3/8] Dependency Verification
echo ----------------------------------------

:: Upgrade pip first
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: Install/Update dependencies
echo [INFO] Installing dependencies from requirements.txt...
pip install -r "%PROJECT_DIR%requirements.txt" --upgrade >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    goto :error_exit
)

:: Install additional dependency for encryptor
echo [INFO] Installing pycryptodome for encryptor...
pip install pycryptodome --upgrade >nul 2>&1

:: Check critical packages
set "PACKAGE_COUNT=0"
set "MISSING_COUNT=0"

echo [INFO] Checking required packages...

pip show pyinstaller >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show pyinstaller ^| findstr "Version:"') do echo [OK] pyinstaller - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] pyinstaller - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show PySide6 >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show PySide6 ^| findstr "Version:"') do echo [OK] PySide6 - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] PySide6 - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show pyserial >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show pyserial ^| findstr "Version:"') do echo [OK] pyserial - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] pyserial - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show pyyaml >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show pyyaml ^| findstr "Version:"') do echo [OK] pyyaml - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] pyyaml - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show cantools >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show cantools ^| findstr "Version:"') do echo [OK] cantools - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] cantools - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show ldfparser >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show ldfparser ^| findstr "Version:"') do echo [OK] ldfparser - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] ldfparser - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

pip show pycryptodome >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pip show pycryptodome ^| findstr "Version:"') do echo [OK] pycryptodome - %%v
    set /a PACKAGE_COUNT+=1
) else (
    echo [ERROR] pycryptodome - NOT INSTALLED
    set /a MISSING_COUNT+=1
)

if %MISSING_COUNT% gtr 0 (
    echo [ERROR] Missing %MISSING_COUNT% required packages
    goto :error_exit
)

echo [OK] All dependencies verified - %PACKAGE_COUNT% packages installed
echo.

REM =============================================================================
REM ======== DIRECTORY SETUP SECTION ===========================================
REM =============================================================================

echo [4/8] Output Directory Setup
echo ----------------------------------------

if not exist "%RELEASE_DIR%" (
    mkdir "%RELEASE_DIR%" >nul 2>&1
    echo [OK] Created release directory
)

if exist "%TARGET_DIR%" (
    echo [INFO] Cleaning existing target directory...
    rmdir /s /q "%TARGET_DIR%" >nul 2>&1
)

mkdir "%TARGET_DIR%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create target directory
    goto :error_exit
)
echo [OK] Target directory ready: version_%VERSION%
echo.

REM =============================================================================
REM ======== PACKAGING SECTION 1 - DIAGNOSTIC TOOL ============================
REM =============================================================================

echo [5/8] Building Diagnostic Tool Executable
echo ============================================================
echo [INFO] Packaging mode: Single EXE file
echo [INFO] Output name: %MAIN_OUTPUT_NAME%.exe
echo.

:: Build PyInstaller command for diagnostic tool
set "PYINSTALLER_CMD=pyinstaller --noconfirm --onefile --noconsole --name=%MAIN_OUTPUT_NAME% --clean"

:: Add icon if exists
if "%ICON_EXISTS%"=="1" (
    set "PYINSTALLER_CMD=%PYINSTALLER_CMD% --icon=%ICON_PATH%"
)

:: Add config file if exists
if "%CONFIG_EXISTS%"=="1" (
    set "PYINSTALLER_CMD=%PYINSTALLER_CMD% --add-data=%CONFIG_FILE%;."
)

:: Add hidden imports and exclusions
set "PYINSTALLER_CMD=%PYINSTALLER_CMD% --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtWidgets --hidden-import=PySide6.QtGui"
set "PYINSTALLER_CMD=%PYINSTALLER_CMD% --hidden-import=serial --hidden-import=yaml --hidden-import=cantools --hidden-import=ldfparser"
set "PYINSTALLER_CMD=%PYINSTALLER_CMD% --exclude-module=pytest --exclude-module=unittest --exclude-module=tkinter --exclude-module=matplotlib"
set "PYINSTALLER_CMD=%PYINSTALLER_CMD% %PROJECT_DIR%%MAIN_SCRIPT%"

echo [INFO] Running PyInstaller for Diagnostic Tool...
%PYINSTALLER_CMD% >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Diagnostic Tool build failed
    echo [INFO] Trying to run PyInstaller with output for debugging...
    %PYINSTALLER_CMD%
    goto :error_exit
)

:: Check if exe was created
if not exist "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe" (
    echo [ERROR] Diagnostic Tool executable not found after build
    goto :error_exit
)

:: Get file size
for %%F in ("%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe") do set "MAIN_FILE_SIZE=%%~zF"
set /a MAIN_FILE_SIZE_MB=%MAIN_FILE_SIZE% / 1048576
echo [OK] Diagnostic Tool build completed successfully
echo [OK] Executable size: %MAIN_FILE_SIZE_MB% MB
echo.

REM =============================================================================
REM ======== PACKAGING SECTION 2 - ENCRYPTOR TOOL =============================
REM =============================================================================

echo [6/8] Building Encryptor Tool Executable
echo ============================================================
echo [INFO] Packaging mode: Single EXE file
echo [INFO] Output name: %ENCRYPTOR_OUTPUT_NAME%.exe
echo.

:: Build PyInstaller command for encryptor tool
set "PYINSTALLER_CMD2=pyinstaller --noconfirm --onefile --windowed --name=%ENCRYPTOR_OUTPUT_NAME% --clean"

:: Add icon if exists
if "%ICON_EXISTS%"=="1" (
    set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --icon=%ICON_PATH%"
)

:: Add hidden imports for PySide6
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=PySide6.QtCore"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=PySide6.QtWidgets"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=PySide6.QtGui"

:: Add hidden imports for Crypto
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=Crypto.Cipher.AES"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=Crypto.Protocol.KDF"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=Crypto.Random"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=Crypto.Util.Padding"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --hidden-import=Crypto.Hash.SHA256"

:: Add utils module path
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --paths=%PROJECT_DIR%"

:: Exclude unnecessary modules
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --exclude-module=pytest --exclude-module=unittest --exclude-module=tkinter --exclude-module=matplotlib"
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% --exclude-module=serial --exclude-module=cantools --exclude-module=ldfparser"

:: Add encryptor script
set "PYINSTALLER_CMD2=%PYINSTALLER_CMD2% %PROJECT_DIR%%ENCRYPTOR_SCRIPT%"

echo [INFO] Running PyInstaller for Encryptor Tool...
%PYINSTALLER_CMD2% >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Encryptor Tool build failed
    echo [INFO] Trying to run PyInstaller with output for debugging...
    %PYINSTALLER_CMD2%
    goto :error_exit
)

:: Check if exe was created
if not exist "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe" (
    echo [ERROR] Encryptor Tool executable not found after build
    goto :error_exit
)

:: Get file size
for %%F in ("%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe") do set "ENCRYPTOR_FILE_SIZE=%%~zF"
set /a ENCRYPTOR_FILE_SIZE_MB=%ENCRYPTOR_FILE_SIZE% / 1048576
echo [OK] Encryptor Tool build completed successfully
echo [OK] Executable size: %ENCRYPTOR_FILE_SIZE_MB% MB
echo.

REM =============================================================================
REM ======== SIGNING SECTION ===================================================
REM =============================================================================

echo [7/8] Digital Signature
echo ============================================================

if "%SIGN_AVAILABLE%"=="0" (
    echo [SKIP] Signing tools not available, skipping signature process
    echo [INFO] Moving executables to target directory without signature...
    
    move /Y "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe" "%TARGET_DIR%\" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to move Diagnostic Tool executable
        goto :error_exit
    )
    echo [OK] Diagnostic Tool deployed to: %TARGET_DIR%
    
    move /Y "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe" "%TARGET_DIR%\" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to move Encryptor Tool executable
        goto :error_exit
    )
    echo [OK] Encryptor Tool deployed to: %TARGET_DIR%
    
    goto :skip_signing
)

echo [INFO] Signing executables with digital certificate...
echo.

:: Change to sign_tools directory
pushd "%SIGN_TOOLS_DIR%"

:: Check if certificate exists
set "CERT_EXISTS=0"
if exist "%CERT_NAME%.pfx" (
    echo [INFO] Using existing certificate: %CERT_NAME%.pfx
    set "CERT_EXISTS=1"
) else (
    echo [INFO] Certificate not found, creating new certificate...
    echo [NOTICE] You will need to enter password "%SIGN_PASS_WORD%" THREE times during certificate creation
    echo.
    
    echo [STEP 1] Creating certificate...
    makecert.exe -sv %CERT_NAME%.pvk -r -n "CN=MAHLE Automotive Technologies" -pe -sky signature %CERT_NAME%.cer
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create certificate
        popd
        goto :error_exit
    )
    echo [SUCCESS] Certificate created
    
    echo [STEP 2] Converting to SPC format...
    cert2spc.exe %CERT_NAME%.cer %CERT_NAME%.spc
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to convert to SPC
        popd
        goto :error_exit
    )
    echo [SUCCESS] SPC file created
    
    echo [STEP 3] Creating PFX file...
    pvk2pfx.exe -pvk %CERT_NAME%.pvk -pi %SIGN_PASS_WORD% -spc %CERT_NAME%.spc -pfx %CERT_NAME%.pfx -f
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create PFX file
        popd
        goto :error_exit
    )
    echo [SUCCESS] PFX file created
    echo.
)

:: Sign Diagnostic Tool
echo [SIGNING] %MAIN_OUTPUT_NAME%.exe...
signtool.exe sign /f %CERT_NAME%.pfx /p %SIGN_PASS_WORD% "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to sign Diagnostic Tool
    popd
    goto :error_exit
)

echo [TIMESTAMP] Adding timestamp to %MAIN_OUTPUT_NAME%.exe...
signtool.exe timestamp /t http://timestamp.comodoca.com/authenticode "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Primary timestamp server failed, trying alternative...
    signtool.exe timestamp /t http://timestamp.digicert.com "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARN] Timestamp failed, but signature is valid
    ) else (
        echo [OK] Timestamp added (alternative server)
    )
) else (
    echo [OK] Timestamp added
)
echo [SUCCESS] %MAIN_OUTPUT_NAME%.exe signed successfully
echo.

:: Sign Encryptor Tool
echo [SIGNING] %ENCRYPTOR_OUTPUT_NAME%.exe...
signtool.exe sign /f %CERT_NAME%.pfx /p %SIGN_PASS_WORD% "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to sign Encryptor Tool
    popd
    goto :error_exit
)

echo [TIMESTAMP] Adding timestamp to %ENCRYPTOR_OUTPUT_NAME%.exe...
signtool.exe timestamp /t http://timestamp.comodoca.com/authenticode "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Primary timestamp server failed, trying alternative...
    signtool.exe timestamp /t http://timestamp.digicert.com "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARN] Timestamp failed, but signature is valid
    ) else (
        echo [OK] Timestamp added (alternative server)
    )
) else (
    echo [OK] Timestamp added
)
echo [SUCCESS] %ENCRYPTOR_OUTPUT_NAME%.exe signed successfully
echo.

:: Return to project directory
popd

echo [SUCCESS] All executables signed successfully
echo.

:: Move signed executables to target directory
echo [INFO] Deploying signed executables...
move /Y "%PROJECT_DIR%dist\%MAIN_OUTPUT_NAME%.exe" "%TARGET_DIR%\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to move Diagnostic Tool executable
    goto :error_exit
)
echo [OK] Signed %MAIN_OUTPUT_NAME%.exe deployed to: %TARGET_DIR%

move /Y "%PROJECT_DIR%dist\%ENCRYPTOR_OUTPUT_NAME%.exe" "%TARGET_DIR%\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to move Encryptor Tool executable
    goto :error_exit
)
echo [OK] Signed %ENCRYPTOR_OUTPUT_NAME%.exe deployed to: %TARGET_DIR%

:skip_signing

:: Create README for encryptor
echo [INFO] Creating documentation...
(
echo HEX Encryptor Tool v%VERSION%
echo ================================
echo.
echo This tool provides encryption and decryption functionality for HEX files.
echo.
echo Features:
echo - AES-256 encryption
echo - HMAC integrity verification
echo - User-friendly GUI interface
echo - Secure file handling
echo.
echo Usage:
echo 1. Run %ENCRYPTOR_OUTPUT_NAME%.exe
echo 2. Select operation mode ^(Encrypt/Decrypt^)
echo 3. Choose security level ^(Basic/Secure^)
echo 4. Browse and select input file
echo 5. Enter password
echo 6. Click button to process
echo.
echo Output files are saved in the same directory as input files.
echo.
echo Build Date: %date% %time%
echo Build Version: %VERSION%
) > "%TARGET_DIR%\Encryptor_README.txt"

if %errorlevel% equ 0 (
    echo [OK] Encryptor_README.txt created
)

echo.

REM =============================================================================
REM ======== CLEANUP SECTION ===================================================
REM =============================================================================

echo [8/8] Cleanup
echo ----------------------------------------

:: Remove build directory
if exist "%PROJECT_DIR%build" (
    rmdir /s /q "%PROJECT_DIR%build" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Removed: build
    )
)

:: Remove dist directory
if exist "%PROJECT_DIR%dist" (
    rmdir /s /q "%PROJECT_DIR%dist" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Removed: dist
    )
)

:: Remove __pycache__
if exist "%PROJECT_DIR%__pycache__" (
    rmdir /s /q "%PROJECT_DIR%__pycache__" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Removed: __pycache__
    )
)

if exist "%PROJECT_DIR%gui\__pycache__" (
    rmdir /s /q "%PROJECT_DIR%gui\__pycache__" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Removed: gui\__pycache__
    )
)

if exist "%PROJECT_DIR%utils\__pycache__" (
    rmdir /s /q "%PROJECT_DIR%utils\__pycache__" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Removed: utils\__pycache__
    )
)

:: Remove spec files
del /q "%PROJECT_DIR%*.spec" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Removed spec files
)

echo [OK] Cleanup completed
echo.

REM =============================================================================
REM ======== COMPLETION SECTION ================================================
REM =============================================================================

echo ============================================================
echo   PACKAGING ^& SIGNING SUCCESSFUL!
echo ============================================================
echo   Version:              %VERSION%
echo.
echo   Tool 1 - Diagnostic Tool:
echo   Output:               %MAIN_OUTPUT_NAME%.exe
echo   Size:                 %MAIN_FILE_SIZE_MB% MB
if "%SIGN_AVAILABLE%"=="1" (
    echo   Signed:               YES
) else (
    echo   Signed:               NO ^(tools not available^)
)
echo.
echo   Tool 2 - Encryptor Tool:
echo   Output:               %ENCRYPTOR_OUTPUT_NAME%.exe
echo   Size:                 %ENCRYPTOR_FILE_SIZE_MB% MB
if "%SIGN_AVAILABLE%"=="1" (
    echo   Signed:               YES
) else (
    echo   Signed:               NO ^(tools not available^)
)
echo.
echo   Location:             %TARGET_DIR%
echo   End Time:             %date% %time%
echo ============================================================
echo.
echo   Both tools have been successfully packaged and deployed!
echo.

:: Open target directory
explorer "%TARGET_DIR%"

pause
exit /b 0

REM =============================================================================
REM ======== ERROR HANDLER =====================================================
REM =============================================================================

:error_exit
echo.
echo ============================================================
echo   PACKAGING FAILED!
echo ============================================================
echo   Please check the error messages above
echo   Time: %date% %time%
echo ============================================================
echo.
pause
exit /b 1
