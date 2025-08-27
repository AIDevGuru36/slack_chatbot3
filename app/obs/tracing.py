import os

def init_tracing():
    # Optional LangSmith tracing
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2","true")
        if not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "Rounds-Slack-BI-Bot"
        print("[obs] LangSmith tracing enabled")
    else:
        print("[obs] LangSmith tracing disabled (no LANGCHAIN_API_KEY)")
