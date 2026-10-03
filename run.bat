where git >nul 2>&1 && if exist .git\NUL git pull
if not exist .venv (python -m venv .venv)

if exist .venv\bin (
    set "VENV_BIN=.venv\bin"
) else (
    set "VENV_BIN=.venv\Scripts"
)

"%VENV_BIN%\python" -m pip install -r requirements.txt -U
"%VENV_BIN%\python" -m ninova_fetcher %*
pause
