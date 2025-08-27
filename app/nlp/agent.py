import os, re, json, logging
from typing import Dict, Any, Optional
from .schema_doc import SCHEMA_TEXT
from .prompts import SYSTEM_PROMPT, FEW_SHOTS
from .config import USE_OPENAI, LLM_MODEL, LLM_FIRST, LLM_TEMPERATURE, LOG_LLM_USAGE, LOG_RULE_USAGE
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
OFFTOPIC_PATTERNS = [
    re.compile(r"^\s*(hi|hello|hey|yo|sup|hiya|good (morning|afternoon|evening))\s*!?$", re.I),
    re.compile(r"^\s*(thanks|thank you|thx)\s*!?$", re.I),
    # obvious off-topic words you don't want to handle:
    re.compile(r"\b(joke|weather|time|date|news)\b", re.I),
]

# OpenAI via langchain
try:
    if USE_OPENAI:
        from langchain_openai import ChatOpenAI
except Exception:
    pass

SIMPLE_RULES = [
    (re.compile(r"^\s*help\s*$", re.I),
     {"sql": "", "answer_type": "decline",
      "explanation": "", "assumptions": "",
      "decline_text":
        "I answer analytics about the Rounds app portfolio. Try:\n"
        "• how many apps do we have?\n"
        "• how many android apps do we have?\n"
        "• which country generates the most revenue?\n"
        "• list all iOS apps sorted by their popularity\n"
        "• biggest change in UA spend Jan 2025 vs Dec 2024"
     }),
    (re.compile(r"how\s+many\s+apps\s+do\s+we\s+have\??", re.I),
     {"sql": "SELECT COUNT(DISTINCT app_name) AS app_count FROM app_metrics;", "answer_type": "simple",
      "explanation": "Counts distinct app names.", "assumptions": ""}),
    (re.compile(r"how\s+many\s+android\s+apps", re.I),
     {"sql": "SELECT COUNT(DISTINCT app_name) AS app_count FROM app_metrics WHERE platform='Android';", "answer_type": "simple",
      "explanation": "Counts distinct Android apps.", "assumptions": ""}),
    (re.compile(r"which\s+country\s+generates?\s+the\s+most\s+revenue", re.I),
     {"sql": "SELECT country, SUM(in_app_revenue + ads_revenue) AS total_revenue FROM app_metrics GROUP BY country ORDER BY total_revenue DESC LIMIT 20;",
      "answer_type": "table","explanation":"Ranks countries by total revenue.","assumptions":"Using all available data."}),
    (re.compile(r"list\s+all\s+ios\s+apps.*popularity", re.I),
     {"sql":"SELECT app_name, SUM(installs) AS popularity FROM app_metrics WHERE platform='iOS' AND date >= date('now','-30 day') GROUP BY app_name ORDER BY popularity DESC LIMIT 100;",
      "answer_type":"table","explanation":"Popularity defined as installs over last 30 days.","assumptions":"Popularity=installs(last 30 days)."}),
    (re.compile(r"biggest\s+change\s+in\s+ua\s+spend.*jan\s*2025.*dec\s*2024", re.I),
    {"sql":
    "SELECT app_name, ua_dec_2024_12 AS ua_dec_2024_12, ua_jan_2025_01 AS ua_jan_2025_01, "
    "(ua_jan_2025_01 - ua_dec_2024_12) AS delta, "
    "CASE WHEN ua_dec_2024_12=0 THEN NULL ELSE (ua_jan_2025_01 - ua_dec_2024_12)*1.0/ua_dec_2024_12 END AS pct_change "
    "FROM ( "
    "  SELECT app_name, "
    "         SUM(CASE WHEN date BETWEEN '2024-12-01' AND '2024-12-31' THEN ua_cost ELSE 0 END) AS ua_dec_2024_12, "
    "         SUM(CASE WHEN date BETWEEN '2025-01-01' AND '2025-01-31' THEN ua_cost ELSE 0 END) AS ua_jan_2025_01 "
    "  FROM app_metrics "
    "  GROUP BY app_name "
    ") t "
    "ORDER BY ABS(delta) DESC "
    "LIMIT 100",
    "answer_type":"table","explanation":"Compares monthly UA cost and ranks by absolute change.","assumptions":"Months fixed to Dec 2024 vs Jan 2025."}),
]

def _apply_followup(last_sql: str, user_text: str) -> Optional[str]:
    import re
    m = re.search(r"(ios|android)", user_text, re.I)
    if not m:
        return None
    platform = "iOS" if m.group(1).lower() == "ios" else "Android"

    # 1) normalize the previous SQL (remove trailing semicolon)
    sql = (last_sql or "").strip()
    sql = re.sub(r";\s*$", "", sql)  # drop ONE trailing semicolon safely

    # 2) if a platform filter exists, swap it
    if re.search(r"\bplatform\s*=\s*'(?:iOS|Android)'\b", sql, re.I):
        new_sql = re.sub(
            r"\bplatform\s*=\s*'(?:iOS|Android)'\b",
            f"platform='{platform}'",
            sql,
            flags=re.I,
        )
        return new_sql

    # 3) otherwise, add a platform filter either after WHERE or before GROUP/ORDER/LIMIT/end
    if re.search(r"\bwhere\b", sql, re.I):
        # add AND after WHERE
        new_sql = re.sub(
            r"(\bwhere\b)",
            r"\1 " + f"platform='{platform}' AND ",
            sql,
            flags=re.I,
        )
    else:
        # insert before GROUP BY / ORDER BY / LIMIT / end
        new_sql = re.sub(
            r"(group\s+by|order\s+by|limit|$)",
            f" WHERE platform='{platform}' " + r"\1",
            sql,
            flags=re.I,
        )
    return new_sql

def plan_query(user_text: str, last_plan: Optional[Dict[str,Any]] = None) -> Dict[str,Any]:
    # Follow-up quick pass (keep this for efficiency regardless of mode)
    if last_plan:
        new_sql = _apply_followup(last_plan.get("sql",""), user_text)
        if new_sql:
            return {
                "sql": new_sql,
                "answer_type": last_plan.get("answer_type","table"),
                "explanation": "Follow-up filtered by platform.",
                "assumptions": "Interpreted as a platform filter follow-up."
            }
    
    # LLM as primary method (if available and configured)
    if USE_OPENAI and LLM_FIRST:
        try:
            llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
            logger.info(f"[nlp] Using LLM as primary method with model={LLM_MODEL}")
            
            # Handle follow-up queries with context
            context_info = ""
            if last_plan:
                context_info = f"\n\nPrevious query context:\nSQL: {last_plan.get('sql', '')}\nAnswer type: {last_plan.get('answer_type', '')}\nExplanation: {last_plan.get('explanation', '')}"
            
            shot_strs = []
            for s in FEW_SHOTS:
                shot_strs.append(f"User: {s['user']}\nJSON: {json.dumps(s['json'])}")
            
            prompt = (SYSTEM_PROMPT + "\n\nSCHEMA:\n" + SCHEMA_TEXT + 
                     context_info + "\n\n" + "\n\n".join(shot_strs) +
                     f"\n\nUser: {user_text}\nReturn ONLY the JSON.")
            
            resp = llm.invoke(prompt)
            data = json.loads(resp.content.strip("` ").strip())
            data.setdefault("answer_type", "table")
            data.setdefault("explanation", "")
            data.setdefault("assumptions", "")
            return data
        except Exception as e:
            logger.warning(f"[nlp] LLM primary method failed: {e}")
            # Fall back to rules if LLM fails
    
    # Rules-based approach (either as primary or fallback)
    for pat, plan in SIMPLE_RULES:
        if pat.search(user_text):
            if LLM_FIRST:
                logger.info("[nlp] Using rule-based fallback after LLM failure")
            else:
                logger.info("[nlp] Using rule-based primary method")
            return plan
    
    # Off-topic / small talk: politely decline and steer to analytics
    for pat in OFFTOPIC_PATTERNS:
        if pat.search(user_text or ""):
            return {
                "answer_type": "decline",
                "decline_text": (
                    "I'm focused on the Rounds app portfolio analytics. "
                    "Try questions like:\n"
                    "• how many apps do we have?\n"
                    "• which country generates the most revenue?\n"
                    "• list all iOS apps sorted by popularity\n"
                    "• biggest change in UA spend Jan 2025 vs Dec 2024"
                ),
                "explanation": "",
                "assumptions": "",
            }    
    
    # LLM as fallback (if not used as primary and available)
    if USE_OPENAI and not LLM_FIRST:
        try:
            llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
            logger.info(f"[nlp] Using LLM as fallback method with model={LLM_MODEL}")
            
            shot_strs = []
            for s in FEW_SHOTS:
                shot_strs.append(f"User: {s['user']}\nJSON: {json.dumps(s['json'])}")
            
            prompt = (SYSTEM_PROMPT + "\n\nSCHEMA:\n" + SCHEMA_TEXT + "\n\n" + "\n\n".join(shot_strs) +
                    f"\n\nUser: {user_text}\nReturn ONLY the JSON.")
            
            resp = llm.invoke(prompt)
            data = json.loads(resp.content.strip("` ").strip())
            data.setdefault("answer_type", "table")
            data.setdefault("explanation", "")
            data.setdefault("assumptions", "")
            return data
        except Exception as e:
            logger.warning(f"[nlp] LLM fallback method failed: {e}")
    
    # Last resort generic
    return {
        "sql": "SELECT app_name, platform, date, country, installs, in_app_revenue + ads_revenue AS total_revenue, ua_cost FROM app_metrics ORDER BY date DESC LIMIT 100;",
        "answer_type": "table",
        "explanation": "Generic recent rows.",
        "assumptions": "No specific intent detected; showing recent data."
    }
