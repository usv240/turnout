"""Create the AgentCore resources ahead of time.

Provisioning a memory takes minutes. That is fine once and unacceptable while a chief is waiting, so
it happens here rather than on the first request.

    python -m turnout.agentcore.provision
    python -m turnout.agentcore.provision --list
"""

from __future__ import annotations

import argparse
import time

import boto3

from turnout.agentcore.memory import ResponseMemory

DEPARTMENTS = ("millbrook", "riverton", "cedar")


def provision(region: str = "us-east-1", wait: int = 600) -> dict[str, str]:
    out: dict[str, str] = {}
    for dept in DEPARTMENTS:
        m = ResponseMemory(dept, region)
        started = time.time()
        try:
            mid = m.ensure(wait_seconds=wait, create=True)
            out[dept] = mid
            print(f"  {dept:12s} {mid}  ({time.time() - started:.0f}s)")
        except Exception as exc:
            print(f"  {dept:12s} FAILED {type(exc).__name__}: {str(exc)[:120]}")
    return out


def show(region: str = "us-east-1") -> None:
    cp = boto3.client("bedrock-agentcore-control", region_name=region)
    for m in cp.list_memories(maxResults=100).get("memories", []):
        if m.get("id", "").startswith("turnout_"):
            print(f"  {m['id']:44s} {m.get('status')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        show(a.region)
        return
    print("Provisioning AgentCore memories, one per department. This takes a few minutes each.")
    provision(a.region)


if __name__ == "__main__":
    main()
