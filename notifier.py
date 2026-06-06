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
            "phone": phone.lstrip("+"),
            "text": message,
            "apikey": api_key,
        }
        logger.debug("Sending WhatsApp notification to %s", phone)
        resp = requests.get(CALLMEBOT_URL, params=params, timeout=15)

        if resp.status_code == 200:
            logger.info("WhatsApp notification sent to %s", phone)
            return True

        logger.warning(
            "WhatsApp notification failed for %s: HTTP %d - %s",
            phone, resp.status_code, resp.text,
        )
        return False

    except requests.RequestException as exc:
        logger.warning("WhatsApp notification failed for %s: %s", phone, exc)
        return False


def send_whatsapp_multi(phones: str, api_keys: str, message: str):
    """
    Send a WhatsApp message to multiple recipients.

    Args:
        phones: Comma-separated phone numbers
        api_keys: Comma-separated API keys (matching order)
        message: Message text to send
    """
    phone_list = [p.strip() for p in phones.split(",")]
    key_list = [k.strip() for k in api_keys.split(",")]

    if len(phone_list) != len(key_list):
        logger.error(
            "CALLMEBOT_PHONE has %d numbers but CALLMEBOT_API_KEY has %d keys. "
            "They must match.",
            len(phone_list), len(key_list),
        )
        return

    for phone, api_key in zip(phone_list, key_list):
        if phone and api_key:
            send_whatsapp(phone, api_key, message)
