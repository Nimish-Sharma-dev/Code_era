from typing import Dict, Any


def calculate_debt_vs_asset_roi(loan: Dict[str, Any], asset_signal: Dict[str, Any]) -> float:
    """Calculate a simplified ROI differential between a loan and an asset."""
    loan_rate = loan.get("interest_rate", 0.0)
    asset_return = asset_signal.get("expected_return", 0.0)
    return asset_return - loan_rate
