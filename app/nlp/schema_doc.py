SCHEMA_TEXT = """
You can query a single table: app_metrics

Columns:
  - app_name (TEXT): Name of the app (e.g., Paint Pro, Countdown, FitTrack, NoteMaster, BudgetBuddy)
  - platform (TEXT): 'iOS' or 'Android'
  - date (DATE TEXT 'YYYY-MM-DD')
  - country (TEXT): e.g., US, GB, DE, FR, CA, BR, IN, AU
  - installs (INTEGER)
  - in_app_revenue (REAL)
  - ads_revenue (REAL)
  - ua_cost (REAL)

Common derived fields:
  - total_revenue = in_app_revenue + ads_revenue
"""
