"""Theme manager for handling dynamic theme switching."""

from __future__ import annotations

from typing import Callable, List


class ThemeManager:
    """Manages application-wide theme switching and callbacks.

    This class maintains the current theme state and notifies registered
    callbacks when the theme changes, allowing UI components to update
    their appearance dynamically.
    """

    def __init__(self, initial_theme: str = "Dark"):
        """Initialize the theme manager.

        Args:
            initial_theme: Starting theme name ("Dark" or "Light")
        """
        self._current_theme = initial_theme
        self._callbacks: List[Callable[[str], None]] = []

    @property
    def current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Set the current theme and notify all registered callbacks.

        Args:
            theme_name: Theme to switch to ("Dark" or "Light")
        """
        if theme_name != self._current_theme:
            self._current_theme = theme_name
            self._notify_callbacks()

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback to be called when theme changes.

        The callback will be invoked with the new theme name as argument.

        Args:
            callback: Function that takes theme_name (str) as argument
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str], None]) -> None:
        """Unregister a previously registered callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of theme change."""
        for callback in self._callbacks:
            try:
                callback(self._current_theme)
            except Exception as e:
                print(f"Error in theme callback: {e}")

    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return ["Dark", "Light"]
