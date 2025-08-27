import os, logging
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .handlers import build_app

logging.basicConfig(level=logging.INFO)
load_dotenv()

def main():
    app = build_app()
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN (App-level token) is required for Socket Mode. Check .env")
    handler = SocketModeHandler(app, app_token)
    print("⚡ Running Slack bot in Socket Mode...")
    handler.start()

if __name__ == "__main__":
    main()
