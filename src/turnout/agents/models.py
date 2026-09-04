"""Model factory. Model ids come from configuration."""

from __future__ import annotations

from strands.models import BedrockModel

from turnout.config import settings


def reasoning_model(max_tokens: int = 1500) -> BedrockModel:
    return BedrockModel(model_id=settings.reasoning_model_id, region_name=settings.region,
                        temperature=0.1, max_tokens=max_tokens)


def fast_model(max_tokens: int = 600) -> BedrockModel:
    return BedrockModel(model_id=settings.fast_model_id, region_name=settings.region,
                        temperature=0.0, max_tokens=max_tokens)
