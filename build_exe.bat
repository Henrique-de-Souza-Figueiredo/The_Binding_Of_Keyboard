@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERRO: .venv nao encontrada.
    echo Crie a venv e instale as dependencias antes de gerar o exe.
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm TheBindingOfKeyboard.spec
if errorlevel 1 exit /b 1

echo.
echo Executavel gerado em:
echo dist\The Binding Of Keyboard.exe
