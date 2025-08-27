import os, random, sqlite3, math
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

DB_PATH = os.getenv("DB_PATH", "data/rounds.db")
SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")

APPS = [
    ("Paint Pro", "Android"),
    ("Paint Pro", "iOS"),
    ("Countdown", "Android"),
    ("Countdown", "iOS"),
    ("FitTrack", "Android"),
    ("FitTrack", "iOS"),
    ("NoteMaster", "Android"),
    ("NoteMaster", "iOS"),
    ("BudgetBuddy", "Android"),
    ("BudgetBuddy", "iOS"),
    ("QR Scaner", "iOS"),
    ("TimerX", "Android"),
]

COUNTRIES = ["US","GB","DE","FR","CA","BR","IN","AU"]

def ensure_db():
    Path("data").mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    with con:
        con.executescript(SCHEMA)
    con.close()

def seasonality(day_idx):
    # Weekly seasonality + mild monthly trend
    return 1.0 + 0.15*math.sin(2*math.pi*(day_idx%7)/7.0) + 0.05*math.sin(2*math.pi*(day_idx%30)/30.0)

def base_installs(app, platform):
    base_map = {
        "Paint Pro": 220,
        "Countdown": 180,
        "FitTrack": 260,
        "NoteMaster": 200,
        "BudgetBuddy": 240,
        "QR Scaner": 190,
        "TimerX": 210,
    }
    base = base_map.get(app, 200) #default baseline if unknown
    if platform == "iOS":
        base = int(base * 0.9)
    return base

def run():
    ensure_db()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM app_metrics")
    start = date(2024, 12, 1)
    end = date(2025, 8, 15)
    all_rows = []
    day_idx = 0
    random.seed(42)

    for app_name, platform in APPS:
        for c in COUNTRIES:
            d = start
            while d <= end:
                s = seasonality(day_idx)
                inst = max(0, int(base_installs(app_name, platform) * s * random.uniform(0.8, 1.3)))
                # revenue mix
                iap = round(inst * random.uniform(0.05, 0.18), 2)
                ads = round(inst * random.uniform(0.02, 0.12), 2)
                ua = round(inst * random.uniform(0.02, 0.16), 2)
                all_rows.append((app_name, platform, d.isoformat(), c, inst, iap, ads, ua))
                d += timedelta(days=1)
                day_idx += 1

    cur.executemany(
        "INSERT INTO app_metrics (app_name, platform, date, country, installs, in_app_revenue, ads_revenue, ua_cost) VALUES (?,?,?,?,?,?,?,?)",
        all_rows
    )
    con.commit()
    con.close()
    print(f"Seeded {len(all_rows)} rows into {DB_PATH}")

if __name__ == "__main__":
    load_dotenv()
    run()
