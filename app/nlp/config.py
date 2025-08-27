"""
Configuration for NLP and LLM settings
"""
import os

# LLM Configuration
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_FIRST = os.getenv("LLM_FIRST", "true").lower() == "true"
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# NLP Configuration
ENABLE_FOLLOWUP_LOGIC = os.getenv("ENABLE_FOLLOWUP_LOGIC", "true").lower() == "true"
ENABLE_RULE_FALLBACK = os.getenv("ENABLE_RULE_FALLBACK", "true").lower() == "true"

# Logging Configuration
LOG_LLM_USAGE = os.getenv("LOG_LLM_USAGE", "true").lower() == "true"
LOG_RULE_USAGE = os.getenv("LOG_RULE_USAGE", "true").lower() == "true"

def get_llm_config():
    """Get current LLM configuration as a dict"""
    return {
        "use_openai": USE_OPENAI,
        "model": LLM_MODEL,
        "llm_first": LLM_FIRST,
        "temperature": LLM_TEMPERATURE,
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

def get_nlp_config():
    """Get current NLP configuration as a dict"""
    return {
        "llm_first": LLM_FIRST,
        "enable_followup": ENABLE_FOLLOWUP_LOGIC,
        "enable_rule_fallback": ENABLE_RULE_FALLBACK,
        "log_llm": LOG_LLM_USAGE,
        "log_rules": LOG_RULE_USAGE
    }
