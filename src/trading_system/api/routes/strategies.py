from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from trading_system.api.errors import RequestValidationError
from trading_system.api.schemas import (
    StrategyConfigDTO,
    StrategyProfileCreateDTO,
    StrategyProfileDTO,
)
from trading_system.strategy.base import SignalSide
from trading_system.strategy.repository import StrategyProfile, StrategyProfileRepository

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@router.post("", response_model=StrategyProfileDTO, status_code=status.HTTP_201_CREATED)
def create_strategy_profile(payload: StrategyProfileCreateDTO) -> StrategyProfileDTO:
    strategy = payload.strategy
    if strategy.profile_id is not None:
        raise RequestValidationError(
            error_code="invalid_strategy",
            message="Stored strategy profiles must use inline pattern strategy settings.",
        )
    if strategy.pattern_set_id is None:
        raise RequestValidationError(
            error_code="invalid_strategy",
            message="strategy.pattern_set_id is required.",
        )
    if not strategy.label_to_side:
        raise RequestValidationError(
            error_code="invalid_strategy",
            message="strategy.label_to_side must contain at least one mapping.",
        )

    profile = StrategyProfile(
        strategy_id=payload.strategy_id.strip(),
        name=payload.name.strip(),
        strategy_type=strategy.type,
        pattern_set_id=strategy.pattern_set_id.strip(),
        label_to_side={
            label: SignalSide(side)
            for label, side in sorted(strategy.label_to_side.items())
        },
        trade_quantity=strategy.trade_quantity,
        threshold_overrides={
            label: float(value) for label, value in sorted(strategy.threshold_overrides.items())
        },
    )
    repository = StrategyProfileRepository(_resolve_strategy_dir())
    repository.save(profile)
    return _to_strategy_profile_dto(profile)


@router.get("", response_model=list[StrategyProfileDTO])
def list_strategy_profiles() -> list[StrategyProfileDTO]:
    repository = StrategyProfileRepository(_resolve_strategy_dir())
    return [_to_strategy_profile_dto(profile) for profile in repository.list()]


@router.get("/{strategy_id}", response_model=StrategyProfileDTO)
def get_strategy_profile(strategy_id: str) -> StrategyProfileDTO:
    repository = StrategyProfileRepository(_resolve_strategy_dir())
    try:
        profile = repository.get(strategy_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_strategy_profile_dto(profile)


def _resolve_strategy_dir() -> Path:
    return Path(os.getenv("TRADING_SYSTEM_STRATEGY_DIR", "configs/strategies"))


def _to_strategy_profile_dto(profile: StrategyProfile) -> StrategyProfileDTO:
    return StrategyProfileDTO(
        strategy_id=profile.strategy_id,
        name=profile.name,
        strategy=StrategyConfigDTO(
            type=profile.strategy_type,
            pattern_set_id=profile.pattern_set_id,
            label_to_side={label: side.value for label, side in profile.label_to_side.items()},
            trade_quantity=profile.trade_quantity,
            threshold_overrides=profile.threshold_overrides,
        ),
    )
