# bq.py
import os, re
from typing import List, Dict
from google.cloud import bigquery

_client = None

def _client() -> bigquery.Client:
    global _client
    if _client is None:
        # מסתמך על GOOGLE_APPLICATION_CREDENTIALS מה-ENV
        _client = bigquery.Client()
    return _client

def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def _table_fqdn() -> str:
    # עדיפות לביטוי המלא אם הוגדר
    fq = os.getenv("BQ_TABLE_FQ")
    if fq:
        return fq
    # אחרת – בניה מנתונים חלקיים
    project = os.getenv("BQ_PROJECT")
    dataset = os.getenv("BQ_DATASET")
    table   = os.getenv("BQ_TABLE")
    if not (project and dataset and table):
        raise RuntimeError(
            "Missing table config: set BQ_TABLE_FQ or BQ_PROJECT/BQ_DATASET/BQ_TABLE"
        )
    return f"{project}.{dataset}.{table}"

def search_contacts(search_type: str, q: str, limit: int = 100) -> List[Dict]:
    """
    מחזיר רשימת רשומות: [{name, title, phone}, ...]
    search_type: free | name | title
    """
    q = (q or "").strip()
    if not q:
        return []

    table = _table_fqdn()
    q_lower = q.lower()
    q_digits = _digits_only(q)

    params = [
        bigquery.ScalarQueryParameter("q", "STRING", q_lower),
        bigquery.ScalarQueryParameter("qd", "STRING", q_digits),
        bigquery.ScalarQueryParameter("lim", "INT64", limit),
    ]

    if search_type == "name":
        where = "LOWER(name) LIKE CONCAT('%', @q, '%')"
    elif search_type == "title":
        where = "LOWER(title) LIKE CONCAT('%', @q, '%')"
    else:  # free
        where = """
            (LOWER(name)  LIKE CONCAT('%', @q, '%')
             OR LOWER(title) LIKE CONCAT('%', @q, '%')
             OR REGEXP_REPLACE(CAST(phone AS STRING), r'\\D', '') LIKE CONCAT('%', @qd, '%'))
        """

    query = f"""
    SELECT
      name,
      title,
      CAST(phone AS STRING) AS phone
    FROM `{table}`
    WHERE {where}
    ORDER BY name
    LIMIT @lim
    """

    job = _client().query(
        query,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
    )
    rows = job.result()

    out = []
    for r in rows:
        # שדות לפי שמות העמודות בטבלה
        out.append({
            "name":  r["name"]  if "name"  in r else None,
            "title": r["title"] if "title" in r else None,
            "phone": r["phone"] if "phone" in r else None,
        })
    return out
