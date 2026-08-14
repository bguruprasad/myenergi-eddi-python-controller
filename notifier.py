"""Telegram notification via the Bot API."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(token: str, chat_id: str, message: str) -> bool:
    """
    Send a message to a single Telegram chat.

    Args:
        token: Telegram bot token from BotFather
        chat_id: Target chat ID (positive for users, negative for groups)
        message: Message text to send

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        logger.debug("Sending Telegram notification to chat %s", chat_id)
        resp = requests.post(
            TELEGRAM_API_URL.format(token=token),
            data={"chat_id": chat_id, "text": message},
            timeout=15,
        )

        if resp.ok and resp.json().get("ok"):
            logger.info("Telegram notification sent to chat %s", chat_id)
            return True

        # Telegram puts a human-readable reason in `description`.
        try:
            reason = resp.json().get("description", resp.text)
        except ValueError:
            reason = resp.text

        logger.warning(
            "Telegram notification failed for chat %s: HTTP %d - %s",
            chat_id, resp.status_code, reason,
        )
        return False

    except requests.RequestException as exc:
        logger.warning(
            "Telegram notification failed for chat %s: %s", chat_id, exc
        )
        return False


def send_telegram_multi(token: str, chat_ids: str, message: str):
    """
    Send a message to one or more Telegram chats.

    Args:
        token: Telegram bot token from BotFather
        chat_ids: Comma-separated chat IDs
        message: Message text to send
    """
    for chat_id in (c.strip() for c in chat_ids.split(",")):
        if chat_id:
            send_telegram(token, chat_id, message)
