import os, logging
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .handlers import build_app

logging.basicConfig(level=logging.INFO)
load_dotenv(override=True)

def mask(t): return (t[:6] + "..." + t[-4:]) if t else "MISSING"

print("OPENAI =", "set" if os.getenv("OPENAI_API_KEY") else "MISSING")
print("LANGSMITH =", "set" if os.getenv("LANGCHAIN_API_KEY") else "MISSING")
print("LLM_MODEL =", os.getenv("LLM_MODEL", "gpt-4o-mini"))

def main():
    app = build_app()
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token or not app_token.startswith("xapp-1-"):
        raise RuntimeError("Bad/missing SLACK_APP_TOKEN (xapp-1-...)")
    print("BOT =", mask(os.getenv("SLACK_BOT_TOKEN")), " APP =", mask(app_token))
    print("⚡ Running Slack bot in Socket Mode...")
    SocketModeHandler(app, app_token).start()

if __name__ == "__main__":
    main()
