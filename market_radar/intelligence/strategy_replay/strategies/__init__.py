"""Macro strategy definitions for the replay system."""
from .inflation_headline import get_strategy_definition as get_cpi
from .inflation_core import get_strategy_definition as get_core_cpi
from .labor_payrolls import get_strategy_definition as get_nfp
from .labor_unemployment import get_strategy_definition as get_unemployment
from .core_pce import get_strategy_definition as get_core_pce
from .fomc_rate_decision import get_strategy_definition as get_fomc

ALL_MACRO_STRATEGIES = {
    "us_cpi": get_cpi(),
    "us_core_cpi": get_core_cpi(),
    "us_nonfarm_payrolls": get_nfp(),
    "us_unemployment_rate": get_unemployment(),
    "us_core_pce": get_core_pce(),
    "us_fomc_rate_decision": get_fomc(),
}

from .regulation_event import get_strategy_definition as get_regulation
from .catalyst_event import get_strategy_definition as get_catalyst
from .forced_flow import get_strategy_definition as get_forced_flow

# Vertical expansion strategies (exploratory maturity)
ALL_VERTICAL_STRATEGIES = {
    "regulation_event": get_regulation(),
    "catalyst_event": get_catalyst(),
    "forced_flow": get_forced_flow(),
}
