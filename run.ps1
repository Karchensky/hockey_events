$ErrorActionPreference = "Stop"

if (-Not (Test-Path .venv)) {
  python -m venv .venv
}

. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m playwright install
python -m src.main