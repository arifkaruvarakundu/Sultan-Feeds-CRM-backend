import io
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _infer_column_kind(dtype: Any) -> str:
    dtype_str = str(dtype)
    if any(k in dtype_str for k in ["int", "float", "decimal", "number"]):
        return "numeric"
    if any(k in dtype_str for k in ["datetime", "date"]):
        return "datetime"
    if any(k in dtype_str for k in ["bool"]):
        return "boolean"
    return "categorical"


def _safe_sample(values: List[Any], limit: int = 5) -> List[Any]:
    result: List[Any] = []
    for v in values[:limit]:
        try:
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                result.append(None)
            else:
                result.append(v)
        except Exception:
            result.append(None)
    return result


def summarize_dataframe(df: pd.DataFrame, max_rows_profile: int = 5000, top_k_categories: int = 10) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "rows": 0,
            "cols": 0,
            "columns": [],
            "notes": ["Empty DataFrame"]
        }

    df_profile = df
    if len(df) > max_rows_profile:
        df_profile = df.head(max_rows_profile)

    columns_meta: List[Dict[str, Any]] = []
    for col in df_profile.columns:
        series = df_profile[col]
        dtype = series.dtype
        kind = _infer_column_kind(dtype)
        non_null_count = int(series.notna().sum())
        null_count = int(series.isna().sum())
        missing_ratio = float(null_count / len(df_profile)) if len(df_profile) else 0.0

        col_meta: Dict[str, Any] = {
            "name": str(col),
            "dtype": str(dtype),
            "kind": kind,
            "non_null": non_null_count,
            "nulls": null_count,
            "missing_ratio": round(missing_ratio, 4),
            "example_values": _safe_sample(series.dropna().unique().tolist(), 5),
        }

        if kind == "numeric":
            try:
                desc = series.describe()
                col_meta["stats"] = {
                    "min": float(desc.get("min", float("nan"))) if pd.notna(desc.get("min")) else None,
                    "max": float(desc.get("max", float("nan"))) if pd.notna(desc.get("max")) else None,
                    "mean": float(desc.get("mean", float("nan"))) if pd.notna(desc.get("mean")) else None,
                    "std": float(desc.get("std", float("nan"))) if pd.notna(desc.get("std")) else None,
                    "p25": float(series.quantile(0.25)) if series.notna().any() else None,
                    "p50": float(series.quantile(0.50)) if series.notna().any() else None,
                    "p75": float(series.quantile(0.75)) if series.notna().any() else None,
                }
            except Exception:
                col_meta["stats"] = {}
        elif kind in ("categorical", "boolean"):
            try:
                vc = series.astype(str).value_counts().head(top_k_categories)
                col_meta["top_values"] = [{"value": k, "count": int(v)} for k, v in vc.items()]
            except Exception:
                col_meta["top_values"] = []

        columns_meta.append(col_meta)

    summary: Dict[str, Any] = {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "columns": columns_meta,
        "sample": df.head(5).to_dict(orient="records"),
    }
    return summary


def build_prompt_from_summary(summary: Dict[str, Any], user_question: Optional[str]) -> str:
    # Limit the size of the summary we pass to the LLM to keep prompt small
    def truncate_text(text: str, max_chars: int = 12000) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1000] + "\n...\n(truncated)"

    schema_preview: List[str] = []
    for col in summary.get("columns", [])[:30]:  # cap schema columns to 30
        line = f"- {col['name']} (kind={col['kind']}, dtype={col['dtype']}, missing={col['missing_ratio']})"
        if "stats" in col and col["stats"]:
            stats = col["stats"]
            line += f" stats(min={stats.get('min')}, max={stats.get('max')}, mean={stats.get('mean')})"
        if "top_values" in col and col["top_values"]:
            top_vals = ", ".join([str(tv["value"]) for tv in col["top_values"][:5]])
            line += f" top_values=[{top_vals}]"
        schema_preview.append(line)

    sample_rows_json = json.dumps(summary.get("sample", [])[:5], ensure_ascii=False)

    user_ask = user_question.strip() if user_question else (
        "Provide a concise analysis: key trends, anomalies, correlations, data quality issues, and business insights."
    )

    prompt = f"""
You are a senior data analyst. You will analyze a dataset provided via a summary of its schema and basic statistics. 
Return a crisp, actionable analysis for a business stakeholder. Avoid overly technical language. Include:
- key trends
- anomalies/outliers
- correlations/segments
- data quality issues
- 3-5 suggested actions or next steps

Dataset overview: rows={summary.get('rows')}, cols={summary.get('cols')}
Schema (first 30 cols):
{chr(10).join(schema_preview)}

Sample rows (up to 5):
{sample_rows_json}

User question / focus:
{user_ask}

Return JSON with keys: insights (list of strings), risks (list of strings), quality_issues (list of strings), suggested_actions (list of strings), and, if relevant, simple_metrics (object of metric -> value). Keep total under 500 words.
"""
    return truncate_text(prompt)


def analyze_csv_bytes(csv_bytes: bytes, user_question: Optional[str] = None, max_rows_profile: int = 5000) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    buffer = io.BytesIO(csv_bytes)
    # Try standard CSV parsing; fallback to more permissive options
    try:
        df = pd.read_csv(buffer, low_memory=False)
    except Exception:
        buffer.seek(0)
        df = pd.read_csv(buffer, low_memory=False, on_bad_lines="skip")

    summary = summarize_dataframe(df, max_rows_profile=max_rows_profile)
    prompt = build_prompt_from_summary(summary, user_question)
    return df, summary, prompt


def analyze_tabular_bytes(
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    user_question: Optional[str] = None,
    max_rows_profile: int = 5000,
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    """
    Parse CSV/XLSX/XLS into a DataFrame, then produce summary and LLM prompt.

    - Uses extension from filename when available.
    - For .xlsx uses openpyxl engine; for .xls uses xlrd engine.
    - Falls back between CSV and Excel readers if detection fails.
    """
    ext = ""
    if filename:
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

    buffer = io.BytesIO(file_bytes)

    def _parse_csv() -> pd.DataFrame:
        try:
            return pd.read_csv(buffer, low_memory=False)
        except Exception:
            buffer.seek(0)
            return pd.read_csv(buffer, low_memory=False, on_bad_lines="skip")

    def _parse_excel() -> pd.DataFrame:
        try:
            buffer.seek(0)
            # Prefer explicit engine by extension where possible
            if ext == ".xlsx":
                return pd.read_excel(buffer, engine="openpyxl")
            if ext == ".xls":
                return pd.read_excel(buffer, engine="xlrd")
            return pd.read_excel(buffer)
        except Exception:
            # Last attempt without engine hint
            buffer.seek(0)
            return pd.read_excel(buffer)

    if ext == ".csv":
        df = _parse_csv()
    elif ext in {".xlsx", ".xls"}:
        df = _parse_excel()
    else:
        # Try CSV first, then Excel
        try:
            df = _parse_csv()
        except Exception:
            df = _parse_excel()

    summary = summarize_dataframe(df, max_rows_profile=max_rows_profile)
    prompt = build_prompt_from_summary(summary, user_question)
    return df, summary, prompt


def invoke_llm(prompt: str, llm: Any) -> Dict[str, Any]:
    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        return {"error": f"LLM call failed: {str(e)}"}

    # Try parse JSON, else fallback to plain text
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        return {"result": obj}
    except Exception:
        return {"result": text}


def _to_primitive(x):
    try:
        if hasattr(x, "item"):
            return _to_primitive(x.item())
    except Exception:
        pass
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        if isinstance(x, float):
            if math.isnan(x) or math.isinf(x):
                return None
            return x
    except Exception:
        pass
    if isinstance(x, (int, str, bool)) or x is None:
        return x
    return str(x)

def json_sanitize(obj):
    if isinstance(obj, dict):
        return {str(_to_primitive(k)): json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_sanitize(v) for v in obj]
    return _to_primitive(obj)