# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""UI modules for the Streamlit Golf Caddy application."""

from ui.components import (
    render_adjustment_breakdown,
    render_backup_card,
    render_club_banner,
    render_confidence_badge,
    render_debug_panel,
    render_explanation,
    render_footer,
    render_plays_like_metric,
    render_strategy_note,
)
from ui.scenarios import SAMPLE_SCENARIOS, Scenario
from ui.styles import APP_CSS, CONFIDENCE_COLORS, CONFIDENCE_LABELS

__all__ = [
    "APP_CSS",
    "CONFIDENCE_COLORS",
    "CONFIDENCE_LABELS",
    "SAMPLE_SCENARIOS",
    "Scenario",
    "render_adjustment_breakdown",
    "render_backup_card",
    "render_club_banner",
    "render_confidence_badge",
    "render_debug_panel",
    "render_explanation",
    "render_footer",
    "render_plays_like_metric",
    "render_strategy_note",
]
