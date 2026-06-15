from typing import Any

import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_expo_push(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, Any],
) -> list[str]:
    if not tokens:
        return []
    messages = [{"to": token, "sound": "default", "title": title, "body": body, "data": data} for token in tokens]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(EXPO_PUSH_URL, json=messages)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    invalid: list[str] = []
    tickets = payload.get("data", [])
    if isinstance(tickets, dict):
        tickets = [tickets]
    for token, ticket in zip(tokens, tickets, strict=False):
        if not isinstance(ticket, dict):
            continue
        details = ticket.get("details") or {}
        if ticket.get("status") == "error" and details.get("error") == "DeviceNotRegistered":
            invalid.append(token)
    return invalid
