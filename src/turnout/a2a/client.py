"""A2A client. Sends one message to a peer department's agent and returns its text reply."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

DEFAULT_TIMEOUT = 90.0


def _text_of(response: Any) -> str:
    """Pull the text out of whatever shape the A2A client hands back."""
    out: list[str] = []
    seen: set[int] = set()

    def walk(obj: Any) -> None:
        if obj is None or isinstance(obj, (int, float, bool)):
            return
        if isinstance(obj, str):
            out.append(obj)
            return
        if id(obj) in seen:
            return
        seen.add(id(obj))
        if isinstance(obj, dict):
            if obj.get("kind") == "text" and isinstance(obj.get("text"), str):
                out.append(obj["text"])
                return
            for v in obj.values():
                walk(v)
            return
        if isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)
            return
        for attr in ("parts", "root", "text", "artifacts", "result", "status", "message", "history"):
            if hasattr(obj, attr):
                walk(getattr(obj, attr))

    walk(response)
    return "\n".join(t for t in out if t.strip())


def extract_json(text: str) -> str:
    """The first complete JSON object in an agent reply.

    A streaming reply can repeat the answer and echo the request back, so taking everything between
    the first brace and the last one produces nonsense. Scan for the first balanced object that
    actually parses instead.
    """
    import json

    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start:i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except ValueError:
                    start = -1
    return text


async def send_text_async(base_url: str, text: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    import httpx
    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.types import Message, Part, Role, TextPart

    async with httpx.AsyncClient(timeout=timeout) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
        client = ClientFactory(ClientConfig(httpx_client=http, streaming=False)).create(card)
        msg = Message(kind="message", role=Role.user, message_id=uuid.uuid4().hex,
                      parts=[Part(root=TextPart(kind="text", text=text))])
        chunks: list[str] = []
        async for event in client.send_message(msg):
            got = _text_of(event)
            if got:
                chunks.append(got)
        return "\n".join(chunks)


def send_text(base_url: str, text: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Blocking send. Safe from tool code, which Strands runs on a worker thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(send_text_async(base_url, text, timeout))
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, send_text_async(base_url, text, timeout)).result(timeout + 15)


async def fetch_card_async(base_url: str, timeout: float = 20.0) -> dict:
    import httpx
    from a2a.client import A2ACardResolver

    async with httpx.AsyncClient(timeout=timeout) as http:
        card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
        return card.model_dump(mode="json", exclude_none=True)


def fetch_card(base_url: str, timeout: float = 20.0) -> dict:
    return asyncio.run(fetch_card_async(base_url, timeout))
