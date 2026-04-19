from .styles import *  # noqa: F401,F403
from .styles import (  # explicit re-exports for type checkers
    set_theme, get_theme_colors, get_color, build_stylesheet, THEMES,
    FM_UI, FM_BOLD, FM_H2, FM_SECTION, FM_TITLE, FM_TINY, FM_MONO,
)
from .theme_manager import ThemeManager  # noqa: F401


# Back-compat shim — legacy call sites may import apply_all_well_theme.
# The Qt port applies themes via QApplication.setStyleSheet(build_stylesheet(name))
# at startup / on theme change, so this function is a no-op that simply
# updates the current-theme tracker.
def apply_all_well_theme(_style=None, theme_name: str = None) -> None:  # noqa: D401
    if theme_name is not None:
        set_theme(theme_name)


def update_widget_colors(_widget, _color_map) -> None:  # no-op — QSS handles cascade
    pass


def rebuild_widget_colors(_widget, _old_theme: str, _new_theme: str) -> None:  # no-op
    pass
