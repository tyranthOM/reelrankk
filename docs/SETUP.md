# ReelRank Setup

## Steps
1. Install stuff (run from root `reelrank/` folder):
   pip install -r requirements.txt

2. Build DB:
   python app/db/seed_data.py

3. Run server (from root folder, NOT inside app/):
   python -m uvicorn app.main:app --reload

4. Open browser:
   http://127.0.0.1:8000

## Notes
- No Docker needed. Pure Python + SQLite.
- Python 3.10+ required.
- Stop server: CTRL+C
- Always run commands from root `reelrank/` folder, not from inside subfolders.