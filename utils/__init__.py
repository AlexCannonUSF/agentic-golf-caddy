"""Utility modules used by agents and UI."""

from utils.config import cache_dir, data_dir, http_timeout_seconds, nominatim_user_agent, project_root
from utils.course_manager import CourseManager, CourseNotFoundError
from utils.data_sources import (
    DiskCache,
    fetch_course,
    geocode,
    get_elevation,
    get_elevation_delta,
    get_weather,
    parse_course_payload,
)
from utils.evaluation import RunRecorder
from utils.feedback_manager import FeedbackManager
from utils.importers import (
    build_profile_from_shots,
    build_tendencies,
    detect_import_format,
    import_foresight_csv,
    import_golfpad_csv,
    import_shot_file,
    import_trackman_csv,
    load_shots,
    save_imported_profile,
    save_shots,
    slugify_player_id,
)
from utils.pin_manager import PinManager, PinSheetNotFoundError
from utils.profile_manager import (
    ProfileAlreadyExistsError,
    ProfileManager,
    ProfileNotFoundError,
)
from utils.validators import (
    InputValidationError,
    ValidationResult,
    normalize_elevation,
    normalize_lie_type,
    normalize_pin_position,
    normalize_strategy,
    normalize_target_mode,
    normalize_wind_direction,
    validate_shot_context_or_raise,
    validate_shot_input,
)
from utils.logger import PipelineLogger, setup_logging
from utils.wizard import (
    QUICK_WIZARD_ANCHOR_CLUBS,
    build_profile_from_quick_calibration,
    interpolate_club_distances,
)

__all__ = [
    "CourseManager",
    "CourseNotFoundError",
    "FeedbackManager",
    "DiskCache",
    "InputValidationError",
    "PinManager",
    "PipelineLogger",
    "PinSheetNotFoundError",
    "ProfileAlreadyExistsError",
    "ProfileManager",
    "ProfileNotFoundError",
    "QUICK_WIZARD_ANCHOR_CLUBS",
    "RunRecorder",
    "ValidationResult",
    "build_profile_from_shots",
    "build_profile_from_quick_calibration",
    "build_tendencies",
    "cache_dir",
    "data_dir",
    "detect_import_format",
    "fetch_course",
    "geocode",
    "get_elevation",
    "get_elevation_delta",
    "get_weather",
    "http_timeout_seconds",
    "import_foresight_csv",
    "import_golfpad_csv",
    "import_shot_file",
    "import_trackman_csv",
    "interpolate_club_distances",
    "load_shots",
    "nominatim_user_agent",
    "normalize_elevation",
    "normalize_lie_type",
    "normalize_pin_position",
    "normalize_strategy",
    "normalize_target_mode",
    "normalize_wind_direction",
    "parse_course_payload",
    "project_root",
    "save_imported_profile",
    "save_shots",
    "setup_logging",
    "slugify_player_id",
    "validate_shot_context_or_raise",
    "validate_shot_input",
]
