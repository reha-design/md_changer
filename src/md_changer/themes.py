"""Built-in document themes and CSS layer composition."""

from dataclasses import dataclass
from collections.abc import Mapping
from types import MappingProxyType

from md_changer.styles import COMMON_PRINT_CSS


@dataclass(frozen=True)
class ThemeDefinition:
    """A named document and Mermaid color theme."""

    name: str
    label: str
    css: str
    mermaid_theme: str
    mermaid_variables: Mapping[str, str]


THEMES = (
    ThemeDefinition(
        name="default",
        label="기본",
        css="",
        mermaid_theme="default",
        mermaid_variables=MappingProxyType({
            "primaryColor": "#f6f8fa",
            "primaryTextColor": "#202124",
            "lineColor": "#57606a",
        }),
    ),
    ThemeDefinition(
        name="modern",
        label="모던",
        css="""
body { color: #1f2937; }
h1, h2, h3, h4, h5, h6 { color: #0f4c81; margin-top: 1.45em; }
h1 { border-bottom-color: #93c5fd; font-size: 30px; }
h2 { border-bottom-color: #bfdbfe; font-size: 24px; }
a { color: #2563eb; }
""",
        mermaid_theme="base",
        mermaid_variables=MappingProxyType({
            "primaryColor": "#dbeafe",
            "primaryTextColor": "#0f4c81",
            "primaryBorderColor": "#2563eb",
            "lineColor": "#2563eb",
        }),
    ),
    ThemeDefinition(
        name="minimal",
        label="미니멀",
        css="""
body { color: #262626; }
h1, h2, h3, h4, h5, h6 { color: #171717; }
h1, h2 { border-bottom: 0; padding-bottom: 0; }
a { color: #404040; text-decoration: underline; }
blockquote { border-left-color: #a3a3a3; color: #525252; }
th { background: #fafafa; }
""",
        mermaid_theme="neutral",
        mermaid_variables=MappingProxyType({
            "primaryColor": "#f5f5f5",
            "primaryTextColor": "#262626",
            "primaryBorderColor": "#737373",
            "lineColor": "#525252",
        }),
    ),
    ThemeDefinition(
        name="report",
        label="문서/리포트",
        css="""
body { color: #334155; line-height: 1.55; }
h1, h2, h3, h4, h5, h6 { color: #1e3a5f; margin-top: 1.05em; }
h1 { border-bottom-color: #94a3b8; font-size: 27px; }
h2 { border-bottom-color: #cbd5e1; font-size: 21px; }
table { margin: 0.55em 0; }
th, td { border-color: #cbd5e1; padding: 5px 7px; }
th { background: #e2e8f0; }
a { color: #1e3a5f; }
""",
        mermaid_theme="base",
        mermaid_variables=MappingProxyType({
            "primaryColor": "#e2e8f0",
            "primaryTextColor": "#1e3a5f",
            "primaryBorderColor": "#64748b",
            "lineColor": "#475569",
        }),
    ),
)


def list_themes() -> tuple[ThemeDefinition, ...]:
    """Return built-in themes in their stable display order."""
    return THEMES


def get_theme(name: str) -> ThemeDefinition:
    """Return a built-in theme or explain which names are valid."""
    for theme in THEMES:
        if theme.name == name:
            return theme
    valid_names = ", ".join(theme.name for theme in THEMES)
    raise ValueError(f"Unknown theme {name!r}. Valid themes: {valid_names}")


def compose_css(theme: str = "default", custom_css: str | None = None) -> str:
    """Compose shared print, selected theme, and optional user CSS layers."""
    definition = get_theme(theme)
    layers = [
        "/* md-changer: common print CSS */\n" + COMMON_PRINT_CSS.strip(),
        f"/* md-changer: theme {definition.name} */\n" + definition.css.strip(),
    ]
    if custom_css is not None:
        layers.append("/* md-changer: custom CSS */\n" + custom_css)
    return "\n\n".join(layers) + "\n"
