"""Reusable Streamlit UI components for the Golf Caddy app."""

from __future__ import annotations

from html import escape

import streamlit as st

from agents.pipeline import PipelineResult
from models import Course, Hole, PlayerProfile, ShotIntent, TeeBox, WeatherObservation
from ui.styles import CONFIDENCE_LABELS


def _ordered_club_rows(player_profile: PlayerProfile) -> list[tuple[str, float]]:
    return sorted(player_profile.club_distances.items(), key=lambda item: item[1], reverse=True)


def _humanize_flag(flag: str) -> str:
    return flag.replace("_", " ").strip().title()


def render_page_hero() -> None:
    """Render the landing hero and quick usage steps."""
    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-copy">
                <div class="hero-kicker">Agentic Golf Caddy</div>
                <h1>Pick a smarter club with context you can actually trust.</h1>
                <p>
                    Keep the shot distance in control, layer in course and live-condition context,
                    and see why the caddie chose the club instead of getting a black-box answer.
                </p>
            </div>
            <div class="hero-steps">
                <div class="hero-step">
                    <span>1</span>
                    <strong>Set the player and course</strong>
                    <small>Use the sidebar to choose the profile, hole, tee, and pin.</small>
                </div>
                <div class="hero-step">
                    <span>2</span>
                    <strong>Enter the shot your way</strong>
                    <small>Use structured fields or describe the situation in plain English.</small>
                </div>
                <div class="hero-step">
                    <span>3</span>
                    <strong>Review the fit and reasoning</strong>
                    <small>See the recommendation, adjustments, backup club, and feedback tools.</small>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_setup_snapshot(
    player_profile: PlayerProfile,
    profile_status: str,
    course: Course | None,
    hole: Hole | None,
    tee: TeeBox | None,
    weather: WeatherObservation | None,
    *,
    manual_weather_only: bool,
    pin_position: str | None = None,
) -> None:
    """Render a compact summary of the active recommendation setup."""
    course_value = "Manual entry" if course is None or hole is None else escape(course.name)
    course_meta = "No saved hole selected" if course is None or hole is None else f"Hole {hole.number}"
    tee_label = tee.label if tee is not None else "None selected"
    pin_label = pin_position.replace("_", " ").title() if pin_position else "Not set"
    if manual_weather_only or weather is None:
        weather_value = "Manual"
        weather_meta = "Using typed conditions"
    else:
        weather_value = f"{weather.wind_speed_mph:.0f} mph"
        weather_meta = f"{weather.temperature_f:.0f} F"

    cards = [
        ("Player profile", escape(player_profile.name), escape(profile_status)),
        ("Course", course_value, escape(course_meta)),
        ("Tee / Pin", escape(tee_label), escape(pin_label)),
        ("Conditions", weather_value, escape(weather_meta)),
    ]
    card_html = "".join(
        f"""
        <div class="setup-card">
            <div class="setup-label">{label}</div>
            <div class="setup-value">{value}</div>
            <div class="setup-meta">{meta}</div>
        </div>
        """
        for label, value, meta in cards
    )
    st.markdown(
        f"""
        <div class="setup-shell">
            <div class="section-eyebrow">Active Setup</div>
            <div class="setup-grid">{card_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_context_summary(result: PipelineResult) -> None:
    """Render the normalized shot context used by the recommendation."""
    shot_context = result.shot_context
    if shot_context is None:
        return

    details = [
        f"{shot_context.distance_to_target:.0f} yds",
        f"lie: {shot_context.lie_type.value}",
        f"target: {shot_context.target_mode.value.replace('_', ' ')}",
    ]
    if shot_context.pin_position is not None:
        details.append(f"pin: {shot_context.pin_position.value}")
    if shot_context.hazard_note:
        details.append(f"hazard: {shot_context.hazard_note}")
    if shot_context.player_confidence is not None:
        details.append(f"player confidence: {shot_context.player_confidence}/5")

    pills = "".join(
        f'<span class="context-pill">{escape(detail)}</span>'
        for detail in details
    )
    st.markdown(
        f"""
        <div class="context-shell">
            <div class="section-eyebrow">Recommendation Context</div>
            <div class="pill-row">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_club_banner(result: PipelineResult) -> None:
    """Render the primary club recommendation banner."""
    decision = result.decision
    delta = round(decision.plays_like_distance - decision.actual_distance, 1)
    delta_text = f"{delta:+.0f}" if delta != 0 else "0"

    st.markdown(
        f"""<div class="club-banner">
            <p class="club-name">{decision.primary_club.upper()}</p>
            <p class="plays-like">
                Plays like {decision.plays_like_distance:.0f} yds
                ({delta_text} from {decision.actual_distance:.0f} yds actual)
            </p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_confidence_badge(confidence_value: str) -> None:
    """Render a color-coded confidence indicator."""
    label = CONFIDENCE_LABELS.get(confidence_value, confidence_value)
    css_class = f"confidence-{confidence_value}"
    st.markdown(
        f'<span class="confidence-badge {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


def render_adjustment_breakdown(adjustments: dict[str, float]) -> None:
    """Render itemized yard adjustments as a styled list."""
    st.markdown("##### Adjustment Breakdown")

    non_zero = {k: v for k, v in adjustments.items() if v != 0.0}
    if not non_zero:
        st.caption("No adjustments — clean conditions.")
        return

    for name, value in adjustments.items():
        if value > 0:
            css = "adj-value-pos"
            sign = f"+{value:.1f}"
        elif value < 0:
            css = "adj-value-neg"
            sign = f"{value:.1f}"
        else:
            css = "adj-value-zero"
            sign = "0.0"

        label_map = {
            "wind": "Wind",
            "elevation": "Elevation",
            "lie": "Lie",
            "temperature": "Temperature",
            "altitude": "Altitude",
        }
        display_name = label_map.get(name, name.capitalize())

        st.markdown(
            f"""<div class="adj-row">
                <span class="adj-label">{display_name}</span>
                <span class="{css}">{sign} yds</span>
            </div>""",
            unsafe_allow_html=True,
        )


def render_backup_card(result: PipelineResult, player_profile: PlayerProfile) -> None:
    """Render the backup club suggestion card."""
    decision = result.decision
    explanation = result.explanation
    backup_dist = player_profile.club_distances.get(
        decision.backup_club, decision.plays_like_distance
    )

    st.markdown(
        f"""<div class="backup-card">
            <div class="backup-title">Backup: {decision.backup_club} ({backup_dist:.0f} avg)</div>
            <div class="backup-detail">{explanation.backup_note}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_explanation(result: PipelineResult) -> None:
    """Render the Coach Agent's explanation text."""
    explanation = result.explanation
    if explanation is None:
        return
    st.markdown(
        f"""<div class="explanation-card">
            <strong>{explanation.summary}</strong><br/>
            {explanation.detail}
        </div>""",
        unsafe_allow_html=True,
    )


def render_plays_like_metric(result: PipelineResult) -> None:
    """Render the plays-like distance as a Streamlit metric."""
    decision = result.decision
    if decision is None:
        return
    delta = round(decision.plays_like_distance - decision.actual_distance, 1)
    st.markdown(
        f"""
        <div class="section-eyebrow">Distance Summary</div>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-label">Actual Distance</div>
                <div class="stat-value">{decision.actual_distance:.0f} <span>yds</span></div>
                <div class="stat-meta">Measured shot distance</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Plays-Like Distance</div>
                <div class="stat-value">{decision.plays_like_distance:.0f} <span>yds</span></div>
                <div class="stat-meta">{delta:+.1f} yards from actual after conditions</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_fit(result: PipelineResult, player_profile: PlayerProfile) -> None:
    """Show how well the selected clubs fit the normalized shot distance."""
    decision = result.decision
    if decision is None:
        return

    primary_distance = player_profile.club_distances.get(decision.primary_club, decision.plays_like_distance)
    backup_distance = player_profile.club_distances.get(decision.backup_club, decision.plays_like_distance)
    primary_gap = round(primary_distance - decision.plays_like_distance, 1)
    backup_gap = round(backup_distance - decision.plays_like_distance, 1)
    adaptive_shift = (
        "Yes"
        if result.deterministic_decision is not None
        and result.deterministic_decision.primary_club != decision.primary_club
        else "No"
    )

    st.markdown(
        f"""
        <div class="section-eyebrow">Recommendation Fit</div>
        <div class="fit-grid">
            <div class="fit-card">
                <div class="fit-label">Primary carry gap</div>
                <div class="fit-value">{primary_gap:+.1f} yds</div>
                <div class="fit-meta">{escape(decision.primary_club)} against plays-like number</div>
            </div>
            <div class="fit-card">
                <div class="fit-label">Backup carry gap</div>
                <div class="fit-value">{backup_gap:+.1f} yds</div>
                <div class="fit-meta">{escape(decision.backup_club)} as the alternate option</div>
            </div>
            <div class="fit-card">
                <div class="fit-label">Adaptive change</div>
                <div class="fit-value">{adaptive_shift}</div>
                <div class="fit-meta">Whether adaptive strategy changed the final club</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_strategy_note(result: PipelineResult) -> None:
    """Render the strategy-specific decision note."""
    if result.decision is not None:
        st.caption(result.decision.strategy_note)


def render_shot_intent_card(shot_intent: ShotIntent) -> None:
    """Render parsed shot intent from natural-language input."""
    st.markdown(
        f"""<div class="intent-card">
            <div class="intent-title">Parsed Shot Intent</div>
            <div class="intent-detail">{shot_intent.user_facing_summary or "Shot parsed from natural language."}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_clarification_card(result: PipelineResult) -> None:
    """Render the clarification question if the pipeline needs more information."""
    clarification = result.clarification
    if clarification is None or not clarification.needs_clarification:
        return

    st.warning(clarification.question or "One more clarification is needed before recommending a club.")
    st.caption(clarification.reason)


def render_adaptive_strategy(result: PipelineResult) -> None:
    """Render the adaptive strategy note chosen from bounded club candidates."""
    adaptive = result.adaptive_decision
    if adaptive is None:
        return

    risk_flags = ", ".join(_humanize_flag(flag) for flag in adaptive.risk_flags) if adaptive.risk_flags else "No special risk flags"
    st.markdown(
        f"""<div class="adaptive-card">
            <div class="adaptive-title">Adaptive Caddie Note</div>
            <div class="adaptive-detail"><strong>Target line:</strong> {escape(adaptive.target_line.title())}</div>
            <div class="adaptive-detail">{adaptive.strategy_rationale}</div>
            <div class="adaptive-detail"><strong>Risk flags:</strong> {risk_flags}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_verification_note(result: PipelineResult) -> None:
    """Render verifier status when the explanation needed correction."""
    verification = result.verification
    if verification is None:
        return

    if verification.corrected_output_used:
        st.info("Verifier corrected the final explanation to keep it grounded in the actual decision data.")
    elif verification.issues:
        st.caption(f"Verifier notes: {'; '.join(verification.issues)}")


def render_debug_panel(result: PipelineResult) -> None:
    """Render raw JSON output from each agent step in an expander."""
    with st.expander("Debug: Raw Agent Outputs", expanded=False):
        if result.shot_intent is not None:
            st.markdown("**Input Interpreter — ShotIntent:**")
            st.json(result.shot_intent.model_dump(mode="json"))

        if result.clarification is not None:
            st.markdown("**Clarification Agent:**")
            st.json(result.clarification.model_dump(mode="json"))

        st.markdown("**Agent 1 — ShotContext:**")
        st.json(result.shot_context.model_dump(mode="json") if result.shot_context is not None else {})

        if result.deterministic_decision is not None:
            st.markdown("**Agent 2 — Deterministic Decision:**")
            st.json(result.deterministic_decision.model_dump(mode="json"))

        if result.candidate_options:
            st.markdown("**Adaptive Candidate Options:**")
            st.json([option.model_dump(mode="json") for option in result.candidate_options])

        if result.adaptive_decision is not None:
            st.markdown("**Adaptive Strategy Decision:**")
            st.json(result.adaptive_decision.model_dump(mode="json"))

        if result.decision is not None:
            st.markdown("**Final Decision:**")
            st.json(result.decision.model_dump(mode="json"))

        if result.explanation is not None:
            st.markdown("**Coach Agent — Explanation:**")
            st.json(result.explanation.model_dump(mode="json"))

        if result.verification is not None:
            st.markdown("**Verifier Agent:**")
            st.json(result.verification.model_dump(mode="json"))

        if result.timing:
            st.markdown("**Pipeline Timing:**")
            st.json(result.timing)


def render_footer() -> None:
    """Render the app footer."""
    st.markdown(
        '<div class="app-footer">Agentic Golf Caddy &mdash; '
        "A Multi-Agent AI System for Golf Club Recommendation"
        "<br/>"
        "Live data attribution: Open-Meteo weather, OpenStreetMap Nominatim geocoding, USGS elevation."
        "</div>",
        unsafe_allow_html=True,
    )


def render_profile_distances(player_profile: PlayerProfile) -> None:
    """Render club distances sorted from longest to shortest."""
    rows = "".join(
        f"""
        <div class="profile-row">
            <span class="profile-club">{escape(club)}</span>
            <span class="profile-distance">{dist:.0f} yds</span>
        </div>
        """
        for club, dist in _ordered_club_rows(player_profile)
    )
    st.markdown(
        f'<div class="profile-table">{rows}</div>',
        unsafe_allow_html=True,
    )
