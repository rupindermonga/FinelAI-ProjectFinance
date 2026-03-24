import google.generativeai as genai
import json
import logging
import os
from pathlib import Path
from typing import List, Optional
from ..models import ColumnConfig, CategoryConfig

logger = logging.getLogger(__name__)

SUPPORTED_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}


def _env_keys() -> list:
    """
    Return all valid Gemini API keys from the environment.
    Reads GEMINI_API_KEYS (comma-separated) first, then falls back to GEMINI_API_KEY.
    """
    multi = os.getenv("GEMINI_API_KEYS", "")
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip() and k.strip() != "your_gemini_api_key_here"]
        if keys:
            return keys
    single = os.getenv("GEMINI_API_KEY", "").strip()
    if single and single != "your_gemini_api_key_here":
        return [single]
    return []


def _env_key() -> str:
    """Return the first valid .env key (kept for backward compat with check_api_key)."""
    keys = _env_keys()
    return keys[0] if keys else ""


def check_api_key(db=None) -> bool:
    """Return True if at least one Gemini API key is available (DB or .env)."""
    if _env_key():
        return True
    if db is not None:
        from ..models import GeminiApiKey
        return db.query(GeminiApiKey).filter(GeminiApiKey.is_active == True).count() > 0
    return False


def build_category_hint(categories: List[CategoryConfig]) -> dict:
    """
    Build allowed-values hints for category / sub_category / sub_division
    to inject into the Gemini prompt.
    Returns a dict with keys: category_hint, sub_category_hint, sub_division_hint
    """
    active = [c for c in categories if c.is_active]
    top_cats = [c for c in active if c.level == "category"]

    if not top_cats:
        return {}

    by_id = {c.id: c for c in active}

    category_names = [c.name for c in top_cats]

    # Build sub-category map: "CategoryName" → ["Sub1", "Sub2", ...]
    sub_cat_map = {}
    all_sub_cats = [c for c in active if c.level == "sub_category"]
    for sc in all_sub_cats:
        parent = by_id.get(sc.parent_id)
        if parent:
            sub_cat_map.setdefault(parent.name, []).append(sc.name)

    # Sub-divisions are direct children of categories (independent of sub-categories)
    sub_div_map = {}         # "CategoryName" → ["Div 1", "Div 2", ...]
    requires_sub_div = set() # category names that REQUIRE a sub-division
    all_sub_divs = [c for c in active if c.level == "sub_division"]
    for sd in all_sub_divs:
        parent = by_id.get(sd.parent_id)
        if parent and parent.level == "category":
            sub_div_map.setdefault(parent.name, []).append(sd.name)

    for cat in top_cats:
        if cat.requires_sub_division:
            requires_sub_div.add(cat.name)

    return {
        "category_names": category_names,
        "sub_cat_map": sub_cat_map,
        "sub_div_map": sub_div_map,
        "requires_sub_div": requires_sub_div,
    }


def build_extraction_prompt(columns: List[ColumnConfig], categories: List[CategoryConfig] = None, corrections: list = None) -> str:
    """Build a dynamic extraction prompt from active column configs, configured categories, and past corrections."""
    active_cols = [c for c in columns if c.is_active and c.field_key != "line_items"]
    line_item_col = next((c for c in columns if c.field_key == "line_items" and c.is_active), None)
    cat_hint = build_category_hint(categories or [])

    # Build the JSON schema description
    fields_desc = {}
    for col in active_cols:
        type_hint = {
            "string": "string or null",
            "number": "number or null",
            "date": "date string YYYY-MM-DD or null",
            "boolean": "true/false or null",
        }.get(col.field_type, "string or null")
        desc = col.field_description or col.field_label

        # Inject allowed values for classification fields — or force null if none configured
        if col.field_key == "category":
            if cat_hint.get("category_names"):
                allowed = ", ".join(cat_hint["category_names"])
                desc = f"Category of this invoice. Must be EXACTLY one of: [{allowed}]. Use null if none applies."
            else:
                desc = "ALWAYS return null — no categories have been configured by the user."
        elif col.field_key == "sub_category":
            if cat_hint.get("sub_cat_map"):
                parts = [f"If category is '{k}': [{', '.join(v)}]" for k, v in cat_hint["sub_cat_map"].items()]
                desc = f"Sub-category within the category. Options — {'; '.join(parts)}. Use null if none applies."
            else:
                desc = "ALWAYS return null — no sub-categories have been configured by the user."
        elif col.field_key == "sub_division":
            sub_div_map = cat_hint.get("sub_div_map", {})
            requires_sub_div = cat_hint.get("requires_sub_div", set())
            if not sub_div_map and not requires_sub_div:
                desc = "ALWAYS return null — no sub-divisions have been configured by the user."
            elif sub_div_map or requires_sub_div:
                parts = []
                for cat_name, divs in sub_div_map.items():
                    req = cat_name in requires_sub_div
                    parts.append(
                        f"If category='{cat_name}': allowed values [{', '.join(divs)}]"
                        + (" — if not found in invoice use exactly 'Not Available'" if req else " — if not found use null")
                    )
                # Categories that require sub-division but have none defined yet
                for cat_name in requires_sub_div - set(sub_div_map.keys()):
                    parts.append(f"If category='{cat_name}': use 'Not Available' if sub-division not stated")
                no_subdiv = [n for n in cat_hint.get("category_names", []) if n not in requires_sub_div]
                if no_subdiv:
                    parts.append(f"If category is one of [{', '.join(no_subdiv)}]: use null (sub-division not applicable)")
                desc = "Sub-division as stated in the invoice. Rules: " + "; ".join(parts) + "."

        fields_desc[col.field_key] = f"{desc} ({type_hint})"

    if line_item_col:
        fields_desc["line_items"] = (
            "Array of ALL line items on the invoice. Each item must include: "
            "{ "
            "line_no (number), "
            "manufacturer (string — brand/maker of the product, null for services), "
            "sku (string — part number or product code), "
            "description (string — full product or service description), "
            "qty (number), "
            "unit (string — UOM: pcs/ea/hr/kg/m/etc.), "
            "unit_price (number — unit rate), "
            "discount_amount (number), "
            "tax_rate (number — percentage), "
            "line_total (number), "
            "sub_division (string — construction trade/CSI division for this line, null if not applicable)"
            " }"
        )

    fields_desc["confidence_score"] = "Your confidence in the overall extraction accuracy, 0.0 to 1.0 (number)"

    prompt = f"""You are an expert invoice data extractor for a construction and procurement management system. Carefully read this invoice document and extract ALL the following fields accurately.

Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

Required JSON fields:
{json.dumps(fields_desc, indent=2)}

Extraction rules:
- Use null for any field you cannot find or are unsure about
- Dates must be YYYY-MM-DD format only (e.g. 2024-01-15)
- Numbers must be pure numeric values — no currency symbols or commas (e.g. 1234.56 not $1,234.56)
- Currency: use ISO 4217 code (CAD, USD, EUR, GBP, etc.)
- tax_total: combine ALL tax types (GST + HST + PST + VAT) into one number
- line_items: extract EVERY line item row, do not skip any
- For the category/sub_category/sub_division fields: use EXACTLY the allowed values listed above; do not invent new values
- confidence_score: 0.9+ = clear invoice, 0.5–0.9 = some ambiguity, <0.5 = poor quality scan
"""

    # Append user corrections as few-shot learning examples
    if corrections:
        lines = []
        for c in corrections:
            vendor_ctx = f" (vendor: {c['vendor_name']})" if c.get("vendor_name") else ""
            lines.append(f"- Field '{c['field_key']}'{vendor_ctx}: DO NOT use \"{c['original_value']}\", the correct value is \"{c['corrected_value']}\"")
        prompt += "\nUser corrections — learn from these past mistakes:\n" + "\n".join(lines) + "\n"

    return prompt


async def extract_invoice_from_file(
    file_path: str,
    columns: List[ColumnConfig],
    categories: List[CategoryConfig] = None,
    api_keys: List[str] = None,
    corrections: list = None,
) -> dict:
    """
    Upload file to Gemini and extract invoice data.
    Tries each key in api_keys (DB-managed, ordered by priority), then the .env
    fallback key.  Raises ValueError only if every key fails.
    """
    prompt = build_extraction_prompt(columns, categories or [], corrections or [])
    ext = Path(file_path).suffix.lower()
    mime_type = SUPPORTED_MIME.get(ext)
    if not mime_type:
        raise ValueError(f"Unsupported file type: {ext}")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Build the list of keys to try: DB keys first, then .env keys as fallback
    keys_to_try: List[str] = list(api_keys or [])
    for env_k in _env_keys():
        if env_k not in keys_to_try:
            keys_to_try.append(env_k)

    if not keys_to_try:
        raise ValueError(
            "No Gemini API keys configured. "
            "Add at least one key in Admin → API Keys (or set GEMINI_API_KEY in .env)."
        )

    import hashlib

    def _key_tag(k: str, idx: int, total: int) -> str:
        h = hashlib.sha256(k.encode()).hexdigest()[:8]
        return f"key {idx}/{total} [sha256:{h}]"

    def _classify_error(e: Exception) -> str:
        """Return a short human-readable reason for the failure."""
        msg = str(e).lower()
        if "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate" in msg:
            return "rate-limited / quota exceeded"
        if "401" in msg or "403" in msg or "api_key" in msg or "invalid" in msg or "permission" in msg:
            return "invalid or unauthorised key"
        return str(e)

    total = len(keys_to_try)
    last_error: Exception = Exception("No keys available")
    for idx, key in enumerate(keys_to_try, start=1):
        tag = _key_tag(key, idx, total)
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)

            uploaded_file = genai.upload_file(path=file_path, mime_type=mime_type)
            try:
                response = model.generate_content(
                    [uploaded_file, prompt],
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
            finally:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception:
                    pass

            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
                raw_text = raw_text.rsplit("```", 1)[0]

            logger.info("Gemini %s succeeded.", tag)
            return json.loads(raw_text)

        except Exception as e:
            last_error = e
            reason = _classify_error(e)
            logger.warning("Gemini %s failed (%s) — trying next key.", tag, reason)
            continue  # try the next key

    raise ValueError(f"All {total} Gemini API key(s) failed. Last error: {last_error}")
