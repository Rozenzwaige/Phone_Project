# bq.py
import os, re
from typing import List, Dict
from google.cloud import bigquery

_bq_client = None  # <- שם משתנה אחר

def get_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()  # דורש GOOGLE_APPLICATION_CREDENTIALS תקין
    return _bq_client

def _digits_only(s: str) -> str:
    import re
    return re.sub(r"\D+", "", s or "")

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
    q = (q or "").strip()
    if not q:
        return []

    table    = _table_fqdn()
    q_lower  = q.lower()
    q_digits = _digits_only(q)

    params = [
        bigquery.ScalarQueryParameter("q",  "STRING", q_lower),
        bigquery.ScalarQueryParameter("qd", "STRING", q_digits),
        bigquery.ScalarQueryParameter("lim","INT64",  limit),
    ]

    if search_type == "name":
        where = "LOWER(name) LIKE CONCAT('%', @q, '%')"
    elif search_type == "title":
        where = "LOWER(title) LIKE CONCAT('%', @q, '%')"
    else:
        where = """
          (LOWER(name)  LIKE CONCAT('%', @q, '%')
           OR LOWER(title) LIKE CONCAT('%', @q, '%')
           OR REGEXP_REPLACE(CAST(phone AS STRING), r'\\D', '') LIKE CONCAT('%', @qd, '%'))
        """

    sql = f"""
      SELECT
        name,
        title,
        CAST(phone AS STRING) AS phone
      FROM `{table}`
      WHERE {where}
      ORDER BY name
      LIMIT @lim
    """

    job  = get_client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    rows = job.result()

    out = []
    for r in rows:
        out.append({"name": r.get("name"), "title": r.get("title"), "phone": r.get("phone")})
    return out
