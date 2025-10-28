# bq.py
import os, re
from typing import List, Dict
from google.cloud import bigquery

_bq_client = None

def get_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()  # משתמש ב-GOOGLE_APPLICATION_CREDENTIALS
    return _bq_client

def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def _safe_ident(name: str) -> str:
    """רק אותיות/ספרות/קו תחתי לשמות עמודות; אחרת נזרוק שגיאה ברורה."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        raise RuntimeError(f"Illegal column name: {name!r}")
    return name

def _table_fqdn() -> str:
    fq = os.getenv("BQ_TABLE_FQ")
    if fq:
        return fq
    project = os.getenv("BQ_PROJECT")
    dataset = os.getenv("BQ_DATASET")
    table   = os.getenv("BQ_TABLE")
    if not (project and dataset and table):
        raise RuntimeError("Missing table config: set BQ_TABLE_FQ or BQ_PROJECT/BQ_DATASET/BQ_TABLE")
    return f"{project}.{dataset}.{table}"

def search_contacts(search_type: str, q: str, limit: int = 100) -> List[Dict]:
    """
    מחזיר: [{"name":..., "title":..., "phone":...}, ...]
    """
    q = (q or "").strip()
    if not q:
        return []

    table_fq = _table_fqdn()

    # שמות עמודות ניתנים לשינוי דרך ENV
    name_col  = _safe_ident(os.getenv("BQ_COL_NAME",  "name"))
    title_col = _safe_ident(os.getenv("BQ_COL_TITLE", "title"))
    phone_col = _safe_ident(os.getenv("BQ_COL_PHONE", "phone"))

    q_lower  = q.lower()
    q_digits = _digits_only(q)

    params = [
        bigquery.ScalarQueryParameter("q",  "STRING", q_lower),
        bigquery.ScalarQueryParameter("qd", "STRING", q_digits),
        bigquery.ScalarQueryParameter("lim","INT64",  limit),
    ]

    if search_type == "name":
        where = f"LOWER(`{name_col}`) LIKE CONCAT('%', @q, '%')"
    elif search_type == "title":
        where = f"LOWER(`{title_col}`) LIKE CONCAT('%', @q, '%')"
    else:
        where = (
            f"LOWER(`{name_col}`) LIKE CONCAT('%', @q, '%') OR "
            f"LOWER(`{title_col}`) LIKE CONCAT('%', @q, '%') OR "
            f"REGEXP_REPLACE(CAST(`{phone_col}` AS STRING), r'\\D', '') LIKE CONCAT('%', @qd, '%')"
        )

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

    job  = get_client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    rows = job.result()

    out: List[Dict] = []
    for r in rows:
        out.append({"name": r.get("name"), "title": r.get("title"), "phone": r.get("phone")})
    return out
