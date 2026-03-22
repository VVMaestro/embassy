import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock


def default_state_path() -> str:
    src_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(src_dir)
    return os.path.join(project_root, "data", "runtime_state.json")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RuntimeState:
    enabled: bool
    disabled_reason: str | None
    updated_at: str
    last_success_at: str | None = None


class RuntimeStateStore:
    def __init__(self, path: str | None = None, logger: logging.Logger | None = None):
        self.path = os.path.abspath(path or default_state_path())
        self.logger = logger or logging.getLogger("runtime_state")
        self._lock = Lock()

    def get_state(self) -> RuntimeState:
        with self._lock:
            return self._load_state_locked()

    def enable(self) -> RuntimeState:
        with self._lock:
            current = self._load_state_locked()
            state = RuntimeState(
                enabled=True,
                disabled_reason=None,
                updated_at=utc_now_iso(),
                last_success_at=current.last_success_at,
            )
            self._persist_state_locked(state)
            return state

    def disable(self, reason: str) -> RuntimeState:
        with self._lock:
            current = self._load_state_locked()
            state = RuntimeState(
                enabled=False,
                disabled_reason=reason,
                updated_at=utc_now_iso(),
                last_success_at=current.last_success_at,
            )
            self._persist_state_locked(state)
            return state

    def mark_approved_and_disable(
        self, reason: str = "auto_disabled_after_step4_success"
    ) -> RuntimeState:
        with self._lock:
            timestamp = utc_now_iso()
            state = RuntimeState(
                enabled=False,
                disabled_reason=reason,
                updated_at=timestamp,
                last_success_at=timestamp,
            )
            self._persist_state_locked(state)
            return state

    def _load_state_locked(self) -> RuntimeState:
        if not os.path.exists(self.path):
            state = RuntimeState(
                enabled=True,
                disabled_reason=None,
                updated_at=utc_now_iso(),
                last_success_at=None,
            )
            self._persist_state_locked(state)
            return state

        try:
            with open(self.path, encoding="utf-8") as handle:
                payload = json.load(handle)

            state = RuntimeState(
                enabled=bool(payload["enabled"]),
                disabled_reason=payload.get("disabled_reason"),
                updated_at=payload["updated_at"],
                last_success_at=payload.get("last_success_at"),
            )
            return state
        except Exception as error:
            self.logger.error(
                "Failed to read runtime state from %s: %s", self.path, error
            )
            fallback_state = RuntimeState(
                enabled=False,
                disabled_reason="state_load_error",
                updated_at=utc_now_iso(),
                last_success_at=None,
            )

            try:
                self._persist_state_locked(fallback_state)
            except Exception as persist_error:
                self.logger.error(
                    "Failed to persist fallback runtime state to %s: %s",
                    self.path,
                    persist_error,
                )

            return fallback_state

    def _persist_state_locked(self, state: RuntimeState):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(self.path),
            delete=False,
        ) as handle:
            json.dump(asdict(state), handle, ensure_ascii=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = handle.name

        os.replace(temp_path, self.path)
