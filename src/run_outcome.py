from enum import Enum


class RunOutcome(str, Enum):
    APPROVED = "APPROVED"
    NO_SLOT = "NO_SLOT"
    FAILED = "FAILED"
