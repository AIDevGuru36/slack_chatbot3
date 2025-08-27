import os
from pathlib import Path
import pandas as pd
from slack_bolt import App

def ensure_exports_dir() -> Path:
    p = Path("data/exports")
    p.mkdir(parents=True, exist_ok=True)
    return p

def df_to_csv(df: pd.DataFrame, basename: str) -> str:
    exports = ensure_exports_dir()
    path = exports / f"{basename}.csv"
    df.to_csv(path, index=False)
    return str(path)

def upload_csv(app: App, channel: str, file_path: str, title: str = "export.csv", thread_ts: str = None):
    with open(file_path, "rb") as f:
        app.client.files_upload_v2(
            channels=channel,
            file=f,
            filename=os.path.basename(file_path),
            title=title,
            thread_ts=thread_ts
        )
