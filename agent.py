"""AI Bug Triage Agent using Google Gemini."""

import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


BASE = Path(__file__).parent
BUGS_FILE = BASE / "data" / "bugs.csv"
TICKETS_FILE = BASE / "data" / "tickets.csv"

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "on",
    "and", "or", "se", "ka", "ki", "ke", "ho", "hai",
    "nahi", "par", "mein", "bhi", "kar", "karne", "aur",
    "ye", "wo"
}
TICKET_FIELDS = [
    "ticket_id",
    "created_at",
    "title",
    "severity",
    "priority",
    "module",
    "steps_to_reproduce",
    "expected",
    "actual"
]
MODULES = [
    "Login",
    "Signup",
    "Search",
    "Cart",
    "Checkout",
    "Order Tracking",
    "Profile",
    "General"
]

SEVERITIES = [
    "Critical",
    "High",
    "Medium",
    "Low"
]



SYSTEM_PROMPT = """
You are a senior QA engineer doing bug triage for an e-commerce website.

Bug reports may be written in English, Hindi or Hinglish.

Always return the final output fields in English.

Return ONLY valid JSON with exactly these fields:

{
  "is_duplicate": true or false,
  "duplicate_of_id": "existing bug id or empty string",
  "severity": "Critical|High|Medium|Low",
  "priority": "P1|P2|P3",
  "module": "Login|Signup|Search|Cart|Checkout|Order Tracking|Profile|General",
  "clean_title": "short bug title",
  "steps_to_reproduce": "steps if available",
  "expected": "expected behavior",
  "actual": "actual behavior",
  "reasoning": "2-3 sentence explanation"
}

Severity guide:
- Critical: payment/money loss, login impossible, data loss, security issue, app unusable
- High: major feature broken, no workaround
- Medium: feature partly broken, workaround exists
- Low: cosmetic, typo, minor UI

Priority:
- P1 = fix now
- P2 = this sprint
- P3 = backlog
"""


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY nahi mila. .env file mein Gemini API key add karo."
        )

    return genai.Client(api_key=api_key)


def search_similar_bugs(keywords: str):
    words = {
        w
        for w in re.findall(r"\w+", keywords.lower())
        if w not in STOPWORDS
    }

    matches = []

    with open(BUGS_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = (
                f"{row['title']} "
                f"{row['description']} "
                f"{row['module']}"
            ).lower()

            score = sum(1 for w in words if w in text)

            if score:
                matches.append({
                    **row,
                    "match_score": score
                })

    matches.sort(
        key=lambda r: r["match_score"],
        reverse=True
    )

    return matches[:3] or "No similar bugs found"


def create_ticket(dry_run=False, **fields):
    if dry_run:
        return "DRY RUN: ticket not saved"

    exists = TICKETS_FILE.exists()

    if exists:
        with open(TICKETS_FILE, encoding="utf-8") as f:
            count = sum(1 for _ in f) - 1
    else:
        count = 0

    row = {
        "ticket_id": f"TKT-{count + 1:03d}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        **fields
    }

    with open(
        TICKETS_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=TICKET_FIELDS,
            extrasaction="ignore"
        )

        if not exists:
            writer.writeheader()

        writer.writerow(row)

    return f"Ticket created: {row['ticket_id']}"


def triage(
    bug_report: str,
    create_tickets: bool = True,
    max_steps: int = 8
) -> dict:

    client = get_client()

    initial_words = " ".join(
        re.findall(r"\w+", bug_report.lower())
    )

    similar_bugs = search_similar_bugs(initial_words)

    context = f"""
BUG REPORT:

{bug_report}

POSSIBLE EXISTING BUGS:

{json.dumps(
    similar_bugs,
    ensure_ascii=False,
    indent=2
)}

Analyze the bug and determine whether it is a duplicate.
"""

    response = None

    # Retry Gemini request when temporary 503 occurs
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=context,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            break

        except Exception as e:
            error_text = str(e)

            if "503" in error_text or "UNAVAILABLE" in error_text:
                if attempt < 2:
                    time.sleep(5)
                    continue

            return {
                "decision": None,
                "log": [],
                "error": f"Gemini API error: {e}"
            }

    if response is None:
        return {
            "decision": None,
            "log": [],
            "error": "Gemini response nahi mila."
        }

    raw = response.text.strip()

    try:
        decision = json.loads(raw)

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            raw,
            re.DOTALL
        )

        if not match:
            return {
                "decision": None,
                "log": [],
                "error": "Gemini ne valid JSON response nahi diya."
            }

        try:
            decision = json.loads(match.group(0))

        except Exception as e:
            return {
                "decision": None,
                "log": [],
                "error": f"Gemini response parse nahi hua: {e}"
            }

    decision.setdefault("duplicate_of_id", "")
    decision.setdefault("steps_to_reproduce", "")
    decision.setdefault("expected", "")
    decision.setdefault("actual", "")
    decision.setdefault("reasoning", "")

    log = [
        {
            "tool": "search_similar_bugs",
            "input": {
                "keywords": initial_words
            },
            "output": similar_bugs
        }
    ]

    # Create ticket only when bug is not duplicate
    if not decision.get("is_duplicate", False):

        ticket_result = create_ticket(
            dry_run=not create_tickets,
            title=decision.get(
                "clean_title",
                "Untitled bug"
            ),
            severity=decision.get(
                "severity",
                "Medium"
            ),
            priority=decision.get(
                "priority",
                "P2"
            ),
            module=decision.get(
                "module",
                "General"
            ),
            steps_to_reproduce=decision.get(
                "steps_to_reproduce",
                ""
            ),
            expected=decision.get(
                "expected",
                ""
            ),
            actual=decision.get(
                "actual",
                ""
            )
        )

        log.append({
            "tool": "create_ticket",
            "input": decision,
            "output": ticket_result
        })

    log.append({
        "tool": "submit_triage",
        "input": decision,
        "output": "Recorded"
    })

    return {
        "decision": decision,
        "log": log,
        "error": None
    }


if __name__ == "__main__":

    print(
        "Bug report likho "
        "(khatam karne ke liye empty line):"
    )

    lines = []

    while True:

        line = input()

        if line == "":
            break

        lines.append(line)

    result = triage(
        "\n".join(lines)
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )