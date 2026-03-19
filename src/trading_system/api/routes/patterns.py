from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from trading_system.api.errors import RequestValidationError
from trading_system.api.schemas import (
    LearnedPatternDTO,
    PatternSetDTO,
    PatternSetSaveRequestDTO,
    PatternTrainRequestDTO,
)
from trading_system.core.compat import UTC
from trading_system.core.types import MarketBar
from trading_system.patterns.repository import PatternSet, PatternSetRepository
from trading_system.patterns.trainer import PatternTrainer
from trading_system.patterns.types import LearnedPattern, PatternExample

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


@router.post("/train", response_model=PatternSetDTO)
def train_patterns(payload: PatternTrainRequestDTO) -> PatternSetDTO:
    _validate_pattern_examples(payload)
    trainer = PatternTrainer(default_threshold=payload.default_threshold)
    pattern_examples = []
    for example in payload.examples:
        pattern_examples.append(
            PatternExample(
                label=example.label.strip(),
                bars=_to_market_bars(payload.symbol, example.bars),
            )
        )
    try:
        learned_patterns = trainer.train(pattern_examples)
    except ValueError as exc:
        raise RequestValidationError(
            error_code="invalid_pattern_examples",
            message=str(exc),
        ) from exc
    pattern_set = PatternSet(
        pattern_set_id=_suggest_identifier(payload.name),
        name=payload.name.strip(),
        symbol=payload.symbol.strip().upper(),
        default_threshold=payload.default_threshold,
        examples_count=len(payload.examples),
        patterns=learned_patterns,
    )
    return _to_pattern_set_dto(pattern_set)


@router.post("", response_model=PatternSetDTO, status_code=status.HTTP_201_CREATED)
def save_pattern_set(payload: PatternSetSaveRequestDTO) -> PatternSetDTO:
    pattern_set = PatternSet(
        pattern_set_id=payload.pattern_set_id.strip(),
        name=payload.name.strip(),
        symbol=payload.symbol.strip().upper(),
        default_threshold=payload.default_threshold,
        examples_count=payload.examples_count,
        patterns=[_to_learned_pattern(pattern) for pattern in payload.patterns],
    )
    repository = PatternSetRepository(_resolve_pattern_dir())
    repository.save(pattern_set)
    return _to_pattern_set_dto(pattern_set)


@router.get("", response_model=list[PatternSetDTO])
def list_pattern_sets() -> list[PatternSetDTO]:
    repository = PatternSetRepository(_resolve_pattern_dir())
    return [_to_pattern_set_dto(pattern_set) for pattern_set in repository.list()]


@router.get("/{pattern_set_id}", response_model=PatternSetDTO)
def get_pattern_set(pattern_set_id: str) -> PatternSetDTO:
    repository = PatternSetRepository(_resolve_pattern_dir())
    try:
        pattern_set = repository.get(pattern_set_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_pattern_set_dto(pattern_set)


def _resolve_pattern_dir() -> Path:
    return Path(os.getenv("TRADING_SYSTEM_PATTERN_DIR", "configs/patterns"))


def _validate_pattern_examples(payload: PatternTrainRequestDTO) -> None:
    for example in payload.examples:
        if not example.label.strip():
            raise RequestValidationError(
                error_code="invalid_pattern_examples",
                message="Pattern example labels must be non-empty.",
            )


def _to_market_bars(symbol: str, bars) -> list[MarketBar]:
    parsed_bars: list[MarketBar] = []
    normalized_symbol = symbol.strip().upper()
    for bar in bars:
        try:
            timestamp = datetime.fromisoformat(bar.timestamp.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError as exc:
            raise RequestValidationError(
                error_code="invalid_pattern_examples",
                message=f"Invalid bar timestamp: {bar.timestamp}",
            ) from exc
        parsed_bars.append(
            MarketBar(
                symbol=normalized_symbol,
                timestamp=timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )
        )
    return parsed_bars


def _suggest_identifier(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return normalized or "pattern-set"


def _to_pattern_set_dto(pattern_set: PatternSet) -> PatternSetDTO:
    return PatternSetDTO(
        pattern_set_id=pattern_set.pattern_set_id,
        name=pattern_set.name,
        symbol=pattern_set.symbol,
        default_threshold=pattern_set.default_threshold,
        examples_count=pattern_set.examples_count,
        patterns=[
            LearnedPatternDTO(
                label=pattern.label,
                lookback=pattern.lookback,
                sample_size=pattern.sample_size,
                threshold=pattern.threshold,
                prototype=list(pattern.prototype),
            )
            for pattern in pattern_set.patterns
        ],
    )


def _to_learned_pattern(pattern: LearnedPatternDTO) -> LearnedPattern:
    return LearnedPattern(
        label=pattern.label,
        lookback=pattern.lookback,
        prototype=tuple(pattern.prototype),
        sample_size=pattern.sample_size,
        threshold=pattern.threshold,
    )
