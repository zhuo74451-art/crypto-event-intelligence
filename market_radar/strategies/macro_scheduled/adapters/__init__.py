"""
Adapters package for the macro-scheduled event intelligence system.

Provides stub adapters, legacy wrappers, and validation bridges
that connect the macro strategy to external data sources and the
intelligence kernel system.
"""

from .intelligence_kernel_stub import (
    MacroStrategyHypothesisProposal,
    MacroAssessmentProposal,
    MacroTransmissionProposal,
)

from .acquisition_stub import AcquisitionStub
from .legacy_price_reader import LegacyPriceReader
from .legacy_market_reader import LegacyMarketReader
from .validation_stub import ValidationStub

__all__ = [
    "MacroStrategyHypothesisProposal",
    "MacroAssessmentProposal",
    "MacroTransmissionProposal",
    "AcquisitionStub",
    "LegacyPriceReader",
    "LegacyMarketReader",
    "ValidationStub",
]
