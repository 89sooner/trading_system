"""Pattern learning, matching, and alerting primitives."""

from trading_system.patterns.alerts import PatternAlert, PatternAlertService
from trading_system.patterns.matcher import PatternMatcher
from trading_system.patterns.repository import PatternSet, PatternSetRepository
from trading_system.patterns.trainer import PatternTrainer
from trading_system.patterns.types import LearnedPattern, PatternExample, PatternMatch

__all__ = [
    "LearnedPattern",
    "PatternAlert",
    "PatternAlertService",
    "PatternExample",
    "PatternMatch",
    "PatternMatcher",
    "PatternSet",
    "PatternSetRepository",
    "PatternTrainer",
]
