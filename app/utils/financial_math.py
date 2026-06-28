"""
Financial math helpers: amortization, compound interest, NPV, loan payoff.
Pure functions — no I/O, fully testable.
"""
from __future__ import annotations
from typing import List, Tuple
import math


def monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    """Standard amortization monthly payment formula (PMT)."""
    if annual_rate == 0:
        return principal / term_months if term_months > 0 else 0.0
    r = annual_rate / 100 / 12
    return principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)


def remaining_balance(principal: float, annual_rate: float, term_months: int, paid_months: int) -> float:
    """Outstanding balance after N payments."""
    if annual_rate == 0:
        return max(0, principal - (principal / term_months) * paid_months)
    r = annual_rate / 100 / 12
    pmt = monthly_payment(principal, annual_rate, term_months)
    return principal * (1 + r) ** paid_months - pmt * ((1 + r) ** paid_months - 1) / r


def total_interest_paid(principal: float, annual_rate: float, term_months: int) -> float:
    """Total interest paid over the full loan term."""
    pmt = monthly_payment(principal, annual_rate, term_months)
    return pmt * term_months - principal


def compound_growth(principal: float, annual_rate: float, years: float, n: int = 12) -> float:
    """Compound interest: A = P(1 + r/n)^(nt)."""
    return principal * (1 + annual_rate / n) ** (n * years)


def future_value_annuity(monthly_contribution: float, annual_rate: float, years: float) -> float:
    """Future value of a regular monthly contribution."""
    if annual_rate == 0:
        return monthly_contribution * 12 * years
    r = annual_rate / 12
    n = years * 12
    return monthly_contribution * ((1 + r) ** n - 1) / r


def debt_avalanche_order(loans: List[dict]) -> List[dict]:
    """Sort loans highest-interest-first (avalanche method — minimises total interest)."""
    return sorted(loans, key=lambda l: l.get("interest_rate", 0), reverse=True)


def debt_snowball_order(loans: List[dict]) -> List[dict]:
    """Sort loans smallest-balance-first (snowball method — maximises motivation)."""
    return sorted(loans, key=lambda l: l.get("current_balance", 0))


def months_to_payoff(balance: float, annual_rate: float, monthly_payment_amt: float) -> int:
    """Number of months to pay off a loan with fixed monthly payment."""
    if monthly_payment_amt <= 0:
        return 9999
    if annual_rate == 0:
        return math.ceil(balance / monthly_payment_amt)
    r = annual_rate / 100 / 12
    if monthly_payment_amt <= balance * r:
        return 9999  # Payment doesn't cover interest
    n = math.log(monthly_payment_amt / (monthly_payment_amt - balance * r)) / math.log(1 + r)
    return math.ceil(n)


def emergency_fund_target(monthly_expenses: float, months: int = 6) -> float:
    """Recommended emergency fund size."""
    return monthly_expenses * months


def savings_rate(income: float, expenses: float, debt_payment: float) -> float:
    """Net savings rate as a percentage of income."""
    if income <= 0:
        return 0.0
    return max(0.0, (income - expenses - debt_payment) / income * 100)


def debt_to_income_ratio(monthly_debt: float, monthly_income: float) -> float:
    """Standard DTI ratio used by lenders."""
    if monthly_income <= 0:
        return 1.0
    return monthly_debt / monthly_income
