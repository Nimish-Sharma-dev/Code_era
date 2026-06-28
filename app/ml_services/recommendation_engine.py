"""
Personalized financial recommendation engine.

Design principle: recommendations NEVER consider only market conditions.
Every recommendation is filtered through the user's complete financial
picture: debts, emergency fund, savings rate, risk tolerance, and goals.

Priority ordering (financial planning best practice):
  1. Emergency fund (≥3 months expenses)
  2. High-interest debt payoff (>7% APR)
  3. Retirement / tax-advantaged savings
  4. Medium-term goals
  5. Investment optimisation
  6. Crypto / speculative (only after 1-4 are solid)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import uuid

from app.core.logging import get_logger
from app.ml_services.risk_engine import RiskProfile

logger = get_logger(__name__)


class RecommendationPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    OPTIONAL = 5


@dataclass
class FinancialRecommendation:
    """A single actionable financial recommendation with full context."""
    action: str                      # buy/sell/hold/pay_debt/build_emergency_fund/rebalance
    category: str                    # investment/debt/savings/insurance/crypto
    title: str
    explanation: str
    confidence_score: float          # 0.0–1.0
    priority: RecommendationPriority
    risk_level: str
    symbol: Optional[str] = None
    expected_roi: Optional[float] = None
    suggested_amount: Optional[float] = None
    rationale_factors: List[str] = field(default_factory=list)


class RecommendationEngine:
    """
    Holistic financial recommendation engine.

    Ingests the user's complete financial state and generates ranked,
    explainable recommendations. Each recommendation includes:
      - WHY it's being made (factors)
      - HOW CONFIDENT the system is
      - WHAT RISK it carries
      - HOW MUCH to act on it
    """

    EMERGENCY_FUND_MONTHS = 6
    HIGH_INTEREST_THRESHOLD = 0.07   # 7% APR
    MEDIUM_INTEREST_THRESHOLD = 0.04  # 4% APR
    MAX_CRYPTO_ALLOCATION = 0.05     # 5% of net worth

    def generate(
        self,
        *,
        user_id: str,
        risk_profile: RiskProfile,
        monthly_income: float,
        monthly_expenses: float,
        monthly_debt_payment: float,
        total_cash: float,
        total_debt: float,
        portfolio_value: float,
        crypto_value: float,
        loans: List[Dict],
        goals: List[Dict],
        investments: List[Dict],
        market_predictions: List[Dict],
        portfolio_sentiment: Dict[str, float],
        risk_tolerance: str,
    ) -> List[FinancialRecommendation]:
        """
        Generate a prioritised list of financial recommendations.

        This is the core orchestration method. It evaluates every financial
        domain in priority order, then merges and deduplicates.
        """
        recommendations: List[FinancialRecommendation] = []

        monthly_savings = monthly_income - monthly_expenses - monthly_debt_payment
        emergency_fund_months = total_cash / monthly_expenses if monthly_expenses > 0 else 0
        net_worth = total_cash + portfolio_value + crypto_value - total_debt
        dti = monthly_debt_payment / monthly_income if monthly_income > 0 else 0

        # ── Layer 1: Emergency Fund ───────────────────────────────────────────
        ef_recs = self._emergency_fund_recommendations(
            total_cash, monthly_expenses, emergency_fund_months, monthly_savings
        )
        recommendations.extend(ef_recs)

        # ── Layer 2: High-Interest Debt ───────────────────────────────────────
        # Only after emergency fund is at 3+ months
        if emergency_fund_months >= 3:
            debt_recs = self._debt_recommendations(loans, monthly_savings, monthly_income)
            recommendations.extend(debt_recs)

        # ── Layer 3: Savings Goals ────────────────────────────────────────────
        if emergency_fund_months >= 3 and dti <= 0.36:
            goal_recs = self._goal_recommendations(goals, monthly_savings)
            recommendations.extend(goal_recs)

        # ── Layer 4: Investment Optimisation ──────────────────────────────────
        # Only when financial foundation is solid
        if (emergency_fund_months >= 3 and risk_profile.overall_score < 60):
            invest_recs = self._investment_recommendations(
                investments, market_predictions, portfolio_sentiment,
                risk_tolerance, monthly_savings, total_debt, net_worth
            )
            recommendations.extend(invest_recs)

        # ── Layer 5: Crypto Allocation ────────────────────────────────────────
        if (emergency_fund_months >= 6 and risk_profile.overall_score < 50
                and risk_tolerance in ("aggressive", "speculative")):
            crypto_recs = self._crypto_recommendations(
                crypto_value, net_worth, portfolio_sentiment
            )
            recommendations.extend(crypto_recs)

        # ── Layer 6: Portfolio Rebalancing ────────────────────────────────────
        if investments:
            rebalance_recs = self._rebalancing_recommendations(
                investments, risk_tolerance, net_worth
            )
            recommendations.extend(rebalance_recs)

        # Sort by priority then confidence
        recommendations.sort(key=lambda r: (r.priority.value, -r.confidence_score))
        logger.info(
            "Recommendations generated",
            user_id=user_id,
            count=len(recommendations),
            risk_score=risk_profile.overall_score,
        )
        return recommendations[:15]  # Cap at 15 actionable recommendations

    def _emergency_fund_recommendations(
        self, total_cash: float, monthly_expenses: float,
        current_months: float, monthly_savings: float
    ) -> List[FinancialRecommendation]:
        recs = []
        if monthly_expenses <= 0:
            return recs

        if current_months < 1:
            months_to_min = max(0, 3 - current_months)
            amount_needed = months_to_min * monthly_expenses
            recs.append(FinancialRecommendation(
                action="build_emergency_fund",
                category="savings",
                title="🚨 Emergency Fund Critical — Build Immediately",
                explanation=(
                    f"You have less than 1 month of expenses in liquid savings. "
                    f"This is your #1 financial priority. Aim to save "
                    f"${amount_needed:,.0f} before taking any other financial action. "
                    f"Job loss, medical bills, or car repairs could devastate your finances."
                ),
                confidence_score=0.99,
                priority=RecommendationPriority.CRITICAL,
                risk_level="low",
                suggested_amount=min(monthly_savings * 0.8, monthly_expenses),
                rationale_factors=["No liquid safety net", "High financial fragility"],
            ))
        elif current_months < 3:
            recs.append(FinancialRecommendation(
                action="build_emergency_fund",
                category="savings",
                title="⚠️ Increase Emergency Fund to 3 Months",
                explanation=(
                    f"Your emergency fund covers {current_months:.1f} months. "
                    f"Prioritise building this to 3 months (${3 * monthly_expenses:,.0f}) "
                    f"before aggressive investing or debt overpayment."
                ),
                confidence_score=0.95,
                priority=RecommendationPriority.HIGH,
                risk_level="low",
                suggested_amount=min(monthly_savings * 0.5, monthly_expenses * 0.5),
                rationale_factors=["Below minimum emergency fund", "Financial vulnerability"],
            ))
        elif current_months < self.EMERGENCY_FUND_MONTHS:
            recs.append(FinancialRecommendation(
                action="build_emergency_fund",
                category="savings",
                title="Build Emergency Fund to 6 Months",
                explanation=(
                    f"You have {current_months:.1f} months covered. "
                    f"Increasing to 6 months provides resilience against prolonged job loss."
                ),
                confidence_score=0.80,
                priority=RecommendationPriority.MEDIUM,
                risk_level="low",
                suggested_amount=monthly_savings * 0.3,
                rationale_factors=["Below ideal emergency fund level"],
            ))
        return recs

    def _debt_recommendations(
        self, loans: List[Dict], monthly_savings: float, monthly_income: float
    ) -> List[FinancialRecommendation]:
        recs = []
        if not loans or monthly_savings <= 0:
            return recs

        # Sort by interest rate descending (avalanche method)
        sorted_loans = sorted(loans, key=lambda l: l.get("interest_rate", 0), reverse=True)

        for loan in sorted_loans:
            rate = loan.get("interest_rate", 0) / 100
            balance = loan.get("current_balance", 0)
            name = loan.get("name", "Loan")

            if rate > self.HIGH_INTEREST_THRESHOLD:
                extra_payment = min(monthly_savings * 0.4, balance * 0.1)
                recs.append(FinancialRecommendation(
                    action="pay_debt",
                    category="debt",
                    title=f"💸 Aggressively Pay Off {name} ({rate*100:.1f}% APR)",
                    explanation=(
                        f"At {rate*100:.1f}% APR, every dollar paid reduces guaranteed interest "
                        f"cost. Paying ${extra_payment:,.0f}/month extra on this loan "
                        f"likely outperforms most market investments after tax."
                    ),
                    confidence_score=0.92,
                    priority=RecommendationPriority.HIGH,
                    risk_level="low",
                    suggested_amount=extra_payment,
                    rationale_factors=[
                        f"High APR ({rate*100:.1f}%) exceeds expected market returns",
                        "Risk-free guaranteed 'return' by eliminating interest cost",
                    ],
                ))
            elif rate > self.MEDIUM_INTEREST_THRESHOLD:
                recs.append(FinancialRecommendation(
                    action="pay_debt",
                    category="debt",
                    title=f"Consider Overpaying {name} ({rate*100:.1f}% APR)",
                    explanation=(
                        f"At {rate*100:.1f}% APR this debt is in the borderline zone. "
                        f"Consider splitting extra cash 50/50 between this debt and investments."
                    ),
                    confidence_score=0.70,
                    priority=RecommendationPriority.MEDIUM,
                    risk_level="low",
                    rationale_factors=["Medium APR — borderline vs investing"],
                ))
            break  # One debt recommendation at a time (highest priority first)

        return recs

    def _goal_recommendations(
        self, goals: List[Dict], monthly_savings: float
    ) -> List[FinancialRecommendation]:
        recs = []
        if not goals or monthly_savings <= 0:
            return recs

        top_goal = min(goals, key=lambda g: g.get("priority", 99))
        progress = top_goal.get("current_amount", 0) / max(top_goal.get("target_amount", 1), 1)

        recs.append(FinancialRecommendation(
            action="increase",
            category="savings",
            title=f"Contribute to Goal: {top_goal.get('name', 'Top Goal')}",
            explanation=(
                f"Your top priority goal is {progress*100:.0f}% funded. "
                f"Allocate ${min(monthly_savings*0.3, 500):,.0f}/month to reach it faster."
            ),
            confidence_score=0.75,
            priority=RecommendationPriority.MEDIUM,
            risk_level="low",
            suggested_amount=min(monthly_savings * 0.3, 500),
            rationale_factors=["Goal-based saving maintains financial motivation"],
        ))
        return recs

    def _investment_recommendations(
        self, investments: List[Dict], predictions: List[Dict],
        sentiment: Dict[str, float], risk_tolerance: str,
        monthly_savings: float, total_debt: float, net_worth: float
    ) -> List[FinancialRecommendation]:
        recs = []
        allocation = min(monthly_savings * 0.4, monthly_savings * 0.6) if total_debt == 0 else monthly_savings * 0.25

        for pred in predictions[:3]:
            symbol = pred.get("symbol", "")
            direction = pred.get("direction", "neutral")
            confidence = pred.get("confidence", 0.5)
            sent_score = sentiment.get(symbol, 0.0)

            if (direction == "bullish" and confidence >= 0.65 and sent_score >= 0):
                recs.append(FinancialRecommendation(
                    action="buy",
                    category="investment",
                    symbol=symbol,
                    title=f"📈 Consider Adding {symbol} to Portfolio",
                    explanation=(
                        f"ML model predicts {direction} direction for {symbol} "
                        f"with {confidence*100:.0f}% confidence. "
                        f"News sentiment score: {sent_score:+.2f}. "
                        f"Suggested allocation: ${allocation:,.0f} based on your savings rate. "
                        f"This recommendation accounts for your current debt load and risk profile."
                    ),
                    confidence_score=confidence * (0.8 + 0.2 * min(abs(sent_score), 1.0)),
                    priority=RecommendationPriority.MEDIUM,
                    risk_level="moderate" if risk_tolerance in ("moderate", "aggressive") else "high",
                    expected_roi=None,  # No guaranteed ROI
                    suggested_amount=allocation,
                    rationale_factors=[
                        f"ML prediction: {direction} ({confidence*100:.0f}% confidence)",
                        f"News sentiment: {sent_score:+.2f}",
                        "Financial foundation verified before this recommendation",
                    ],
                ))
            elif direction == "bearish" and confidence >= 0.70:
                existing = next((i for i in investments if i.get("symbol") == symbol), None)
                if existing:
                    recs.append(FinancialRecommendation(
                        action="reduce",
                        category="investment",
                        symbol=symbol,
                        title=f"⚠️ Consider Reducing {symbol} Exposure",
                        explanation=(
                            f"Bearish prediction for {symbol} ({confidence*100:.0f}% confidence). "
                            f"Negative sentiment score: {sent_score:+.2f}. Consider reducing position."
                        ),
                        confidence_score=confidence,
                        priority=RecommendationPriority.HIGH,
                        risk_level="moderate",
                        rationale_factors=[
                            f"Bearish ML signal ({confidence*100:.0f}%)",
                            f"Negative news sentiment",
                        ],
                    ))
        return recs

    def _crypto_recommendations(
        self, crypto_value: float, net_worth: float, sentiment: Dict[str, float]
    ) -> List[FinancialRecommendation]:
        recs = []
        if net_worth <= 0:
            return recs
        crypto_pct = crypto_value / net_worth
        if crypto_pct > self.MAX_CRYPTO_ALLOCATION:
            recs.append(FinancialRecommendation(
                action="reduce",
                category="crypto",
                title="⚠️ Reduce Crypto Allocation",
                explanation=(
                    f"Crypto is {crypto_pct*100:.1f}% of net worth — exceeds the recommended 5% max "
                    f"for most risk profiles. Consider rebalancing to reduce volatility exposure."
                ),
                confidence_score=0.85,
                priority=RecommendationPriority.HIGH,
                risk_level="high",
                rationale_factors=["Crypto allocation exceeds safe threshold"],
            ))
        return recs

    def _rebalancing_recommendations(
        self, investments: List[Dict], risk_tolerance: str, net_worth: float
    ) -> List[FinancialRecommendation]:
        recs = []
        if not investments or net_worth <= 0:
            return recs

        target_allocations = {
            "conservative": {"bond": 0.60, "equity": 0.30, "cash": 0.10},
            "moderate":     {"bond": 0.40, "equity": 0.50, "etf": 0.10},
            "aggressive":   {"equity": 0.70, "etf": 0.20, "bond": 0.10},
            "speculative":  {"equity": 0.60, "crypto": 0.20, "etf": 0.20},
        }
        target = target_allocations.get(risk_tolerance, target_allocations["moderate"])

        type_values: Dict[str, float] = {}
        for inv in investments:
            asset_type = inv.get("asset_class", "equity")
            type_values[asset_type] = type_values.get(asset_type, 0) + inv.get("current_value", 0)

        total_inv = sum(type_values.values())
        if total_inv < 1000:
            return recs

        drifted = []
        for asset_type, target_pct in target.items():
            actual_pct = type_values.get(asset_type, 0) / total_inv
            drift = abs(actual_pct - target_pct)
            if drift > 0.05:  # 5% drift threshold
                drifted.append((asset_type, actual_pct, target_pct))

        if drifted:
            drift_descriptions = ", ".join(
                f"{t} ({a*100:.0f}% vs {tgt*100:.0f}% target)"
                for t, a, tgt in drifted
            )
            recs.append(FinancialRecommendation(
                action="rebalance",
                category="investment",
                title="🔄 Portfolio Rebalancing Needed",
                explanation=(
                    f"Your portfolio has drifted from your {risk_tolerance} target allocation. "
                    f"Drifted assets: {drift_descriptions}. "
                    f"Rebalancing annually reduces risk and enforces buy-low/sell-high discipline."
                ),
                confidence_score=0.80,
                priority=RecommendationPriority.LOW,
                risk_level="low",
                rationale_factors=["Allocation drift >5% from target", "Annual rebalance discipline"],
            ))
        return recs
