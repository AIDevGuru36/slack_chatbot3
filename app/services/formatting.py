import pandas as pd

def _fmt_cell(val, col):
    # ints -> 1,234 ; floats -> 12.34 ; pct columns -> 12.3%
    try:
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, int):
            return f"{val:,}"
        if isinstance(val, float):
            if "pct" in col.lower() or "percent" in col.lower():
                return f"{val*100:.1f}%"
            return f"{val:.2f}"
    except Exception:
        pass
    return str(val)

def df_to_markdown_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    df_disp = df.head(max_rows)
    headers = list(df_disp.columns)
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"]*len(headers)) + " |")
    for _, row in df_disp.iterrows():
        vals = []
        for col, val in zip(headers, row.tolist()):
            vals.append(_fmt_cell(val, col))
        lines.append("| " + " | ".join(vals) + " |")
    if len(df) > max_rows:
        lines.append(f"_…plus {len(df)-max_rows} more rows_")
    return "\n".join(lines)