import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from slack_bolt.adapter.fastapi import SlackRequestHandler
from .handlers import build_app
from .nlp.config import get_llm_config, get_nlp_config

load_dotenv()

app = FastAPI(title="Rounds Slack BI Bot")
bolt_app = build_app()
handler = SlackRequestHandler(bolt_app)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/config")
async def config():
    """Show current LLM and NLP configuration"""
    return {
        "llm": get_llm_config(),
        "nlp": get_nlp_config()
    }

@app.post("/slack/events")
async def slack_events(request: Request):
    return await handler.handle(request)
