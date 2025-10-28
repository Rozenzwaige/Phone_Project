# bq.py
import os, re
from typing import List, Dict
from google.cloud import bigquery

_bq_client = None

def get_client() -> bigquery.Client:
    """מחזיר מופע BigQuery Client שמבוסס על GOOGLE_APPLICATION_CREDENTIALS."""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client

def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def _safe_ident(name: str) -> str:
    """ולידציה לשמות עמודות (מותר רק אותיות/ספרות/קו תחתון)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        raise RuntimeError(f"Illegal column name: {name!r}")
    return name

def _table_fqdn() -> str:
    """שם טבלה מלא project.dataset.table מתוך ENV."""
    fq = os.getenv("BQ_TABLE_FQ")
    if fq:
        return fq
    project = os.getenv("BQ_PROJECT")
    dataset = os.getenv("BQ_DATASET")
    table   = os.getenv("BQ_TABLE")
    if not (project and dataset and table):
        raise RuntimeError("Missing table config: set BQ_TABLE_FQ or BQ_PROJECT/BQ_DATASET/BQ_TABLE")
    return f"{project}.{dataset}.{table}"

def _location() -> str | None:
    """אזור השאילתה (למשל 'US' / 'EU') אם הוגדר BQ_LOCATION, אחרת None."""
    loc = (os.getenv("BQ_LOCATION") or "").strip()
    return loc or None

def search_contacts(search_type: str, q: str, limit: int = 100) -> List[Dict]:
    """
    חיפוש:
      - name/title: מפרק למילים ודורש AND בין כולן בשדה הרלוונטי.
      - free: AND על כל המילים בטקסט (name/title) + אופציה לחיפוש ספרות בטלפון (OR).
    מחזיר רשימה של dict-ים: [{"name":..., "title":..., "phone":...}, ...]
    """
    q = (q or "").strip()
    if not q:
        return []

    table_fq  = _table_fqdn()
    name_col  = _safe_ident(os.getenv("BQ_COL_NAME",  "name"))
    title_col = _safe_ident(os.getenv("BQ_COL_TITLE", "title"))
    phone_col = _safe_ident(os.getenv("BQ_COL_PHONE", "phone"))

    q_lower   = q.lower()
    words     = [w for w in q_lower.split() if w]
    digits    = _digits_only(q)
    params    = [bigquery.ScalarQueryParameter("lim", "INT64", limit)]

    # === WHERE לפי סוג חיפוש ===
    if search_type == "name":
        clauses = []
        for i, w in enumerate(words) if words else [(0, q_lower)]:
            params.append(bigquery.ScalarQueryParameter(f"w{i}", "STRING", f"%{w}%"))
            clauses.append(f"LOWER(`{name_col}`) LIKE @w{i}")
        where = " AND ".join(clauses)

    elif search_type == "title":
        clauses = []
        for i, w in enumerate(words) if words else [(0, q_lower)]:
            params.append(bigquery.ScalarQueryParameter(f"w{i}", "STRING", f"%{w}%"))
            clauses.append(f"LOWER(`{title_col}`) LIKE @w{i}")
        where = " AND ".join(clauses)

    else:
        # חיפוש חופשי: AND על כל המילים בטקסט (name/title)
        text_clauses = []
        for i, w in enumerate(words) if words else [(0, q_lower)]:
            params.append(bigquery.ScalarQueryParameter(f"w{i}", "STRING", f"%{w}%"))
            text_clauses.append(
                f"(LOWER(`{name_col}`) LIKE @w{i} OR LOWER(`{title_col}`) LIKE @w{i})"
            )
        text_cond = " AND ".join(text_clauses) if text_clauses else "TRUE"

        phone_cond = None
        if len(digits) >= 4:
            params.append(bigquery.ScalarQueryParameter("ph", "STRING", f"%{digits}%"))
            phone_cond = (
                f"REGEXP_REPLACE(CAST(`{phone_col}` AS STRING), r'\\D', '') LIKE @ph"
            )

        # התאמה בטקסט או בטלפון:
        where = f"(({text_cond}) OR ({phone_cond}))" if phone_cond else text_cond
        # אם תרצה שגם טלפון יהיה חובה, החלף ל:
        # where = f"(({text_cond}) AND ({phone_cond}))"

    sql = f"""
      SELECT
        `{name_col}`  AS name,
        `{title_col}` AS title,
        CAST(`{phone_col}` AS STRING) AS phone
      FROM `{table_fq}`
      WHERE {where}
      ORDER BY name
      LIMIT @lim
    """

    job  = get_client().query(
        sql,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
        location=_location(),  # אם הוגדר BQ_LOCATION
    )
    rows = job.result()

    return [{"name": r.get("name"), "title": r.get("title"), "phone": r.get("phone")} for r in rows]
# bq.py (למטה בקובץ)
import datetime as _dt

def log_search_event(user_email: str, query: str, search_type: str, num_results: int,
                     ip: str | None = None, user_agent: str | None = None) -> bool:
    """
    רושם אירוע חיפוש בטבלת BigQuery.
    מחזיר True אם הצליח או אם BQ_LOG_TABLE_FQ לא מוגדר (דלג בשקט).
    """
    table = os.getenv("BQ_LOG_TABLE_FQ")
    if not table:
        return True  # אין טבלת לוגים מוגדרת → לא נכשלים

    row = {
        "ts": _dt.datetime.utcnow(),   # UTC timestamp
        "user_email": user_email or None,
        "query": query or "",
        "search_type": search_type or "",
        "num_results": int(num_results or 0),
        "ip": ip or None,
        "user_agent": user_agent or None,
    }

    client = get_client()
    errors = client.insert_rows_json(table, [row])
    return not bool(errors)
