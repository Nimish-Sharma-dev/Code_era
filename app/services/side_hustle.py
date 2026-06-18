from typing import Dict, Any, List


def generate_side_hustle_recommendations(user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate simple low-capital alternative recommendations."""
    return [
        {"title": "Review recurring subscriptions", "impact": "Reduce monthly burn rate"},
        {"title": "Set up automated savings round-ups", "impact": "Increase cash reserves"},
    ]
