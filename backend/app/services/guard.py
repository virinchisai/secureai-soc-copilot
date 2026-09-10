import re


INJECTION_PATTERNS = [
    r"\bignore (all|any|the|your|previous|prior) (instructions?|prompts?)\b",
    r"\bforget (all|any|the|your|previous|prior) (instructions?|prompts?)\b",
    r"\b(system|developer) (message|prompt|instructions?)\b",
    r"\breveal (the |your )?(prompt|instructions?|secrets?|api keys?)\b",
    r"\bshow (me )?(the |your )?(hidden|system|developer) "
    r"(prompt|message|instructions?)\b",
    r"\b(disregard|override|bypass) (the )?(rules?|instructions?|guardrails?)\b",
    r"\bdisable (the )?(safety|security|guardrails?|filters?)\b",
    r"\bact as (an? )?(unrestricted|unfiltered|different) (ai|assistant|model)\b",
    r"\bdeveloper mode\b",
    r"\b(execute|run) (the )?(hidden|secret) commands?\b",
    r"\bexfiltrate\b",
    r"\bjailbreak\b",
]


def detect_prompt_injection(text: str) -> str | None:
    normalized = " ".join(text.lower().split())
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return "The question resembles a prompt-injection attempt."
    return None
