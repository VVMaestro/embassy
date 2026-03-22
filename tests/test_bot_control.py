import logging
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.bot_control import TelegramControlServer
from src.runtime_state import RuntimeStateStore


class TelegramControlServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_token = os.environ.get("EMBASSY_BOT")
        self.original_user_id = os.environ.get("BOT_USER_ID")
        os.environ["EMBASSY_BOT"] = "token"
        os.environ["BOT_USER_ID"] = "12345"
        self.store = RuntimeStateStore(
            os.path.join(self.temp_dir.name, "runtime_state.json"),
            logging.getLogger("test.state"),
        )
        self.server = TelegramControlServer(
            self.store,
            logging.getLogger("test.telegram"),
        )

    def tearDown(self):
        if self.original_token is None:
            os.environ.pop("EMBASSY_BOT", None)
        else:
            os.environ["EMBASSY_BOT"] = self.original_token

        if self.original_user_id is None:
            os.environ.pop("BOT_USER_ID", None)
        else:
            os.environ["BOT_USER_ID"] = self.original_user_id

    async def test_authorized_user_can_disable_bot(self):
        message = AsyncMock()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=12345),
            effective_message=message,
            callback_query=None,
        )

        await self.server.handle_disable(update, None)

        state = self.store.get_state()
        self.assertFalse(state.enabled)
        message.reply_text.assert_awaited()

    async def test_unauthorized_user_cannot_change_state(self):
        message = AsyncMock()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            effective_message=message,
            callback_query=None,
        )

        await self.server.handle_disable(update, None)

        state = self.store.get_state()
        self.assertTrue(state.enabled)
        message.reply_text.assert_awaited_with("Unauthorized")


if __name__ == "__main__":
    unittest.main()
