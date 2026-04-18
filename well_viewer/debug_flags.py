"""Shared runtime debug toggles for the All-Well app.

Flags are grouped by UI tab so debug output can be enabled per-tab.
"""

# Master switches by tab
REVIEW_TAB_DEBUG: bool = False
ANALYZE_TAB_DEBUG: bool = False

# Review tab debug switches
REVIEW_BAR_DEBUG: bool = False
REVIEW_SCATTER_DEBUG: bool = False

# Backward-compatible alias used by older call sites.
# Keep this until all imports are migrated.
BAR_DEBUG: bool = REVIEW_BAR_DEBUG


def review_bar_debug_enabled() -> bool:
    """Return whether Review tab bar-plot debug output is enabled."""
    return REVIEW_TAB_DEBUG and REVIEW_BAR_DEBUG


def review_scatter_debug_enabled() -> bool:
    """Return whether Review tab scatter debug output is enabled."""
    return REVIEW_TAB_DEBUG and REVIEW_SCATTER_DEBUG
