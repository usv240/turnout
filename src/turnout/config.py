"""Runtime configuration. Everything that differs between local demo and AWS lives here.

Model IDs are configuration, never hard-coded in agent code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Where we run: "local" uses in-memory store, simulated SMS, fixture weather.
    # "aws" uses DynamoDB, End User Messaging, live NWS, AgentCore Memory.
    mode: str = field(default_factory=lambda: _env("TURNOUT_MODE", "local"))
    region: str = field(default_factory=lambda: _env("AWS_REGION", "us-east-1"))

    # Models. Reasoning model does planning and message drafting. Fast model does parsing and classification.
    # Verified on September 3, 2026 in account us-east-1: Sonnet 4.6, Sonnet 4.5, Opus 4.6, Haiku 4.5,
    # Nova Pro and Nova 2 Lite respond. Sonnet 5 is not enabled for this account.
    reasoning_model_id: str = field(
        default_factory=lambda: _env("TURNOUT_REASONING_MODEL", "us.anthropic.claude-sonnet-4-6")
    )
    fast_model_id: str = field(
        default_factory=lambda: _env("TURNOUT_FAST_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
    )
    fallback_model_id: str = field(default_factory=lambda: _env("TURNOUT_FALLBACK_MODEL", "us.amazon.nova-2-lite-v1:0"))

    # Storage
    table_name: str = field(default_factory=lambda: _env("TURNOUT_TABLE", "Turnout"))
    artifacts_bucket: str = field(default_factory=lambda: _env("TURNOUT_BUCKET", "turnout-artifacts"))
    local_state_path: str = field(default_factory=lambda: _env("TURNOUT_STATE", "data/state.json"))

    # Messaging
    sms_origination_id: str = field(default_factory=lambda: _env("TURNOUT_SMS_ORIGINATION", ""))

    # AgentCore. Off by default so the tests and a clone with no AWS access stay fast and offline;
    # on in the deployment, where the risk kernel runs in Code Interpreter and response history
    # lives in Memory. Every result records which one actually answered.
    use_agentcore: bool = field(
        default_factory=lambda: _env("TURNOUT_USE_AGENTCORE", "").lower() in ("1", "true", "yes"))

    # Policy defaults (can be overridden per department)
    default_quiet_hours: tuple[int, int] = (22, 6)
    default_weekly_ask_limit: int = 2
    chief_reply_timeout_hours: int = 2
    closer_wait_minutes: int = 90

    # Risk thresholds
    risk_critical: float = 0.75
    risk_high: float = 0.50
    risk_elevated: float = 0.25

    @property
    def is_local(self) -> bool:
        return self.mode == "local"


settings = Settings()
