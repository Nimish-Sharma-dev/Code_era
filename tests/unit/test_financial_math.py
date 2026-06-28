"""Unit tests for financial math utilities."""

import math
import pytest
from app.utils.financial_math import (
    monthly_payment, total_interest_paid, compound_growth,
    future_value_annuity, months_to_payoff, savings_rate,
    debt_to_income_ratio, debt_avalanche_order, emergency_fund_target,
)


def test_monthly_payment_standard():
    # $200k mortgage, 6% APR, 30 years
    pmt = monthly_payment(200_000, 6.0, 360)
    assert abs(pmt - 1199.10) < 1.0


def test_monthly_payment_zero_rate():
    # Zero interest: just principal / months
    pmt = monthly_payment(12_000, 0.0, 12)
    assert abs(pmt - 1000.0) < 0.01


def test_total_interest_always_positive():
    interest = total_interest_paid(10_000, 8.0, 24)
    assert interest > 0


def test_compound_growth_doubles():
    # Rule of 72: 72/7.2% ≈ 10 years to double
    result = compound_growth(10_000, 0.072, 10)
    assert result > 19_500  # Approximately doubled


def test_future_value_annuity():
    # $500/month at 7% for 10 years
    fv = future_value_annuity(500, 0.07, 10)
    assert fv > 86_000  # Reference: ~$86,730


def test_months_to_payoff():
    months = months_to_payoff(10_000, 18.0, 300)
    assert months > 36  # Takes significant time at 18% APR


def test_months_to_payoff_payment_too_small():
    # $100 payment on $10k at 18% APR — monthly interest = $150, can't cover it
    result = months_to_payoff(10_000, 18.0, 100)
    assert result == 9999


def test_savings_rate_normal():
    rate = savings_rate(5000, 3000, 500)
    assert abs(rate - 30.0) < 0.1


def test_savings_rate_negative_clipped_at_zero():
    rate = savings_rate(3000, 3500, 200)
    assert rate == 0.0


def test_debt_to_income():
    dti = debt_to_income_ratio(1500, 5000)
    assert abs(dti - 0.30) < 0.001


def test_avalanche_order_highest_rate_first():
    loans = [
        {"name": "Car", "interest_rate": 5.5, "current_balance": 10000},
        {"name": "Credit Card", "interest_rate": 22.0, "current_balance": 3000},
        {"name": "Student", "interest_rate": 4.5, "current_balance": 25000},
    ]
    ordered = debt_avalanche_order(loans)
    assert ordered[0]["name"] == "Credit Card"
    assert ordered[-1]["name"] == "Student"


def test_emergency_fund_target():
    target = emergency_fund_target(4000, months=6)
    assert target == 24000.0
