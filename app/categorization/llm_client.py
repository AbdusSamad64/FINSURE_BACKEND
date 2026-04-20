import json
import re
import time
import textwrap
import logging
import random
from typing import List, Dict, Optional

# SDKs
import google.generativeai as genai
from groq import Groq

from app.categorization.config import config

logger = logging.getLogger(__name__)

def _build_prompt(batch: List[Dict], valid_categories: List[str]) -> str:
    """
    Build a prompt asking the LLM to categorize a batch of transactions.
    batch: list of dicts with keys trxID, description, tx_type, amount
    """
    categories_str = "\n".join(f"  - {c}" for c in valid_categories)
    transactions_str = "\n".join(
        f'  {{"trxID": {r["trxID"]}, "description": "{r["description"]}", '
        f'"type": "{r["tx_type"]}", "amount": {r["amount"]}}}'
        for r in batch
    )

    prompt = textwrap.dedent(f"""
        You are a financial transaction categorizer for a Pakistani freelancer's bank account.
        Transactions can be from local clients, international freelance platforms (Payoneer,
        Upwork, Fiverr, Wise, PayPal, etc.), utility companies, banks, or mobile wallets
        (JazzCash, Easypaisa, Raast).

        Categorize each transaction into EXACTLY one of these categories:
{categories_str}

        Category Definitions:
        - "Freelance Income": money received from freelance platforms or foreign clients.
        - "Salary": regular monthly pay from a local employer.
        - "Refund": reversal, cashback, or money returned.
        - "Subscriptions": recurring SaaS, streaming, or software payments.
        - "Bank Service Charges": fees, taxes, penalties levied by the bank.
        - "Utilities and Bills": electricity, gas, water, internet, mobile, insurance bills.
        - "Withdrawal": ATM or counter cash withdrawal.
        - "Personal Transfer": IBFT, Raast, JazzCash, Easypaisa, or any person-to-person transfer.

        Transactions (JSON array):
        [
{transactions_str}
        ]

        Respond ONLY with a valid JSON array (no markdown, no explanation):
        [{{"trxID": <int>, "category": "<category>"}}, ...]
    """).strip()
    return prompt

def _call_gemini(prompt: str) -> str:
    """Raw call to Gemini."""
    if not config.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)
    response = model.generate_content(prompt)
    if not response or not response.text:
        raise RuntimeError("Empty response from Gemini")
    return response.text.strip()

def _call_groq(prompt: str) -> str:
    """Raw call to Groq."""
    if not config.groq_api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    client = Groq(api_key=config.groq_api_key)
    response = client.chat.completions.create(
        model=config.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    if not response or not response.choices:
        raise RuntimeError("Empty response from Groq")
    return response.choices[0].message.content.strip()

def _parse_llm_response(text: str) -> List[Dict]:
    """Extract JSON from potential markdown fences."""
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}. Raw text: {text}")
        raise

def llm_categorize_batch(
    batch: List[Dict], 
    valid_categories_list: List[str],
    cat_name_to_id: Dict[str, int]
) -> List[Dict]:
    """
    Sends a batch to LLM (Gemini primary, Groq fallback).
    Returns list of dicts: {"trxID": int, "categID": int, "categorized_by": str}
    """
    prompt = _build_prompt(batch, valid_categories_list)
    
    primary = config.default_llm
    secondary = "groq" if primary == "gemini" else "gemini"
    
    clients = {
        "gemini": _call_gemini,
        "groq": _call_groq
    }

    # Attempt with Primary
    for attempt in range(1, config.max_retries + 1):
        try:
            logger.info(f"[categorizer] LLM={primary} attempt={attempt}/{config.max_retries}")
            raw_text = clients[primary](prompt)
            parsed = _parse_llm_response(raw_text)
            return _format_results(parsed, cat_name_to_id, f"llm-{primary}")
        except Exception as e:
            # Check if it's a rate limit error (using string matching to avoid heavy imports if possible)
            err_msg = str(e).lower()
            if "exhausted" in err_msg or "rate limit" in err_msg or "429" in err_msg:
                logger.warning(f"[categorizer] {primary} rate limited on attempt {attempt}")
            else:
                logger.warning(f"[categorizer] {primary} failed: {e}")
                
            if attempt < config.max_retries:
                # Exponential backoff: base * 2^(attempt-1) + jitter
                # e.g. 10s -> 20s -> 40s
                wait_time = config.retry_wait_sec * (2 ** (attempt - 1))
                jitter = random.uniform(0, 1) * 2 # up to 2s jitter
                total_wait = wait_time + jitter
                logger.info(f"[categorizer] Retrying in {total_wait:.2f}s...")
                time.sleep(total_wait)
    
    # Fallback to Secondary
    logger.info(f"[categorizer] FALLBACK from {primary} to {secondary}")

    try:
        raw_text = clients[secondary](prompt)
        parsed = _parse_llm_response(raw_text)
        return _format_results(parsed, cat_name_to_id, f"llm-{secondary}")
    except Exception as e:
        logger.error(f"[categorizer] Both LLMs failed for batch: {e}")
        return []

def _format_results(parsed_json: List[Dict], cat_name_to_id: Dict[str, int], method: str) -> List[Dict]:
    results = []
    # Normalize category names for mapping
    normalized_map = {name.strip().lower(): id for name, id in cat_name_to_id.items()}
    
    for item in parsed_json:
        trx_id = item.get("trxID")
        cat_name = item.get("category", "").strip().lower()
        
        if trx_id and cat_name in normalized_map:
            results.append({
                "trxID": trx_id,
                "categID": normalized_map[cat_name],
                "categorized_by": method
            })
        else:
            logger.warning(f"[categorizer] Skipping invalid LLM result: {item}")
    return results
