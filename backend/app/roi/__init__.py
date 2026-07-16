"""Investment ROI calculator based on historical prices + cycle timing."""

from app.roi.calculator import calculate_roi
from app.roi.history import fetch_long_history

__all__ = ["calculate_roi", "fetch_long_history"]
