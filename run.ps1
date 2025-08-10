$ErrorActionPreference = "Stop"

if (-Not (Test-Path .venv)) {
  python -m venv .venv
}

. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m playwright install
python -c "from src.main import build_team_feeds; build_team_feeds()"