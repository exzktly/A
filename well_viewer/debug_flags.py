"""Shared runtime debug toggles for the All-Well app.

Flags are grouped by UI tab so debug output can be enabled per-tab.
"""

# Master switches by tab
REVIEW_TAB_DEBUG: bool = False
ANALYZE_TAB_DEBUG: bool = False

# Review tab debug switches
REVIEW_BAR_DEBUG: bool = False
REVIEW_SCATTER_DEBUG: bool = False
REVIEW_IMAGE_DEBUG: bool = False

# Movie Montage tab debug switches
MOVIE_MONTAGE_DEBUG: bool = False

# Backward-compatible alias used by older call sites.
# Keep this until all imports are migrated.
BAR_DEBUG: bool = REVIEW_BAR_DEBUG


def review_bar_debug_enabled() -> bool:
    """Return whether Review tab bar-plot debug output is enabled."""
    return REVIEW_TAB_DEBUG and REVIEW_BAR_DEBUG


def review_scatter_debug_enabled() -> bool:
    """Return whether Review tab scatter debug output is enabled."""
    return REVIEW_TAB_DEBUG and REVIEW_SCATTER_DEBUG


def review_image_debug_enabled() -> bool:
    """Return whether Review Image tab debug output is enabled."""
    return REVIEW_TAB_DEBUG and REVIEW_IMAGE_DEBUG


def movie_montage_debug_enabled() -> bool:
    """Return whether Movie Montage tab debug output is enabled."""
    return REVIEW_TAB_DEBUG and MOVIE_MONTAGE_DEBUG
