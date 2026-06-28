"""
Financial Health Score (FHS) — a single [0–100] composite metric.

Inspired by FICO's model structure but applied to overall financial wellness
rather than creditworthiness. Higher = healthier.

Components:
  - Savings Rate        (25%)
  - Emergency Fund      (20%)
  - Debt Management     (20%)
  - Net Worth Growth    (15%)
  - Investment Activity (10%)
  - Goal Progress       (10%)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class HealthScoreBreakdown:
    """Detailed breakdown of the FHS with sub-scores and context."""
    overall: float
    grade: str          # A / B / C / D / F
    savings_score: float
    emergency_score: float
    debt_score: float
    net_worth_score: float
    investment_score: float
    goal_score: float
    summary: str
    action_item: str    # Single most impactful action to improve score


class FinancialHealthScorer:
    """
    Computes a holistic financial health score.

    Design notes:
    - Normalise each component to [0–100] before weighting.
    - Never penalise for zero investment if debt/emergency fund unresolved.
    - Net worth growth requires historical data; defaults to neutral if unavailable.
    """

    WEIGHTS = {
        "savings": 0.25,
        "emergency": 0.20,
        "debt": 0.20,
        "net_worth": 0.15,
        "investment": 0.10,
        "goals": 0.10,
    }

    def compute(
        self,
        monthly_income: float,
        monthly_expenses: float,
        monthly_debt_payment: float,
        total_cash: float,
        total_debt: float,
        portfolio_value: float,
        crypto_value: float,
        goals: List[Dict],
        prev_net_worth: float = 0.0,
    ) -> HealthScoreBreakdown:
        """
        Compute the Financial Health Score.

        Args:
            prev_net_worth: Net worth from previous period (for growth calculation).
                            Pass 0.0 if historical data unavailable.
        """
        total_investment = portfolio_value + crypto_value
        net_worth = total_cash + total_investment - total_debt

        savings_score = self._savings_rate_score(monthly_income, monthly_expenses, monthly_debt_payment)
        emergency_score = self._emergency_fund_score(total_cash, monthly_expenses)
        debt_score = self._debt_score(monthly_income, monthly_debt_payment, total_debt)
        net_worth_score = self._net_worth_growth_score(net_worth, prev_net_worth)
        investment_score = self._investment_score(total_investment, monthly_income)
        goal_score = self._goal_score(goals)

        overall = (
            savings_score * self.WEIGHTS["savings"]
            + emergency_score * self.WEIGHTS["emergency"]
            + debt_score * self.WEIGHTS["debt"]
            + net_worth_score * self.WEIGHTS["net_worth"]
            + investment_score * self.WEIGHTS["investment"]
            + goal_score * self.WEIGHTS["goals"]
        )

        grade = self._grade(overall)
        summary = self._build_summary(overall, savings_score, emergency_score, debt_score)
        action = self._best_action(savings_score, emergency_score, debt_score, investment_score)

        return HealthScoreBreakdown(
            overall=round(overall, 1),
            grade=grade,
            savings_score=round(savings_score, 1),
            emergency_score=round(emergency_score, 1),
            debt_score=round(debt_score, 1),
            net_worth_score=round(net_worth_score, 1),
            investment_score=round(investment_score, 1),
            goal_score=round(goal_score, 1),
            summary=summary,
            action_item=action,
        )

    def _savings_rate_score(self, income, expenses, debt_payment) -> float:
        if income <= 0:
            return 0.0
        rate = (income - expenses - debt_payment) / income
        if rate >= 0.30: return 100.0
        if rate >= 0.20: return 80.0 + (rate - 0.20) / 0.10 * 20
        if rate >= 0.10: return 60.0 + (rate - 0.10) / 0.10 * 20
        if rate >= 0.00: return rate / 0.10 * 60
        return max(0.0, 60 + rate * 100)  # Negative rate penalised

    def _emergency_fund_score(self, cash, monthly_expenses) -> float:
        if monthly_expenses <= 0:
            return 50.0
        months = cash / monthly_expenses
        if months >= 12: return 100.0
        if months >= 6:  return 90.0 + (months - 6) / 6 * 10
        if months >= 3:  return 70.0 + (months - 3) / 3 * 20
        if months >= 1:  return 30.0 + (months - 1) / 2 * 40
        return max(0.0, months / 1.0 * 30)

    def _debt_score(self, income, debt_payment, total_debt) -> float:
        if income <= 0 and total_debt > 0:
            return 0.0
        dti = debt_payment / income if income > 0 else 0
        if total_debt == 0: return 100.0
        if dti <= 0.10: return 90.0 + (0.10 - dti) / 0.10 * 10
        if dti <= 0.20: return 75.0 + (0.20 - dti) / 0.10 * 15
        if dti <= 0.36: return 50.0 + (0.36 - dti) / 0.16 * 25
        if dti <= 0.50: return 25.0 + (0.50 - dti) / 0.14 * 25
        return max(0.0, 25 - (dti - 0.50) * 100)

    def _net_worth_growth_score(self, current_nw: float, prev_nw: float) -> float:
        if prev_nw == 0:
            return 60.0 if current_nw >= 0 else 20.0
        growth = (current_nw - prev_nw) / abs(prev_nw) if prev_nw != 0 else 0
        if growth >= 0.20: return 100.0
        if growth >= 0.10: return 80.0 + (growth - 0.10) / 0.10 * 20
        if growth >= 0.00: return 60.0 + growth / 0.10 * 20
        if growth >= -0.10: return 30.0 + (growth + 0.10) / 0.10 * 30
        return max(0.0, 30 + growth * 100)

    def _investment_score(self, total_investment: float, monthly_income: float) -> float:
        if monthly_income <= 0:
            return 50.0
        months_of_income = total_investment / monthly_income
        if months_of_income >= 24: return 100.0
        if months_of_income >= 12: return 80.0
        if months_of_income >= 6:  return 60.0
        if months_of_income >= 3:  return 40.0
        if months_of_income > 0:   return 20.0
        return 10.0  # Not penalised to 0 (may be justified by other factors)

    def _goal_score(self, goals: List[Dict]) -> float:
        if not goals:
            return 50.0  # Neutral if no goals set
        total_progress = sum(
            min(g.get("current_amount", 0) / max(g.get("target_amount", 1), 1), 1.0)
            for g in goals
        ) / len(goals)
        return total_progress * 100

    def _grade(self, score: float) -> str:
        if score >= 90: return "A+"
        if score >= 80: return "A"
        if score >= 70: return "B"
        if score >= 60: return "C"
        if score >= 50: return "D"
        return "F"

    def _build_summary(self, overall, savings, emergency, debt) -> str:
        weakest = min([
            ("savings rate", savings),
            ("emergency fund", emergency),
            ("debt management", debt),
        ], key=lambda x: x[1])
        return (
            f"Financial Health Score: {overall:.0f}/100 (Grade {self._grade(overall)}). "
            f"Biggest improvement opportunity: {weakest[0]} ({weakest[1]:.0f}/100)."
        )

    def _best_action(self, savings, emergency, debt, investment) -> str:
        scores = {
            "Increase your savings rate by reducing discretionary spending": savings,
            "Build your emergency fund to 6 months of expenses": emergency,
            "Pay down high-interest debt aggressively": debt,
            "Start a regular investment contribution plan": investment,
        }
        return min(scores, key=scores.get)
