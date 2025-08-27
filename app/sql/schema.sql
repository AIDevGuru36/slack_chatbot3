CREATE TABLE IF NOT EXISTS app_metrics (
  app_name TEXT NOT NULL,
  platform TEXT NOT NULL CHECK(platform IN ('iOS','Android')),
  date TEXT NOT NULL, -- ISO YYYY-MM-DD
  country TEXT NOT NULL,
  installs INTEGER NOT NULL,
  in_app_revenue REAL NOT NULL,
  ads_revenue REAL NOT NULL,
  ua_cost REAL NOT NULL
);
