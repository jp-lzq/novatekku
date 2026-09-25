"""Interface between the AI gateway and the AI core.

The core (prompts, answer rules, model calls) is a separate, private Python
package.  It must provide ``answer(request: AIRequest) -> str``.  The package
is chosen with the AI_CORE_MODULE setting; when it is not installed the
gateway answers with a short "temporarily unavailable" notice.
"""

import importlib
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

UNAVAILABLE_REPLIES = {
    "ja": "現在 NOVA AI は一時的に利用できません。少し時間をおいてからもう一度お試しください。",
    "zh": "当前 NOVA AI 暂时不可用，请稍后再试。",
    "en": "NOVA AI is temporarily unavailable. Please try again shortly.",
}


@dataclass(frozen=True)
class AIRequest:
    message: str
    language: str  # language the answer should use: zh / ja / en
    message_language: str  # language detected from the question itself
    history: list[dict] = field(default_factory=list)  # earlier messages in this session
    price_rows: list[dict] = field(default_factory=list)  # current accepted prices, one row per store
    matched_rows: list[dict] = field(default_factory=list)  # rows matching the model/capacity asked about
    price_lines: list[str] = field(default_factory=list)  # "model capacity:[store:price,...]" per product
    focused_price_lines: list[str] = field(default_factory=list)
    price_context_required: bool = False  # the question is about prices, stores or selling
    catalog: list[dict] = field(default_factory=list)  # models and capacities that currently have prices
    catalog_question: bool = False  # the question asks which models exist
    bulk_quote: dict | None = None  # {"rows": [...], "total": int} for "model × quantity" questions
    lineup: str = ""  # announced Apple lineup and retail prices (JSON text)


@lru_cache(maxsize=1)
def _load_core() -> Callable[[AIRequest], str] | None:
    module_name = settings.ai_core_module.strip()
    if not module_name:
        return None
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        logger.warning("AI core module %s is not installed", module_name)
        return None
    return module.answer


def answer(request: AIRequest) -> str:
    core = _load_core()
    reply = ""
    if core is not None:
        try:
            reply = core(request)
        except Exception:
            logger.exception("AI core failed")
    return reply or UNAVAILABLE_REPLIES.get(request.language, UNAVAILABLE_REPLIES["en"])
