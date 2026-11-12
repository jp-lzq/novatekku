"""Check the numbers in an AI answer against NOVA's price evidence.

    from app.ai_gateway.verify import verify_answer
    report = verify_answer(reply, request.price_evidence, request.price_rows)
    report.status   -> "ok" / "warning" / "no_evidence" / "no_amounts"

Large language models sometimes write plausible but invented prices (a
"hallucination").  This module finds every amount in the answer (amounts.py),
compares it with the figures the evidence contains (facts.py, check.py) and can
add a short note listing what could not be confirmed (annotate.py).
"""

from .annotate import annotate, notes_for
from .check import Finding, Report, verify_answer

__all__ = ["verify_answer", "annotate", "notes_for", "Report", "Finding"]
