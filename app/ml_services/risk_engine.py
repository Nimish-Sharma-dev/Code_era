"""
Financial risk scoring engine.

Computes a composite risk score [0-100] for each user based on:
  - Debt-to-income ratio
  - Emergency fund coverage
  - Portfolio concentration / diversification
  - Savings rate
  - Investment risk profile vs. declared risk tolerance
  - Loan interest burden

Higher score = higher risk exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskProfile:
    """Structured risk scoring result with sub-component breakdown."""
    overall_score: float          # 0–100 (100 = highest risk)
    risk_level: str               # low / moderate / high / critical
    debt_score: float
    liquidity_score: float
    concentration_score: float
    savings_score: float
    volatility_score: float
    explanation: str
    recommendations: list[str]


class RiskEngine:
    """
    Rule-based and statistical financial risk scoring.

    Each sub-score is normalised to [0,100] before weighting.
    Weights are calibrated to reflect real-world financial planning priorities.
    """

    WEIGHTS = {
        "debt": 0.30,
        "liquidity": 0.25,
        "savings": 0.20,
        "concentration": 0.15,
        "volatility": 0.10,
    }

    THRESHOLDS = {
        "dti_safe": 0.28,        # 28% DTI = generally safe
        "dti_caution": 0.36,     # 36% = caution
        "dti_danger": 0.50,      # 50% = high risk
        "emergency_fund_min": 3,  # months
        "emergency_fund_ideal": 6,
        "savings_rate_min": 0.10,
        "savings_rate_ideal": 0.20,
    }

    def compute_risk_score(
        self,
        monthly_income: float,
        monthly_expenses: float,
        monthly_debt_payment: float,
        total_cash: float,
        total_debt: float,
        portfolio_value: float,
        asset_types: list[str],
        declared_risk_tolerance: str,
        avg_portfolio_volatility: float = 0.0,
        investments: list[dict] = None,
    ) -> RiskProfile:
        """
        Compute comprehensive risk profile.

        Args:
            monthly_income: Total monthly income (post-tax recommended).
            monthly_expenses: Total monthly non-debt expenses.
            monthly_debt_payment: Total monthly loan payments.
            total_cash: Liquid assets (checking + savings wallets).
            total_debt: Total outstanding loan balances.
            portfolio_value: Current value of investment portfolio.
            asset_types: List of asset type strings (equity, crypto, bond, etc.).
            declared_risk_tolerance: User's stated preference.
            avg_portfolio_volatility: Weighted avg volatility of holdings.
            investments: Raw investments list of dicts for dollar-weighted analysis.

        Returns:
            RiskProfile with scores, explanations, and action recommendations.
        """
        debt_score = self._score_debt(monthly_income, monthly_debt_payment, total_debt)
        liquidity_score = self._score_liquidity(total_cash, monthly_expenses)
        savings_score = self._score_savings(monthly_income, monthly_expenses, monthly_debt_payment)
        concentration_score = self._score_concentration(asset_types, portfolio_value, total_cash, investments)
        volatility_score = self._score_volatility(avg_portfolio_volatility, declared_risk_tolerance)

        # Add interaction penalty for compounding/correlated risks
        interaction_penalty = 0.0
        if debt_score > 50.0 and liquidity_score > 50.0:
            interaction_penalty += 12.0
        if savings_score > 50.0 and debt_score > 50.0:
            interaction_penalty += 8.0

        overall = (
            debt_score * self.WEIGHTS["debt"]
            + liquidity_score * self.WEIGHTS["liquidity"]
            + savings_score * self.WEIGHTS["savings"]
            + concentration_score * self.WEIGHTS["concentration"]
            + volatility_score * self.WEIGHTS["volatility"]
            + interaction_penalty
        )
        overall = min(100.0, overall)

        risk_level = self._classify_risk(overall)
        explanation = self._build_explanation(
            overall, debt_score, liquidity_score, savings_score,
            concentration_score, volatility_score, monthly_income,
            monthly_debt_payment
        )
        recommendations = self._generate_recommendations(
            debt_score, liquidity_score, savings_score,
            concentration_score, monthly_income
        )

        return RiskProfile(
            overall_score=round(overall, 2),
            risk_level=risk_level,
            debt_score=round(debt_score, 2),
            liquidity_score=round(liquidity_score, 2),
            concentration_score=round(concentration_score, 2),
            savings_score=round(savings_score, 2),
            volatility_score=round(volatility_score, 2),
            explanation=explanation,
            recommendations=recommendations,
        )

    def _score_debt(
        self, monthly_income: float, monthly_debt: float, total_debt: float
    ) -> float:
        """Score debt risk [0=low_risk, 100=high_risk]."""
        if monthly_income <= 0:
            return 80.0
        dti = monthly_debt / monthly_income
        if dti <= self.THRESHOLDS["dti_safe"]:
            return dti / self.THRESHOLDS["dti_safe"] * 30
        elif dti <= self.THRESHOLDS["dti_caution"]:
            return 30 + (dti - self.THRESHOLDS["dti_safe"]) / (
                self.THRESHOLDS["dti_caution"] - self.THRESHOLDS["dti_safe"]
            ) * 30
        elif dti <= self.THRESHOLDS["dti_danger"]:
            return 60 + (dti - self.THRESHOLDS["dti_caution"]) / (
                self.THRESHOLDS["dti_danger"] - self.THRESHOLDS["dti_caution"]
            ) * 30
        return min(100.0, 90 + (dti - self.THRESHOLDS["dti_danger"]) * 20)

    def _score_liquidity(self, total_cash: float, monthly_expenses: float) -> float:
        """Score liquidity risk — low cash relative to expenses = high risk."""
        if monthly_expenses <= 0:
            return 10.0
        months_coverage = total_cash / monthly_expenses
        ideal = self.THRESHOLDS["emergency_fund_ideal"]
        min_months = self.THRESHOLDS["emergency_fund_min"]
        if months_coverage >= ideal:
            return max(0, 10 - (months_coverage - ideal) * 2)
        elif months_coverage >= min_months:
            return 10 + (ideal - months_coverage) / (ideal - min_months) * 40
        else:
            return min(100, 50 + (min_months - months_coverage) / min_months * 50)

    def _score_savings(
        self, income: float, expenses: float, debt_payment: float
    ) -> float:
        """Score savings adequacy — low/negative savings rate = high risk."""
        if income <= 0:
            return 70.0
        savings = income - expenses - debt_payment
        savings_rate = savings / income
        if savings_rate >= self.THRESHOLDS["savings_rate_ideal"]:
            return 5.0
        elif savings_rate >= self.THRESHOLDS["savings_rate_min"]:
            frac = (savings_rate - self.THRESHOLDS["savings_rate_min"]) / (
                self.THRESHOLDS["savings_rate_ideal"] - self.THRESHOLDS["savings_rate_min"]
            )
            return 5 + (1 - frac) * 35
        elif savings_rate >= 0:
            return 40 + (1 - savings_rate / self.THRESHOLDS["savings_rate_min"]) * 30
        return min(100, 70 + abs(savings_rate) * 30)

    def _score_concentration(
        self, asset_types: list[str], portfolio_value: float, total_cash: float, investments: list[dict] = None
    ) -> float:
        """Score portfolio concentration risk."""
        if portfolio_value == 0:
            return 20.0

        if investments:
            total_val = sum(inv.get("current_value", 0) for inv in investments)
            if total_val > 0:
                hhi = sum((inv.get("current_value", 0) / total_val) ** 2 for inv in investments)
                diversification_score = hhi * 50
                crypto_val = sum(inv.get("current_value", 0) for inv in investments if str(inv.get("asset_class", "")).lower() == "crypto")
                crypto_pct = crypto_val / total_val
                crypto_score = crypto_pct * 50
                return min(100.0, diversification_score + crypto_score)

        unique_types = len(set(asset_types))
        high_risk_count = sum(1 for t in asset_types if t in ("crypto", "speculative"))
        crypto_pct = high_risk_count / max(len(asset_types), 1)

        diversification_score = max(0, 50 - unique_types * 10)
        crypto_score = crypto_pct * 50
        return min(100.0, diversification_score + crypto_score)

    def _score_volatility(self, volatility: float, risk_tolerance: str) -> float:
        """Compare portfolio volatility against user's declared tolerance."""
        tolerance_limits = {
            "conservative": 0.10,
            "moderate": 0.20,
            "aggressive": 0.35,
            "speculative": 1.0,
        }
        limit = tolerance_limits.get(risk_tolerance, 0.20)
        if volatility <= limit:
            return (volatility / limit) * 30
        return min(100, 30 + (volatility - limit) / limit * 70)

    def _classify_risk(self, score: float) -> str:
        if score < 25:
            return "low"
        elif score < 50:
            return "moderate"
        elif score < 75:
            return "high"
        return "critical"

    def _build_explanation(self, overall, debt, liquidity, savings, concentration, volatility,
                            income, debt_payment) -> str:
        dti = (debt_payment / income * 100) if income > 0 else 0
        parts = [
            f"Your overall financial risk score is {overall:.0f}/100 ({self._classify_risk(overall).upper()}).",
            f"Debt burden contributes {debt:.0f}/100 (DTI: {dti:.1f}%).",
            f"Liquidity risk: {liquidity:.0f}/100.",
            f"Savings adequacy: {savings:.0f}/100.",
            f"Portfolio concentration risk: {concentration:.0f}/100.",
        ]
        return " ".join(parts)

    def _generate_recommendations(
        self, debt, liquidity, savings, concentration, income
    ) -> list[str]:
        recs = []
        if debt > 60:
            recs.append("Prioritise debt reduction — your DTI is dangerously high.")
        if liquidity > 50:
            recs.append("Build your emergency fund to cover 6 months of expenses before investing.")
        if savings > 50:
            recs.append("Review discretionary spending to increase your savings rate.")
        if concentration > 60:
            recs.append("Diversify your portfolio — excessive crypto/equity concentration increases volatility.")
        if not recs:
            recs.append("Your financial risk profile is healthy. Focus on optimising returns.")
        return recs
