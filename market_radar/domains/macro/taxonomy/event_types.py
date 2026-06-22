from __future__ import annotations
from enum import Enum, auto


class EventFamily(str, Enum):
    CPI_HEADLINE = "cpi_headline"
    CPI_CORE = "cpi_core"
    NONFARM_PAYROLLS = "nonfarm_payrolls"
    UNEMPLOYMENT_RATE = "unemployment_rate"
    CORE_PCE = "core_pce"
    FOMC_RATE_DECISION = "fomc_rate_decision"
    FOMC_STATEMENT = "fomc_statement"
    AVERAGE_HOURLY_EARNINGS = "average_hourly_earnings"
    LABOR_FORCE_PARTICIPATION = "labor_force_participation"
    INITIAL_JOBLESS_CLAIMS = "initial_jobless_claims"
    PPI = "ppi"
    RETAIL_SALES = "retail_sales"
    ISM = "ism"


class EventComponent(str, Enum):
    # CPI components
    HEADLINE_MOM = "headline_mom"
    HEADLINE_YOY = "headline_yoy"
    CORE_MOM = "core_mom"
    CORE_YOY = "core_yoy"
    SHELTER = "shelter"
    SERVICES_EX_HOUSING = "services_ex_housing"
    ENERGY = "energy"
    FOOD = "food"

    # NFP components
    PAYROLL_CHANGE = "payroll_change"
    UNEMPLOYMENT_RATE = "unemployment_rate"
    AVERAGE_HOURLY_EARNINGS = "average_hourly_earnings"
    PARTICIPATION_RATE = "participation_rate"
    PRIOR_MONTH_REVISION = "prior_month_revision"
    HOUSEHOLD_SURVEY = "household_survey"
    ESTABLISHMENT_SURVEY = "establishment_survey"

    # PCE components
    CORE_PCE_MOM = "core_pce_mom"
    CORE_PCE_YOY = "core_pce_yoy"
    HEADLINE_PCE_MOM = "headline_pce_mom"
    HEADLINE_PCE_YOY = "headline_pce_yoy"
    PERSONAL_INCOME = "personal_income"
    PERSONAL_SPENDING = "personal_spending"
    PCE_REVISIONS = "pce_revisions"

    # FOMC components
    RATE_DECISION = "rate_decision"
    RATE_TARGET_UPPER = "rate_target_upper"
    RATE_TARGET_LOWER = "rate_target_lower"
    DOT_PLOT_MEDIAN = "dot_plot_median"
    STATEMENT_TEXT_HASH = "statement_text_hash"
    BALANCE_SHEET = "balance_sheet"
    FORWARD_GUIDANCE = "forward_guidance"
    ECONOMIC_PROJECTIONS = "economic_projections"
