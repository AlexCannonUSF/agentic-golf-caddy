"""Agentic Golf Caddy — Streamlit application."""

from __future__ import annotations

from datetime import date

import streamlit as st

try:
    import pydeck as pdk
except ImportError:  # pragma: no cover
    pdk = None  # type: ignore[assignment]

from agents.pipeline import Pipeline, PipelineResult
from evaluation.real_runs import render_real_run_report, summarize_real_runs
from models import Course, Elevation, Hole, HolePin, LatLon, PinPosition, PlayerProfile, ShotFeedback, ShotOutcome, SkillLevel, TeeBox, WeatherObservation
from models import RecommendationRating
from ui.components import (
    render_adaptive_strategy,
    render_adjustment_breakdown,
    render_backup_card,
    render_clarification_card,
    render_club_banner,
    render_confidence_badge,
    render_context_summary,
    render_debug_panel,
    render_explanation,
    render_footer,
    render_page_hero,
    render_plays_like_metric,
    render_profile_distances,
    render_recommendation_fit,
    render_setup_snapshot,
    render_shot_intent_card,
    render_strategy_note,
    render_verification_note,
)
from ui.scenarios import SAMPLE_SCENARIOS
from ui.styles import APP_CSS
from utils import (
    CourseManager,
    FeedbackManager,
    InputValidationError,
    PinManager,
    ProfileManager,
    RunRecorder,
    build_profile_from_shots,
    fetch_course,
    geocode,
    get_elevation,
    get_elevation_delta,
    get_weather,
    import_shot_file,
    parse_course_payload,
    save_imported_profile,
    slugify_player_id,
)
from utils.geometry import derive_pin_position, green_reference_points, haversine_yards
from utils.logger import setup_logging

setup_logging()

st.set_page_config(
    page_title="AI Golf Caddy",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

pm = ProfileManager()
course_manager = CourseManager()
pin_manager = PinManager()
feedback_manager = FeedbackManager()
run_recorder = RunRecorder()

if "skill_level" not in st.session_state:
    st.session_state.skill_level = "intermediate"

if "active_profile_key" not in st.session_state:
    st.session_state.active_profile_key = "default:intermediate"

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "latest_profile_name" not in st.session_state:
    st.session_state.latest_profile_name = None

if "location_query" not in st.session_state:
    st.session_state.location_query = ""

for key in ("location_lat", "location_lon", "target_lat", "target_lon", "shot_azimuth_deg"):
    if key not in st.session_state:
        st.session_state[key] = ""

if "use_manual_weather" not in st.session_state:
    st.session_state.use_manual_weather = True

if "live_weather_observation" not in st.session_state:
    st.session_state.live_weather_observation = None

if "live_altitude_ft" not in st.session_state:
    st.session_state.live_altitude_ft = None

if "live_elevation_value" not in st.session_state:
    st.session_state.live_elevation_value = None

if "location_status" not in st.session_state:
    st.session_state.location_status = None

if "location_error" not in st.session_state:
    st.session_state.location_error = None

if "uploaded_source_name" not in st.session_state:
    st.session_state.uploaded_source_name = None

if "upload_profile_name" not in st.session_state:
    st.session_state.upload_profile_name = ""

if "active_course_id" not in st.session_state:
    st.session_state.active_course_id = ""

if "course_osm_ref" not in st.session_state:
    st.session_state.course_osm_ref = "way/35679036"

if "selected_hole_number" not in st.session_state:
    st.session_state.selected_hole_number = 1

if "selected_tee_label" not in st.session_state:
    st.session_state.selected_tee_label = ""

if "course_status" not in st.session_state:
    st.session_state.course_status = None

if "course_error" not in st.session_state:
    st.session_state.course_error = None

if "pin_date" not in st.session_state:
    st.session_state.pin_date = date.today()

if "active_pin_source" not in st.session_state:
    st.session_state.active_pin_source = "saved"

if "custom_pin_lat" not in st.session_state:
    st.session_state.custom_pin_lat = ""

if "custom_pin_lon" not in st.session_state:
    st.session_state.custom_pin_lon = ""

if "pin_status" not in st.session_state:
    st.session_state.pin_status = None

if "pin_error" not in st.session_state:
    st.session_state.pin_error = None


def _store_result(result: PipelineResult, profile_name: str) -> None:
    st.session_state.latest_result = result
    st.session_state.latest_profile_name = profile_name


def _list_imported_profile_stems() -> list[str]:
    return sorted(
        stem for stem in pm.list_profiles() if stem.startswith("imported_")
    )


def _list_benchmark_profile_stems() -> list[str]:
    return sorted(
        stem for stem in pm.list_profiles() if stem.startswith("benchmark_")
    )


def _profile_option_metadata() -> tuple[list[str], dict[str, str]]:
    options: list[str] = []
    labels: dict[str, str] = {}

    for level in SkillLevel:
        key = f"default:{level.value}"
        options.append(key)
        labels[key] = f"Default: {level.value.replace('_', ' ').title()}"

    for stem in _list_imported_profile_stems():
        key = f"custom:{stem}"
        try:
            imported_profile = pm.load_profile(stem)
            labels[key] = f"Imported: {imported_profile.name}"
        except Exception:
            labels[key] = f"Imported: {stem.removeprefix('imported_').replace('_', ' ').title()}"
        options.append(key)

    for stem in _list_benchmark_profile_stems():
        key = f"benchmark:{stem}"
        try:
            benchmark_profile = pm.load_profile(stem)
            labels[key] = f"Benchmark: {benchmark_profile.name}"
        except Exception:
            labels[key] = f"Benchmark: {stem.removeprefix('benchmark_').replace('_', ' ').title()}"
        options.append(key)

    return options, labels


def _load_profile_for_key(profile_key: str) -> PlayerProfile:
    if profile_key.startswith("custom:"):
        return pm.load_profile(profile_key.split(":", 1)[1])
    if profile_key.startswith("benchmark:"):
        return pm.load_profile(profile_key.split(":", 1)[1])
    return pm.load_default_profile(profile_key.split(":", 1)[1])


def _course_option_metadata() -> tuple[list[str], dict[str, str]]:
    options = [""]
    labels = {"": "None"}
    for record in course_manager.list_course_records():
        course_id = str(record["id"])
        options.append(course_id)
        labels[course_id] = f"{record['name']} ({record['hole_count']} holes)"
    return options, labels


def _load_active_course() -> Course | None:
    course_id = st.session_state.active_course_id.strip()
    if not course_id:
        return None
    return course_manager.load_course(course_id)


def _get_selected_hole(course: Course | None) -> Hole | None:
    if course is None:
        return None

    available_numbers = [hole.number for hole in course.holes]
    if not available_numbers:
        return None

    if st.session_state.selected_hole_number not in available_numbers:
        st.session_state.selected_hole_number = available_numbers[0]

    for hole in course.holes:
        if hole.number == st.session_state.selected_hole_number:
            return hole
    return course.holes[0]


def _get_selected_tee(hole: Hole | None) -> TeeBox | None:
    if hole is None or not hole.tees:
        st.session_state.selected_tee_label = ""
        return None

    labels = [tee.label for tee in hole.tees]
    if st.session_state.selected_tee_label not in labels:
        st.session_state.selected_tee_label = labels[0]

    for tee in hole.tees:
        if tee.label == st.session_state.selected_tee_label:
            return tee
    return hole.tees[0]


def _selected_course_context() -> tuple[Course | None, Hole | None, TeeBox | None]:
    try:
        course = _load_active_course()
    except Exception:
        return None, None, None
    hole = _get_selected_hole(course)
    tee = _get_selected_tee(hole)
    return course, hole, tee


def _get_saved_pin(course: Course | None, hole: Hole | None) -> HolePin | None:
    if course is None or hole is None:
        return None
    return pin_manager.get_pin(course.id, hole.number, st.session_state.pin_date)


def _pin_source_options(saved_pin: HolePin | None) -> tuple[list[str], dict[str, str]]:
    options = ["none"]
    labels = {"none": "No pin override"}
    if saved_pin is not None:
        options.append("saved")
        labels["saved"] = "Saved daily pin"
    options.extend(["front", "middle", "back", "custom"])
    labels.update(
        {
            "front": "Front preset",
            "middle": "Middle preset",
            "back": "Back preset",
            "custom": "Custom coordinates",
        }
    )
    return options, labels


def _resolve_active_pin(
    course: Course | None,
    hole: Hole | None,
    tee: TeeBox | None,
) -> tuple[LatLon | None, str | None, HolePin | None]:
    saved_pin = _get_saved_pin(course, hole)
    if course is None or hole is None or tee is None:
        return None, None, saved_pin

    source = st.session_state.active_pin_source
    if source == "saved":
        if saved_pin is None:
            return None, None, saved_pin
        return saved_pin.pin_lat_lon, derive_pin_position(saved_pin.pin_lat_lon, hole.green.polygon, tee.center).value, saved_pin
    if source in {"front", "middle", "back"}:
        preset_points = green_reference_points(hole.green.polygon, tee.center)
        pin_lat_lon = preset_points[PinPosition(source)]
        return pin_lat_lon, source, saved_pin
    if source == "custom":
        try:
            lat = _parse_optional_float(st.session_state.custom_pin_lat, field_name="Custom pin latitude")
            lon = _parse_optional_float(st.session_state.custom_pin_lon, field_name="Custom pin longitude")
        except ValueError:
            return None, None, saved_pin
        if lat is None or lon is None:
            return None, None, saved_pin
        pin_lat_lon = LatLon(lat=lat, lon=lon)
        return pin_lat_lon, derive_pin_position(pin_lat_lon, hole.green.polygon, tee.center).value, saved_pin
    return None, None, saved_pin


def _save_active_pin(course: Course | None, hole: Hole | None, tee: TeeBox | None) -> None:
    pin_lat_lon, pin_position_value, _ = _resolve_active_pin(course, hole, tee)
    if course is None or hole is None:
        st.session_state.pin_error = "Select a course and hole first."
        st.session_state.pin_status = None
        return
    if pin_lat_lon is None:
        st.session_state.pin_error = "Choose a pin source or enter valid custom coordinates first."
        st.session_state.pin_status = None
        return

    source = "preset" if st.session_state.active_pin_source in {"front", "middle", "back"} else "manual"
    pin_manager.save_pin(
        course.id,
        hole.number,
        pin_lat_lon,
        pin_date=st.session_state.pin_date,
        source=source,
    )
    st.session_state.pin_error = None
    st.session_state.pin_status = (
        f"Saved {pin_position_value or 'custom'} pin for {course.name} hole {hole.number} on "
        f"{st.session_state.pin_date.isoformat()}."
    )


def _fetch_course_from_overpass() -> None:
    osm_ref = st.session_state.course_osm_ref.strip()
    if not osm_ref:
        st.session_state.course_error = "Enter an OSM ref like way/35679036 first."
        st.session_state.course_status = None
        return

    try:
        payload = fetch_course(osm_ref)
        parsed_course = parse_course_payload(payload, osm_ref=osm_ref)
        course_manager.save_course(parsed_course, overwrite=True)
    except Exception as exc:
        st.session_state.course_error = f"Could not fetch course from Overpass: {exc}"
        st.session_state.course_status = None
        return

    st.session_state.active_course_id = parsed_course.id
    st.session_state.selected_hole_number = parsed_course.holes[0].number
    st.session_state.selected_tee_label = parsed_course.holes[0].tees[0].label if parsed_course.holes[0].tees else ""
    st.session_state.course_error = None
    st.session_state.course_status = f"Saved {parsed_course.name} from {osm_ref}."


def _parse_optional_float(value: object, *, field_name: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc


def _get_session_location() -> LatLon | None:
    lat = _parse_optional_float(st.session_state.location_lat, field_name="Latitude")
    lon = _parse_optional_float(st.session_state.location_lon, field_name="Longitude")
    if lat is None and lon is None:
        _, _, tee = _selected_course_context()
        return tee.center if tee is not None else None
    if lat is None or lon is None:
        raise ValueError("Both latitude and longitude are required.")
    return LatLon(lat=lat, lon=lon)


def _get_target_location() -> LatLon | None:
    lat = _parse_optional_float(st.session_state.target_lat, field_name="Target latitude")
    lon = _parse_optional_float(st.session_state.target_lon, field_name="Target longitude")
    if lat is None and lon is None:
        course, hole, tee = _selected_course_context()
        pin_lat_lon, _, _ = _resolve_active_pin(course, hole, tee)
        if pin_lat_lon is not None:
            return pin_lat_lon
        return hole.green.center if hole is not None else None
    if lat is None or lon is None:
        raise ValueError("Both target latitude and target longitude are required.")
    return LatLon(lat=lat, lon=lon)


def _get_shot_azimuth() -> float | None:
    value = _parse_optional_float(st.session_state.shot_azimuth_deg, field_name="Shot azimuth")
    if value is None:
        return None
    if not 0.0 <= value < 360.0:
        raise ValueError("Shot azimuth must be between 0 and 359.9 degrees.")
    return round(value, 1)


def _elevation_label_from_delta(delta_ft: float) -> str:
    if abs(delta_ft) < 8.0:
        return Elevation.FLAT.value
    if delta_ft >= 20.0:
        return Elevation.STEEP_UPHILL.value
    if delta_ft > 0.0:
        return Elevation.UPHILL.value
    if delta_ft <= -20.0:
        return Elevation.STEEP_DOWNHILL.value
    return Elevation.DOWNHILL.value


def _derived_live_wind_direction(weather: WeatherObservation | None, fallback: str) -> str:
    if weather is None:
        return fallback
    try:
        shot_azimuth = _get_shot_azimuth()
    except ValueError:
        return fallback
    if shot_azimuth is None:
        return fallback

    relative = ((weather.wind_direction_deg - shot_azimuth + 180.0) % 360.0) - 180.0
    if abs(relative) <= 45.0:
        return "headwind"
    if abs(relative) >= 135.0:
        return "tailwind"
    return "crosswind_right" if relative > 0 else "crosswind_left"


def _get_live_weather_preview() -> WeatherObservation | None:
    payload = st.session_state.live_weather_observation
    if not payload:
        return None
    return WeatherObservation.model_validate(payload)


def _build_environment_overrides() -> dict[str, object]:
    overrides: dict[str, object] = {}
    course, hole, tee = _selected_course_context()
    active_pin_lat_lon, _, _ = _resolve_active_pin(course, hole, tee)
    try:
        location = _get_session_location()
    except ValueError as exc:
        st.error(str(exc))
        return overrides

    try:
        target_location = _get_target_location()
    except ValueError as exc:
        st.error(str(exc))
        return overrides

    try:
        shot_azimuth = _get_shot_azimuth()
    except ValueError as exc:
        st.error(str(exc))
        return overrides

    if location is not None:
        overrides["location"] = location.model_dump(mode="json")
    if target_location is not None:
        overrides["target_location"] = target_location.model_dump(mode="json")
    if shot_azimuth is not None:
        overrides["shot_azimuth_deg"] = shot_azimuth

    if course is not None and hole is not None:
        overrides["course_id"] = course.id
        overrides["hole_number"] = hole.number
        overrides["pin_date"] = st.session_state.pin_date.isoformat()
        overrides["pin_source"] = st.session_state.active_pin_source
        if tee is not None:
            overrides["tee_lat_lon"] = tee.center.model_dump(mode="json")
        if active_pin_lat_lon is not None:
            overrides["pin_lat_lon"] = active_pin_lat_lon.model_dump(mode="json")

    if not st.session_state.use_manual_weather:
        overrides["live_weather_requested"] = True
        overrides["live_elevation_requested"] = True
        live_weather = _get_live_weather_preview()
        if live_weather is not None:
            overrides["weather_observation"] = live_weather.model_dump(mode="json")

    return overrides


def _search_location() -> None:
    query = st.session_state.location_query.strip()
    if not query:
        st.session_state.location_error = "Enter a course or place name first."
        st.session_state.location_status = None
        return

    try:
        location = geocode(query)
    except Exception as exc:
        st.session_state.location_error = f"Could not geocode '{query}': {exc}"
        st.session_state.location_status = None
        return

    st.session_state.location_lat = f"{location.lat:.6f}"
    st.session_state.location_lon = f"{location.lon:.6f}"
    st.session_state.location_error = None
    st.session_state.location_status = f"Loaded coordinates for '{query}'."


def _fetch_live_conditions_preview() -> None:
    try:
        location = _get_session_location()
    except ValueError as exc:
        st.session_state.location_error = str(exc)
        st.session_state.location_status = None
        return

    if location is None:
        st.session_state.location_error = "Provide coordinates or search for a course first."
        st.session_state.location_status = None
        return

    try:
        weather = get_weather(location.lat, location.lon)
        altitude_ft = get_elevation(location.lat, location.lon)
        target_location = _get_target_location()
        st.session_state.live_weather_observation = weather.model_dump(mode="json")
        st.session_state.live_altitude_ft = altitude_ft
        st.session_state.live_elevation_value = None
        if target_location is not None:
            delta_ft = get_elevation_delta(location, target_location)
            st.session_state.live_elevation_value = _elevation_label_from_delta(delta_ft)
        st.session_state.location_error = None
        st.session_state.location_status = "Fetched live weather and elevation preview."
    except Exception as exc:
        st.session_state.location_error = f"Could not fetch live conditions: {exc}"
        st.session_state.location_status = None


def _render_hole_preview(hole: Hole | None, tee: TeeBox | None, pin_lat_lon: LatLon | None = None) -> None:
    if pdk is None or hole is None:
        return

    fairway_data = [
        {
            "polygon": [[point.lon, point.lat] for point in hole.fairway_polygon],
            "fill_color": [111, 178, 104, 140],
        }
    ]
    green_data = [
        {
            "polygon": [[point.lon, point.lat] for point in hole.green.polygon],
            "fill_color": [77, 201, 112, 190],
        }
    ]
    hazard_data = [
        {
            "polygon": [[point.lon, point.lat] for point in hazard.polygon],
            "fill_color": [56, 122, 186, 170] if hazard.kind == "water" else [217, 196, 132, 170],
            "label": hazard.kind,
        }
        for hazard in hole.hazards
    ]
    marker_data = [
        {
            "label": "Green",
            "coordinates": [hole.green.center.lon, hole.green.center.lat],
            "color": [18, 87, 40],
        }
    ]
    if tee is not None:
        marker_data.append(
            {
                "label": tee.label,
                "coordinates": [tee.center.lon, tee.center.lat],
                "color": [179, 54, 62],
            }
        )
    if pin_lat_lon is not None:
        marker_data.append(
            {
                "label": "Pin",
                "coordinates": [pin_lat_lon.lon, pin_lat_lon.lat],
                "color": [250, 221, 20],
            }
        )

    view_state = pdk.ViewState(
        latitude=hole.green.center.lat,
        longitude=hole.green.center.lon,
        zoom=16,
        pitch=0,
    )
    layers = [
        pdk.Layer("PolygonLayer", fairway_data, get_polygon="polygon", get_fill_color="fill_color", stroked=False),
        pdk.Layer("PolygonLayer", green_data, get_polygon="polygon", get_fill_color="fill_color", stroked=False),
    ]
    if hazard_data:
        layers.append(
            pdk.Layer("PolygonLayer", hazard_data, get_polygon="polygon", get_fill_color="fill_color", stroked=False)
        )
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            marker_data,
            get_position="coordinates",
            get_fill_color="color",
            get_radius=6,
            radius_units="pixels",
        )
    )

    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=layers,
            tooltip={"text": "{label}"},
        ),
        use_container_width=True,
    )


with st.sidebar:
    st.markdown("## Player Profile")
    st.caption("Use the sidebar to manage the player, course, pin, imports, and evaluation tools.")

    skill_labels = {
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "scratch": "Scratch",
    }
    profile_options, profile_labels = _profile_option_metadata()
    if st.session_state.active_profile_key not in profile_options:
        st.session_state.active_profile_key = f"default:{st.session_state.skill_level}"

    selected_profile_key = st.selectbox(
        "Active profile",
        options=profile_options,
        index=profile_options.index(st.session_state.active_profile_key),
        format_func=lambda key: profile_labels.get(key, key),
    )
    st.session_state.active_profile_key = selected_profile_key

    if selected_profile_key.startswith("default:"):
        st.session_state.skill_level = selected_profile_key.split(":", 1)[1]

    try:
        profile = _load_profile_for_key(selected_profile_key)
    except Exception as exc:
        st.error(f"Could not load profile: {exc}")
        st.stop()

    derived_tendencies = feedback_manager.summarize_tendencies(profile)

    if selected_profile_key.startswith("default:"):
        selected_skill = selected_profile_key.split(":", 1)[1]
        profile_status = skill_labels.get(selected_skill, selected_skill)
    elif selected_profile_key.startswith("benchmark:"):
        profile_status = "Benchmark profile"
    else:
        profile_status = "Imported profile"

    st.caption(f"**{profile.name}** ({profile_status})")

    with st.expander("Club Distances", expanded=False):
        render_profile_distances(profile)

    with st.expander("Player Tendencies", expanded=False):
        if derived_tendencies.common_miss:
            st.write(f"Common miss: `{derived_tendencies.common_miss}`")
        else:
            st.caption("No feedback history yet.")

        if derived_tendencies.confidence_by_club:
            top_confidence = sorted(
                derived_tendencies.confidence_by_club.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
            for club, confidence in top_confidence:
                st.write(f"{club}: confidence {confidence:.2f}")

    st.divider()
    st.markdown("#### Course & Hole")
    course_options, course_labels = _course_option_metadata()
    if st.session_state.active_course_id not in course_options:
        st.session_state.active_course_id = ""

    selected_course_id = st.selectbox(
        "Saved course",
        options=course_options,
        index=course_options.index(st.session_state.active_course_id),
        format_func=lambda course_id: course_labels.get(course_id, course_id or "None"),
    )
    st.session_state.active_course_id = selected_course_id

    st.text_input(
        "Fetch by OSM ref",
        key="course_osm_ref",
        help="Examples: way/35679036 or relation/6333321",
    )
    if st.button("Fetch Course", use_container_width=True):
        _fetch_course_from_overpass()
        st.rerun()

    selected_course, selected_hole, selected_tee = _selected_course_context()
    if selected_course is not None:
        hole_numbers = [hole.number for hole in selected_course.holes]
        st.selectbox("Hole", options=hole_numbers, key="selected_hole_number")
        selected_hole = _get_selected_hole(selected_course)

        tee_labels = [tee.label for tee in selected_hole.tees] if selected_hole and selected_hole.tees else [""]
        st.selectbox("Tee", options=tee_labels, key="selected_tee_label")
        selected_tee = _get_selected_tee(selected_hole)

        if selected_hole is not None:
            st.caption(
                f"{selected_course.name} • Hole {selected_hole.number} • Par {selected_hole.par}"
            )
        if selected_hole is not None and selected_tee is not None:
            st.caption(
                f"Derived center-green distance: {haversine_yards(selected_tee.center, selected_hole.green.center):.0f} yds "
                f"from tee '{selected_tee.label}'."
            )

    if st.session_state.course_status:
        st.success(st.session_state.course_status)
    if st.session_state.course_error:
        st.error(st.session_state.course_error)

    st.divider()
    st.markdown("#### Pin Setup")
    if selected_course is not None and selected_hole is not None and selected_tee is not None:
        saved_pin = _get_saved_pin(selected_course, selected_hole)
        pin_options, pin_labels = _pin_source_options(saved_pin)
        if st.session_state.active_pin_source not in pin_options:
            st.session_state.active_pin_source = "saved" if saved_pin is not None else "middle"

        st.date_input("Pin date", key="pin_date")
        st.selectbox(
            "Active pin",
            options=pin_options,
            key="active_pin_source",
            format_func=lambda source: pin_labels.get(source, source),
        )

        if saved_pin is not None:
            st.caption(
                f"Saved pin: {saved_pin.pin_lat_lon.lat:.6f}, {saved_pin.pin_lat_lon.lon:.6f} "
                f"for {st.session_state.pin_date.isoformat()}"
            )

        if st.session_state.active_pin_source == "custom":
            st.text_input("Custom pin latitude", key="custom_pin_lat", placeholder="32.896000")
            st.text_input("Custom pin longitude", key="custom_pin_lon", placeholder="-117.247000")

        active_pin_lat_lon, active_pin_position, _ = _resolve_active_pin(selected_course, selected_hole, selected_tee)
        if active_pin_lat_lon is not None:
            st.caption(
                f"Active pin: {active_pin_lat_lon.lat:.6f}, {active_pin_lat_lon.lon:.6f} "
                f"({active_pin_position or 'custom'})"
            )

        if st.button("Save Current Pin", use_container_width=True):
            _save_active_pin(selected_course, selected_hole, selected_tee)
            st.rerun()
    else:
        st.caption("Select a course, hole, and tee to manage daily pins.")

    if st.session_state.pin_status:
        st.success(st.session_state.pin_status)
    if st.session_state.pin_error:
        st.error(st.session_state.pin_error)

    st.divider()
    st.markdown("#### Upload My Shots")
    uploaded_file = st.file_uploader(
        "Import TrackMan, Foresight, or Golf Pad CSV",
        type=["csv"],
        key="shot_history_upload",
    )

    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        try:
            detected_format, imported_shots = import_shot_file(uploaded_bytes, source_name=uploaded_file.name)
            suggested_profile_name = build_profile_from_shots(imported_shots).name
            if st.session_state.uploaded_source_name != uploaded_file.name:
                st.session_state.uploaded_source_name = uploaded_file.name
                st.session_state.upload_profile_name = suggested_profile_name

            st.caption(f"Detected format: `{detected_format}` • Parsed shots: `{len(imported_shots)}`")
            st.text_input("Profile name", key="upload_profile_name")

            preview_profile = build_profile_from_shots(
                imported_shots,
                profile_name=st.session_state.upload_profile_name or suggested_profile_name,
            )
            st.caption(
                f"Preview profile: `{preview_profile.skill_level.value}` • "
                f"{len(preview_profile.club_distances)} clubs"
            )

            preview_rows = [
                {
                    "club": shot.club,
                    "carry_yds": shot.carry_yds,
                    "offline_ft": shot.offline_ft,
                    "captured_at": shot.captured_at.isoformat(),
                }
                for shot in imported_shots[:8]
            ]
            st.dataframe(preview_rows, use_container_width=True, hide_index=True)

            if st.button("Save As Profile", use_container_width=True, key="save_imported_profile"):
                profile_name = st.session_state.upload_profile_name.strip() or suggested_profile_name
                saved_profile, storage_path = save_imported_profile(
                    imported_shots,
                    profile_name=profile_name,
                )
                profile_file_name = f"imported_{slugify_player_id(saved_profile.name)}"
                pm.save_profile(saved_profile, overwrite=True, file_name=profile_file_name)
                st.session_state.active_profile_key = f"custom:{profile_file_name}"
                st.success(
                    f"Saved {saved_profile.name} with {len(imported_shots)} shots. "
                    f"History stored at {storage_path.name}."
                )
                st.rerun()
        except Exception as exc:
            st.error(f"Could not import uploaded file: {exc}")

    st.divider()
    st.markdown("#### Evaluation Admin")
    real_run_summary = summarize_real_runs(
        run_recorder.load_records(
            feedback_file=feedback_manager.feedback_file,
            profile_name=profile.name,
        )
    )
    st.caption(
        f"Logged runs: {real_run_summary['total_runs']} • "
        f"Linked feedback: {real_run_summary['feedback_linked_runs']} • "
        f"Promotable: {real_run_summary['promotable_runs']}"
    )
    if st.button("Write Real-Run Report", use_container_width=True, key="write_real_run_report"):
        report_path = run_recorder.runs_file.parent / "real_run_report.md"
        report_path.write_text(render_real_run_report(real_run_summary), encoding="utf-8")
        st.success(f"Wrote real-run report to {report_path}.")
    if st.button("Export Promotable Benchmarks", use_container_width=True, key="export_real_shot_benchmarks"):
        exported_path = run_recorder.export_promoted_benchmarks(
            feedback_file=feedback_manager.feedback_file,
            profile_name=profile.name,
        )
        st.success(f"Exported promotable benchmark cases to {exported_path}.")

    st.divider()
    debug_mode = st.toggle("Debug mode", value=False, help="Show raw agent outputs")

    st.divider()
    st.markdown("#### Quick Scenarios")
    st.caption("Auto-fill the structured form with a preset shot")

    for scenario in SAMPLE_SCENARIOS:
        if st.button(scenario.label, key=f"scenario_{scenario.label}", use_container_width=True):
            st.session_state.scenario = scenario.to_dict()
            st.rerun()

render_page_hero()

scenario_data = st.session_state.pop("scenario", None)


def _get_default(field: str, fallback):
    if scenario_data and field in scenario_data:
        return scenario_data[field]
    return fallback


def _run_pipeline(raw_input: dict[str, object]) -> PipelineResult:
    pipeline = Pipeline(profile, debug=debug_mode)
    result = pipeline.run(raw_input)
    _store_result(result, profile.name)
    return result


current_result: PipelineResult | None = None
live_weather_preview = _get_live_weather_preview()
selected_course, selected_hole, selected_tee = _selected_course_context()
active_pin_lat_lon, active_pin_position, _ = _resolve_active_pin(selected_course, selected_hole, selected_tee)

render_setup_snapshot(
    profile,
    profile_status,
    selected_course,
    selected_hole,
    selected_tee,
    live_weather_preview,
    manual_weather_only=st.session_state.use_manual_weather,
    pin_position=active_pin_position,
)
st.caption(
    "Use the sidebar for player, course, pin, and data setup. "
    "Use the main area to enter the shot and review the recommendation."
)

main_input_col, live_context_col = st.columns([1.55, 1.0], gap="large")

with main_input_col:
    st.markdown("## Plan the Shot")
    st.caption("Choose the input style that feels faster. Structured entry is precise; free text is quicker when the situation is messy.")

    structured_tab, text_tab = st.tabs(["Structured Shot", "Describe My Shot"])

    with structured_tab:
        st.markdown('<div class="step-caption">Step 1 · Build the shot with structured inputs</div>', unsafe_allow_html=True)
        if selected_course is not None and selected_hole is not None and selected_tee is not None:
            st.caption(
                f"Course context selected: Hole {selected_hole.number} on {selected_course.name}. "
                f"Entered distance stays in control; saved course and pin data only fill in missing context."
            )
            if active_pin_lat_lon is not None:
                st.caption(
                    "Saved/current pin data is active, so pin position can be derived automatically."
                )
        default_wind_speed = int(
            round(live_weather_preview.wind_speed_mph)
        ) if live_weather_preview is not None and not st.session_state.use_manual_weather else int(_get_default("wind_speed", 0))
        default_wind_direction = (
            _derived_live_wind_direction(live_weather_preview, _get_default("wind_direction", "headwind"))
            if not st.session_state.use_manual_weather
            else _get_default("wind_direction", "headwind")
        )
        default_temperature = (
            float(live_weather_preview.temperature_f)
            if live_weather_preview is not None and not st.session_state.use_manual_weather
            else float(_get_default("temperature", 72.0))
        )
        default_altitude_ft = (
            float(st.session_state.live_altitude_ft)
            if st.session_state.live_altitude_ft is not None and not st.session_state.use_manual_weather
            else float(_get_default("altitude_ft", 0.0))
        )
        default_elevation = (
            st.session_state.live_elevation_value
            if st.session_state.live_elevation_value is not None and not st.session_state.use_manual_weather
            else _get_default("elevation", "flat")
        )

        with st.form("structured_shot_form", clear_on_submit=False):
            distance = st.number_input(
                "Distance to target (yards)",
                min_value=30.0,
                max_value=350.0,
                value=float(_get_default("distance_to_target", 150.0)),
                step=1.0,
            )

            col_lie, col_strategy = st.columns(2)
            with col_lie:
                lie_type = st.radio(
                    "Lie",
                    options=["tee", "fairway", "rough", "deep_rough", "bunker"],
                    index=["tee", "fairway", "rough", "deep_rough", "bunker"].index(
                        _get_default("lie_type", "fairway")
                    ),
                )
            with col_strategy:
                strategy = st.radio(
                    "Strategy",
                    options=["safe", "neutral", "aggressive"],
                    index=["safe", "neutral", "aggressive"].index(_get_default("strategy", "neutral")),
                )

            col_wind, col_wind_dir = st.columns(2)
            with col_wind:
                wind_speed = st.select_slider(
                    "Wind speed (mph)",
                    options=list(range(0, 41)),
                    value=default_wind_speed,
                )
            with col_wind_dir:
                wind_direction = st.selectbox(
                    "Wind direction",
                    options=["headwind", "tailwind", "crosswind_left", "crosswind_right"],
                    index=["headwind", "tailwind", "crosswind_left", "crosswind_right"].index(
                        default_wind_direction
                    ),
                )

            elevation = st.selectbox(
                "Elevation",
                options=["flat", "uphill", "downhill", "steep_uphill", "steep_downhill"],
                index=["flat", "uphill", "downhill", "steep_uphill", "steep_downhill"].index(
                    default_elevation
                ),
            )

            with st.expander("Advanced Context", expanded=False):
                col_temp, col_alt = st.columns(2)
                with col_temp:
                    temperature = st.number_input(
                        "Temperature (°F)",
                        min_value=20.0,
                        max_value=120.0,
                        value=default_temperature,
                        step=1.0,
                    )
                with col_alt:
                    altitude_ft = st.number_input(
                        "Altitude (ft)",
                        min_value=0.0,
                        max_value=10000.0,
                        value=default_altitude_ft,
                        step=100.0,
                    )

                col_target_mode, col_pin_position = st.columns(2)
                with col_target_mode:
                    target_mode = st.selectbox(
                        "Target mode",
                        options=["pin", "center_green", "layup"],
                        index=["pin", "center_green", "layup"].index(_get_default("target_mode", "pin")),
                    )
                with col_pin_position:
                    pin_options = ["", "front", "middle", "back"]
                    default_pin = _get_default("pin_position", "") or ""
                    pin_position = st.selectbox(
                        "Pin position",
                        options=pin_options,
                        index=pin_options.index(default_pin),
                    )

                hazard_note = st.text_input(
                    "Hazard note",
                    value=_get_default("hazard_note", "") or "",
                    placeholder="Examples: water_short, bunker_long, trouble_left",
                )
                confidence_option = st.selectbox(
                    "Player confidence",
                    options=["Unknown", 1, 2, 3, 4, 5],
                    index=["Unknown", 1, 2, 3, 4, 5].index(_get_default("player_confidence", "Unknown") or "Unknown"),
                )

            structured_submitted = st.form_submit_button(
                "Get Recommendation",
                type="primary",
                use_container_width=True,
            )

        if structured_submitted:
            raw_input = {
                "distance_to_target": distance,
                "lie_type": lie_type,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "elevation": elevation,
                "strategy": strategy,
                "temperature": temperature,
                "altitude_ft": altitude_ft,
                "target_mode": target_mode,
                "pin_position": pin_position or None,
                "hazard_note": hazard_note or None,
                "player_confidence": None if confidence_option == "Unknown" else confidence_option,
            }
            raw_input.update(_build_environment_overrides())
            try:
                current_result = _run_pipeline(raw_input)
            except InputValidationError as exc:
                st.error(str(exc))

    with text_tab:
        st.markdown('<div class="step-caption">Step 1 · Describe the shot naturally</div>', unsafe_allow_html=True)
        if selected_course is not None and selected_hole is not None:
            st.caption(
                f"Course context selected: Hole {selected_hole.number} on {selected_course.name}. "
                f"If your description includes a distance, that distance is what the recommendation will use."
            )
        with st.form("describe_shot_form", clear_on_submit=False):
            shot_text = st.text_area(
                "Describe the shot in plain English",
                placeholder="145 out, into the wind maybe 10-15, ball sitting down a little, back pin, I just want middle of the green",
                height=140,
            )
            text_confidence_option = st.selectbox(
                "How confident do you feel over the shot?",
                options=["Unknown", 1, 2, 3, 4, 5],
                index=0,
            )
            text_submitted = st.form_submit_button(
                "Analyze and Recommend",
                type="primary",
                use_container_width=True,
            )

        if text_submitted:
            raw_input = {
                "shot_text": shot_text,
                "player_confidence": None if text_confidence_option == "Unknown" else text_confidence_option,
            }
            raw_input.update(_build_environment_overrides())
            try:
                current_result = _run_pipeline(raw_input)
            except InputValidationError as exc:
                st.error(str(exc))

with live_context_col:
    st.markdown("## Live Context")
    st.caption("These controls enrich the recommendation. They should add context, not override the shot distance you already know.")

    with st.expander("Location & Live Conditions", expanded=True):
        st.caption("Use course search or raw coordinates. Live weather can override manual wind and temperature.")

        st.text_input(
            "Course or location search",
            key="location_query",
            placeholder="Bethpage Black Golf Course",
        )

        col_search, col_fetch = st.columns(2)
        with col_search:
            if st.button("Search Course", use_container_width=True):
                _search_location()
        with col_fetch:
            if st.button("Fetch Live Conditions", use_container_width=True):
                _fetch_live_conditions_preview()
                live_weather_preview = _get_live_weather_preview()

        col_lat, col_lon = st.columns(2)
        with col_lat:
            st.text_input("Latitude", key="location_lat", placeholder="40.748655")
        with col_lon:
            st.text_input("Longitude", key="location_lon", placeholder="-73.445753")

        st.checkbox(
            "Use manual weather only",
            key="use_manual_weather",
            help="Leave checked to use the form's manual weather inputs only.",
        )

        st.caption("Optional: add target coordinates and shot azimuth to derive elevation and wind direction automatically.")
        col_tlat, col_tlon = st.columns(2)
        with col_tlat:
            st.text_input("Target latitude", key="target_lat", placeholder="Optional")
        with col_tlon:
            st.text_input("Target longitude", key="target_lon", placeholder="Optional")
        st.text_input(
            "Shot azimuth (degrees from north)",
            key="shot_azimuth_deg",
            placeholder="Optional, e.g. 90 for east",
        )

        if st.session_state.location_status:
            st.success(st.session_state.location_status)
        if st.session_state.location_error:
            st.error(st.session_state.location_error)

        if live_weather_preview is not None:
            st.caption(
                "Preview: "
                f"{live_weather_preview.wind_speed_mph:.1f} mph wind, "
                f"{live_weather_preview.temperature_f:.1f}°F, "
                f"pressure {live_weather_preview.pressure_mb:.1f} mb."
            )
            if st.session_state.live_altitude_ft is not None:
                st.caption(f"Altitude preview: {float(st.session_state.live_altitude_ft):.1f} ft")
            if st.session_state.live_elevation_value:
                st.caption(f"Elevation preview: {st.session_state.live_elevation_value.replace('_', ' ')}")

    if selected_course is not None and selected_hole is not None:
        with st.expander("Course Hole Preview", expanded=True):
            st.caption(
                f"{selected_course.name} • Hole {selected_hole.number} • Par {selected_hole.par} • "
                f"{len(selected_hole.hazards)} mapped hazards"
            )
            if active_pin_position:
                st.caption(f"Pin position: {active_pin_position}")
            _render_hole_preview(selected_hole, selected_tee, active_pin_lat_lon)
    else:
        st.info("No saved course selected yet. You can still use the caddie with manual distance and conditions.")

if current_result is None:
    stored_result = st.session_state.latest_result
    if stored_result is not None and st.session_state.latest_profile_name == profile.name:
        current_result = stored_result

if current_result is not None:
    st.divider()
    st.markdown("## Recommendation")
    st.caption("Review the chosen club, how the conditions changed the number, and whether the shot still looks right to you.")

    result_main_col, result_side_col = st.columns([1.5, 1.0], gap="large")

    if current_result.needs_clarification:
        with result_main_col:
            if current_result.shot_intent is not None and current_result.shot_intent.raw_text != "[structured_input]":
                render_shot_intent_card(current_result.shot_intent)
            render_clarification_card(current_result)
        with result_side_col:
            st.info("The caddie is holding off because one more detail could materially change the recommendation.")
        if debug_mode:
            render_debug_panel(current_result)
    elif current_result.decision is not None and current_result.explanation is not None:
        with result_main_col:
            if current_result.shot_intent is not None and current_result.shot_intent.raw_text != "[structured_input]":
                render_shot_intent_card(current_result.shot_intent)
            render_club_banner(current_result)
            render_adaptive_strategy(current_result)
            render_explanation(current_result)
            render_strategy_note(current_result)
            render_verification_note(current_result)

        with result_side_col:
            render_context_summary(current_result)
            st.markdown("##### Confidence")
            render_confidence_badge(current_result.decision.confidence.value)
            render_plays_like_metric(current_result)
            render_recommendation_fit(current_result, profile)
            render_adjustment_breakdown(current_result.decision.adjustments)
            render_backup_card(current_result, profile)

        st.divider()
        st.markdown("### Shot Feedback")
        st.caption("Log what actually happened so the app can learn which clubs are more reliable for this player.")
        if current_result.run_id:
            st.caption(f"Run ID: `{current_result.run_id}`")

        feedback_club_options = [current_result.decision.primary_club, current_result.decision.backup_club]
        for club_name in profile.club_distances:
            if club_name not in feedback_club_options:
                feedback_club_options.append(club_name)

        with st.form("feedback_form", clear_on_submit=False):
            feedback_col1, feedback_col2 = st.columns(2)
            with feedback_col1:
                club_used = st.selectbox("Club used", options=feedback_club_options, index=0)
                outcome = st.selectbox(
                    "Outcome",
                    options=[outcome.value for outcome in ShotOutcome],
                    format_func=lambda value: value.replace("_", " ").title(),
                )
            with feedback_col2:
                recommendation_rating = st.selectbox(
                    "Recommendation rating",
                    options=["", *[rating.value for rating in RecommendationRating]],
                    format_func=lambda value: (
                        "No rating yet" if value == "" else value.replace("_", " ").title()
                    ),
                )
                actual_outcome_note = st.text_input(
                    "Outcome note",
                    placeholder="Optional note about the miss or contact",
                )
            feedback_submitted = st.form_submit_button("Save Feedback", use_container_width=True)

        if feedback_submitted:
            feedback_manager.add_feedback(
                profile.name,
                ShotFeedback(
                    run_id=current_result.run_id,
                    club_used=club_used,
                    outcome=ShotOutcome(outcome),
                    recommendation_rating=RecommendationRating(recommendation_rating) if recommendation_rating else None,
                    actual_outcome_note=actual_outcome_note or None,
                ),
            )
            st.success("Shot feedback saved and linked to this recommendation run.")

        if debug_mode:
            render_debug_panel(current_result)

render_footer()
