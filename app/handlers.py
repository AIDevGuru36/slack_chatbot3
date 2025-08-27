from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.fastapi import SlackRequestHandler
from typing import Optional
import os, logging, re, time

from .nlp.agent import plan_query
from .sql.runner import run_sql
from .services.cache import ThreadCache
from .services.csv_export import df_to_csv, upload_csv
from .services.formatting import df_to_markdown_table
from .services.authz import filter_columns
from .obs.tracing import init_tracing

logger = logging.getLogger(__name__)
cache = ThreadCache(ttl_seconds=3600)

def build_app() -> App:
    init_tracing()
    app = App(token=os.getenv("SLACK_BOT_TOKEN"), signing_secret=os.getenv("SLACK_SIGNING_SECRET"))

    @app.event("message")
    def handle_message_events(body, event, say, client, context):
        # ignore edits/bot messages
        if event.get("subtype") or event.get("bot_id"):
            return

        channel = event.get("channel")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        user_id = event.get("user")

        # DM? (channels starting with 'D' are IMs)
        if channel and channel.startswith("D"):
            _handle_query(app, say, channel, thread_ts, user_id, text)
            return

        # Channel message: respond only if the bot is actually mentioned
        bot_user_id = context.get("bot_user_id")
        if not bot_user_id:
            try:
                bot_user_id = client.auth_test()["user_id"]
            except Exception:
                bot_user_id = None

        if bot_user_id and f"<@{bot_user_id}>" in text:
            cleaned = text.replace(f"<@{bot_user_id}>", "").strip()
            _handle_query(app, say, channel, thread_ts, user_id, cleaned)

    @app.event("app_mention")
    def handle_mention(body, say, event, context, client):
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        user_id = event.get("user")
        text = event.get("text","")
        # strip bot mention
        text = " ".join([t for t in text.split() if not t.startswith("<@")])
        _handle_query(app, say, channel, thread_ts, user_id, text)

    @app.command("/bi")
    def slash_bi(ack, body, say):
        ack()
        channel = body["channel_id"]
        thread_ts = body.get("container",{}).get("thread_ts") or body.get("container",{}).get("message_ts")
        text = (body.get("text") or "").strip().lower()
        if text in ("help", "", "examples"):
            say(thread_ts=thread_ts, text=(
                "I answer analytics on the Rounds app portfolio.\nTry:\n"
                "• how many apps do we have?\n"
                "• which country generates the most revenue?\n"
                "• list all iOS apps sorted by popularity\n"
                "• biggest change in UA spend Jan 2025 vs Dec 2024\n"
                "Also: *export this as csv*, *show sql*"
            ))
            return
        _handle_query(app, say, channel, thread_ts, body["user_id"], body.get("text",""))

    @app.command("/export")
    def slash_export(ack: Ack, body, say):
        ack()
        channel = body.get("channel_id")
        thread_ts = body.get("container",{}).get("thread_ts") or body.get("container",{}).get("message_ts")
        last = cache.get(channel, thread_ts) if thread_ts else None
        if not last:
            say(text="No recent result to export in this thread.", thread_ts=thread_ts)
            return
        csv_path = df_to_csv(last["df"], "export")
        upload_csv(app, channel, csv_path, title="export.csv", thread_ts=thread_ts)

    @app.action("export_csv")
    def btn_export(ack: Ack, body, say):
        ack()
        channel = body["channel"]["id"]
        thread_ts = body.get("message",{}).get("thread_ts") or body.get("message",{}).get("ts")
        last = cache.get(channel, thread_ts) if thread_ts else None
        if not last:
            say(text="No recent result to export in this thread.", thread_ts=thread_ts)
            return
        csv_path = df_to_csv(last["df"], "export")
        upload_csv(app, channel, csv_path, title="export.csv", thread_ts=thread_ts)

    @app.action("show_sql")
    def btn_sql(ack: Ack, body, say):
        ack()
        channel = body["channel"]["id"]
        thread_ts = body.get("message",{}).get("thread_ts") or body.get("message",{}).get("ts")
        last = cache.get(channel, thread_ts) if thread_ts else None
        if not last:
            say(text="No SQL cached in this thread.", thread_ts=thread_ts)
            return
        say(text=f"```\n{last['sql']}\n```", thread_ts=thread_ts)

    return app

def _handle_query(app: App, say, channel: str, thread_ts: Optional[str], user_id: str, text: str):
    text_lower = (text or "").strip().lower()

    # --- Text-to-action: Export CSV ---
    EXPORT_PATTERNS = [
        r"\b(export|download|save|dump)\b.*\bcsv\b",
        r"^export\s+csv$",
        r"^export\s+this\s+as\s+csv$",
        r"^download\s+csv$",
    ]
    if any(re.search(p, text_lower) for p in EXPORT_PATTERNS):
        last = _get_last_from_cache(channel, thread_ts)
        if not last:
            say(text="No recent result to export in this thread.", thread_ts=thread_ts)
            return
        csv_path = df_to_csv(last["df"], f"export_{int(time.time())}")
        upload_csv(app, channel, csv_path, title="export.csv", thread_ts=thread_ts)
        return

    # --- Text-to-action: Show SQL ---
    SHOW_SQL_PATTERNS = [
        r"\b(show|display|print|reveal|view|see)\b.*\bsql\b",
        r"\bsql\b.*\b(used|query|statement)\b",
        r"^sql$",
        r"^show\s+sql$",
        r"^show\s+the\s+sql$",
    ]
    if any(re.search(p, text_lower) for p in SHOW_SQL_PATTERNS):
        last = _get_last_from_cache(channel, thread_ts)
        if not last:
            say(text="No SQL cached in this thread.", thread_ts=thread_ts)
            return
        say(text=f"```\n{last['sql']}\n```", thread_ts=thread_ts)
        return
    
    last = cache.get(channel, thread_ts) if thread_ts else None
    plan = plan_query(text, last_plan=last.get("plan") if last else None)
    # 0) Off-topic / small-talk branch: politely decline, no SQL
    if plan.get("answer_type") == "decline":
        say(
            text=plan.get("decline_text") or
                    "I’m focused on analytics for the Rounds app portfolio. Ask me about apps, installs, revenue, UA, countries, or platforms.",
            thread_ts=thread_ts,
            blocks=[
                {"type":"section","text":{"type":"mrkdwn","text": plan.get("decline_text") or
                    "I’m focused on analytics for the Rounds app portfolio. "
                    "Ask me about apps, installs, revenue, UA, countries, or platforms."}}
            ]
        )
        return
    try:
        df = run_sql(plan["sql"])
    except Exception as e:
        say(text=f"Sorry, I couldn't run that query: {e}", thread_ts=thread_ts)
        return

    # authz filter
    df = filter_columns(df, user_id)

    # cache
    cache.set(channel, thread_ts, {"plan": plan, "df": df, "sql": plan["sql"]})
    cache.set(channel, "__last__", {"plan": plan, "df": df, "sql": plan["sql"]})

    if plan.get("answer_type") == "simple" and "app_count" in df.columns and len(df)==1:
        n = int(df.iloc[0]["app_count"])
        say(
            text=f"We currently track *{n}* apps.",
            thread_ts=thread_ts,
            blocks=[
                {"type":"section","text":{"type":"mrkdwn","text":f"We currently track *{n}* apps."}},  #*{n}* apps.\n_{plan.get('explanation','')}_"}}
                {"type":"actions","elements":[
                    {"type":"button","text":{"type":"plain_text","text":"Export CSV"},"action_id":"export_csv"},
                    {"type":"button","text":{"type":"plain_text","text":"Show SQL"},"action_id":"show_sql"}
                ]}
            ]
        )
        return

    table_md = df_to_markdown_table(df)
    summary = plan.get("explanation","")
    assumptions = plan.get("assumptions","")
    say(
        text=summary,
        thread_ts=thread_ts,
        blocks=[
            {"type":"section","text":{"type":"mrkdwn","text":f"*Result*\n{summary}\n_{assumptions}_"}},
            {"type":"section","text":{"type":"mrkdwn","text":table_md}},
            {"type":"actions","elements":[
                {"type":"button","text":{"type":"plain_text","text":"Export CSV"},"action_id":"export_csv"},
                {"type":"button","text":{"type":"plain_text","text":"Show SQL"},"action_id":"show_sql"}
            ]}
        ]
    )

def _get_last_from_cache(channel, thread_ts):
    last = cache.get(channel, thread_ts) if thread_ts else None
    if not last:
        last = cache.get(channel, "__last__")  # channel-level fallback
    return last