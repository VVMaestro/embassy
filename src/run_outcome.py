from enum import Enum


class RunOutcome(str, Enum):
    APPROVED = "APPROVED"
    NO_SLOT = "NO_SLOT"
    CAPTCHA_FAILED = "CAPTCHA_FAILED"
    FAILED = "FAILED"
