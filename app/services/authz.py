import os
from typing import Dict

# Simple RBAC: comma-separated list of admin user IDs (U123...)
ADMINS = set(filter(None, (os.getenv("ADMIN_USER_IDS","").split(","))))

def is_admin(user_id: str) -> bool:
    return user_id in ADMINS

# Column-level access control (example: hide ua_cost from non-admins)
def filter_columns(df, user_id: str):
    if is_admin(user_id):
        return df
    if "ua_cost" in df.columns:
        return df.drop(columns=["ua_cost"])
    return df
