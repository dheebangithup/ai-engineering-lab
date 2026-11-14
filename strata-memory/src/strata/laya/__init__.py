"""Laya Decision Model package for Strata Memory Engine.
Provides lightweight, sub-5ms pre-routing, pillar classification,
contradiction gating, and zero-LLM template extraction.
"""

from strata.laya.decision_engine import LayaDecision, LayaDecisionEngine, laya_engine

__all__ = ["LayaDecision", "LayaDecisionEngine", "laya_engine"]
