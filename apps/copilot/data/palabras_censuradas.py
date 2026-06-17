"""Curated ES/EN profanity lists and allow-list defaults for the copilot
moderation layer (PR 1b, copilot-content-moderation).

The hardcoded lists are shipped in code (NOT in a JSON file) so tests can
pin the exact entries. Each token is paired with a severity tag (light /
strong) that ``HardcodedWordListProvider`` consults to decide whether to
censor with ``***`` (light) or report as a hard block (strong).

The list is intentionally conservative and small (~12-20 entries total).
The OpenAI Moderation API is the second line of defence for novel
evasion, and the operator can extend the allow-list (NOT the word list)
without code change by editing the JSON file pointed to by
``COPILOT_MODERATION_ALLOWLIST_PATH``.

A note on curation:
- ``"coño"`` and ``"verga"`` are mild Spanish vulgarities, comparable to
  English ``"damn"`` or ``"crap"``. They are not slurs.
- The strong list includes the multi-word ``"hijo de puta"`` because the
  standalone ``"puta"`` is the more common variant and the whole phrase
  is a target for raw-keyword evaders. The allow-list masks both.
- Slurs are intentionally conservative: a small set of clear-cut cases,
  not an exhaustive dictionary. Operators are expected to extend via
  OpenAI Moderation's semantic classification.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# Light severity — censored with '***' but passed to the LLM
# --------------------------------------------------------------------------- #
# ES light vulgarities (comparable to "damn" or "crap" in English).
# Curated: ~6 entries covering the most common venting words in ES academic
# context (students frustrated about grades, schedules, etc.).
DEFAULT_PROFANITY_LIGHT: tuple[str, ...] = (
    # Spanish (light)
    "mierda",
    "carajo",
    "joder",
    "cagada",
    "coño",
    "verga",
    # English (light)
    "shit",
    "damn",
    "crap",
)


# --------------------------------------------------------------------------- #
# Strong severity — rejected outright (Tier 3a)
# --------------------------------------------------------------------------- #
# ES strong: includes a multi-word phrase as a target for raw-keyword evaders
# (since "puta" alone is the most common form, the phrase is a defence layer).
DEFAULT_PROFANITY_STRONG: tuple[str, ...] = (
    # Spanish (strong)
    "pendejo",
    "puta",
    "cabron",
    "hijo de puta",
    "la concha de tu madre",
    # English (strong)
    "fuck",
    "motherfucker",
    "bitch",
    "asshole",
)


# --------------------------------------------------------------------------- #
# Default in-code allow-list (academic Spanish phrases)
# --------------------------------------------------------------------------- #
# Phrases that have legitimate academic usage. The allow-list masks strong
# matches when the input contains one of these phrases as a substring
# (case-insensitive, on the normalized form).
# Multi-word phrases (e.g. "hijo de") are matched AFTER normalization.
DEFAULT_ALLOWLIST: tuple[str, ...] = (
    "hijo de",  # "hijo de familia", "hijo de la patria", ...
    "a partir de",  # common academic Spanish construction
    "del lado de",  # common academic Spanish construction
)


# --------------------------------------------------------------------------- #
# File-system path to the JSON allow-list (production default)
# --------------------------------------------------------------------------- #
# This path is mirrored in ``config.settings.base.COPILOT_MODERATION_ALLOWLIST_PATH``.
# Kept here for documentation purposes; the actual loader uses the setting.
DEFAULT_ALLOWLIST_FILE_PATH: str = "apps/copilot/data/allowlist_es.json"
