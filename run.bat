if not exist .venv (python -m venv .venv)
.venv\Scripts\python -m install -r requirements.txt -U
.venv\Scripts\python -m ninova_fetcher
pause
