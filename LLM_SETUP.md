# LLM Setup Guide for Slack Chatbot

## Overview
This Slack chatbot now uses LLM (Large Language Model) as the primary method for understanding natural language queries and generating SQL. The system can be configured to use either LLM-first or rule-first approaches.

## Configuration

### Required Environment Variables
```bash
# OpenAI API Key (required for LLM functionality)
OPENAI_API_KEY=your_openai_api_key_here

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### Optional LLM Configuration
```bash
# LLM Model (default: gpt-4o-mini)
LLM_MODEL=gpt-4o-mini

# LLM Priority (default: true - LLM first)
LLM_FIRST=true

# LLM Temperature (default: 0.0 - deterministic)
LLM_TEMPERATURE=0.0

# NLP Features
ENABLE_FOLLOWUP_LOGIC=true
ENABLE_RULE_FALLBACK=true

# Logging
LOG_LLM_USAGE=true
LOG_RULE_USAGE=true
```

## Modes of Operation

### 1. LLM-First Mode (Default: `LLM_FIRST=true`)
- **Primary**: LLM processes all queries first
- **Fallback**: Rules-based system if LLM fails
- **Best for**: Complex queries, natural language understanding
- **Use case**: When you want maximum flexibility and intelligence

### 2. Rule-First Mode (`LLM_FIRST=false`)
- **Primary**: Rules-based system for common queries
- **Fallback**: LLM for complex/unmatched queries
- **Best for**: Fast responses, cost control
- **Use case**: When you want predictable, fast responses for common queries

## How It Works

1. **Query Processing**: User sends natural language query
2. **LLM Analysis**: LLM understands intent and generates SQL
3. **SQL Execution**: Query runs against database
4. **Response Formatting**: Results formatted and sent back
5. **Context Awareness**: Follow-up queries maintain conversation context

## Testing the Configuration

### Check Configuration Status
```bash
curl http://localhost:8000/config
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Example Queries

The LLM can now handle complex queries like:
- "Show me apps with declining revenue over the last quarter"
- "Which countries have the highest user acquisition costs?"
- "Compare iOS vs Android performance metrics"
- "Find apps with unusual spending patterns"

## Troubleshooting

### LLM Not Working
1. Check `OPENAI_API_KEY` is set
2. Verify API key has sufficient credits
3. Check logs for error messages

### Performance Issues
1. Set `LLM_FIRST=false` for faster responses
2. Adjust `LLM_TEMPERATURE` for more/less creative responses
3. Monitor API usage and costs

### Rule Fallback Issues
1. Set `ENABLE_RULE_FALLBACK=true`
2. Check that simple patterns still work
3. Review rule definitions in `agent.py`

## Cost Considerations

- **LLM-First**: Higher cost, better understanding
- **Rule-First**: Lower cost, faster responses
- **Hybrid**: Balance cost and performance

Monitor your OpenAI API usage to optimize costs.
