from ui.qt_theme import build_stylesheet, theme_names


def test_theme_names_contains_dark_light() -> None:
    names = theme_names()
    assert "Dark" in names
    assert "Light" in names


def test_stylesheet_contains_core_selectors() -> None:
    css = build_stylesheet("Dark")
    assert "QWidget" in css
    assert "QPushButton" in css
    assert "QTabBar::tab" in css
    assert "#2563eb" in css
