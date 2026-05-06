where git >nul 2>&1 && if exist .git\NUL git pull
if not exist .venv (python -m venv .venv)
.venv\Scripts\python -m pip install -r requirements.txt -U
.venv\Scripts\python -m ninova_fetcher %*
pause
