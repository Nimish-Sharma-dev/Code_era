from typing import Dict, Any, List


def prune_strategies_by_risk(user_profile: Dict[str, Any], strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter investment strategies based on user risk tolerance."""
    max_risk = user_profile.get("risk_score", 0.5)
    return [strategy for strategy in strategies if strategy.get("risk", 1.0) <= max_risk]
