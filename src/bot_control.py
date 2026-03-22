from __future__ import annotations

import os
from logging import Logger
from typing import TYPE_CHECKING

from runtime_state import RuntimeState, RuntimeStateStore

if TYPE_CHECKING:
    from telegram import InlineKeyboardMarkup, Update
    from telegram.ext import Application, ContextTypes


class TelegramControlServer:
    def __init__(self, state_store: RuntimeStateStore, logger: Logger):
        token = os.getenv("EMBASSY_BOT")
        raw_user_id = os.getenv("BOT_USER_ID")

        if not token:
            raise ValueError("EMBASSY_BOT environment variable is not set")

        if not raw_user_id:
            raise ValueError("BOT_USER_ID environment variable is not set")

        self.token = token
        self.authorized_user_id = int(raw_user_id)
        self.state_store = state_store
        self.logger = logger

    def build_application(self) -> Application:
        from telegram.ext import (
            ApplicationBuilder,
            CallbackQueryHandler,
            CommandHandler,
        )

        application = ApplicationBuilder().token(self.token).build()
        application.add_handler(CommandHandler("status", self.handle_status))
        application.add_handler(CommandHandler("enable", self.handle_enable))
        application.add_handler(CommandHandler("disable", self.handle_disable))
        application.add_handler(CommandHandler("control", self.handle_control))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        return application

    def run(self):
        application = self.build_application()
        application.run_polling()

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        del context
        if not await self._ensure_authorized(update):
            return

        await self._reply(
            update,
            self.format_state_message(self.state_store.get_state()),
            reply_markup=self._control_markup(),
        )

    async def handle_enable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        del context
        if not await self._ensure_authorized(update):
            return

        state = self.state_store.enable()
        self.logger.info("Bot enabled by Telegram user %s", self.authorized_user_id)
        await self._reply(
            update,
            "Bot enabled.\n\n" + self.format_state_message(state),
            reply_markup=self._control_markup(),
        )

    async def handle_disable(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        del context
        if not await self._ensure_authorized(update):
            return

        state = self.state_store.disable("manual_disable")
        self.logger.info("Bot disabled by Telegram user %s", self.authorized_user_id)
        await self._reply(
            update,
            "Bot disabled.\n\n" + self.format_state_message(state),
            reply_markup=self._control_markup(),
        )

    async def handle_control(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        del context
        if not await self._ensure_authorized(update):
            return

        await self._reply(
            update,
            "Control panel\n\n" + self.format_state_message(self.state_store.get_state()),
            reply_markup=self._control_markup(),
        )

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        del context
        query = update.callback_query

        if query is None:
            return

        if not await self._ensure_authorized(update):
            return

        await query.answer()

        action = query.data or ""
        if action == "enable":
            state = self.state_store.enable()
            message = "Bot enabled.\n\n" + self.format_state_message(state)
        elif action == "disable":
            state = self.state_store.disable("manual_disable")
            message = "Bot disabled.\n\n" + self.format_state_message(state)
        else:
            message = self.format_state_message(self.state_store.get_state())

        await self._reply(update, message, reply_markup=self._control_markup())

    @staticmethod
    def format_state_message(state: RuntimeState) -> str:
        status = "enabled" if state.enabled else "disabled"
        disabled_reason = state.disabled_reason or "-"
        last_success_at = state.last_success_at or "-"
        return (
            f"Status: {status}\n"
            f"Disabled reason: {disabled_reason}\n"
            f"Updated at: {state.updated_at}\n"
            f"Last success at: {last_success_at}"
        )

    async def _ensure_authorized(self, update: Update) -> bool:
        user = update.effective_user
        user_id = user.id if user else None
        if user_id == self.authorized_user_id:
            return True

        self.logger.warning("Rejected unauthorized Telegram user: %s", user_id)

        if update.callback_query is not None:
            await update.callback_query.answer("Unauthorized", show_alert=True)
        elif update.effective_message is not None:
            await update.effective_message.reply_text("Unauthorized")

        return False

    async def _reply(
        self,
        update: Update,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ):
        if update.effective_message is None:
            return

        await update.effective_message.reply_text(text, reply_markup=reply_markup)

    @staticmethod
    def _control_markup() -> InlineKeyboardMarkup | None:
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        except ModuleNotFoundError:
            return None

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Enable", callback_data="enable"),
                    InlineKeyboardButton("Disable", callback_data="disable"),
                ],
                [InlineKeyboardButton("Status", callback_data="status")],
            ]
        )
