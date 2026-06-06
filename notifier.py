"""WhatsApp notification via Callmebot API."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(phone: str, api_key: str, message: str) -> bool:
    """
    Send a WhatsApp message via Callmebot.

    Args:
        phone: Phone number with country code (e.g. +353861234567)
        api_key: Callmebot API key
        message: Message text to send

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        params = {
            "phone": phone,
            "text": message,
            "apikey": api_key,
        }
        logger.debug("Sending WhatsApp notification to %s", phone)
        resp = requests.get(CALLMEBOT_URL, params=params, timeout=15)

        if resp.status_code == 200:
            logger.info("WhatsApp notification sent successfully")
            return True

        logger.warning(
            "WhatsApp notification failed: HTTP %d - %s",
            resp.status_code, resp.text,
        )
        return False

    except requests.RequestException as exc:
        logger.warning("WhatsApp notification failed: %s", exc)
        return False
