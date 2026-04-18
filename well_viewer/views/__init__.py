"""Non-notebook view builders and reusable UI components.

`well_viewer.views` is for shared layout/panel/widget builders that are
composed by the runtime and by tab builders, e.g. sidebars, status areas,
preview/image panels, and reusable widgets.

Rule of thumb:
    - If a module builds one page inside the centre notebook, it belongs in
      ``well_viewer.tabs``.
    - If a module builds reusable pieces used across pages (or outside the
      centre notebook), it belongs in ``well_viewer.views``.
"""
