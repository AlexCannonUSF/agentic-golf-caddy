"""Shared enum types used across the project."""

from enum import StrEnum


class LieType(StrEnum):
    """Where the ball is sitting before the shot."""

    TEE = "tee"
    FAIRWAY = "fairway"
    ROUGH = "rough"
    DEEP_ROUGH = "deep_rough"
    BUNKER = "bunker"


class WindDirection(StrEnum):
    """Wind direction relative to the player's target line."""

    HEADWIND = "headwind"
    TAILWIND = "tailwind"
    CROSSWIND_LEFT = "crosswind_left"
    CROSSWIND_RIGHT = "crosswind_right"


class Elevation(StrEnum):
    """Simple elevation buckets used by the plays-like distance engine."""

    FLAT = "flat"
    UPHILL = "uphill"
    DOWNHILL = "downhill"
    STEEP_UPHILL = "steep_uphill"
    STEEP_DOWNHILL = "steep_downhill"


class Strategy(StrEnum):
    """Player's risk preference for the recommendation."""

    SAFE = "safe"
    NEUTRAL = "neutral"
    AGGRESSIVE = "aggressive"


class SkillLevel(StrEnum):
    """Built-in player profile tiers."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    SCRATCH = "scratch"


class PreferredShot(StrEnum):
    """Typical shot shape for a player profile."""

    DRAW = "draw"
    FADE = "fade"
    STRAIGHT = "straight"


class ConfidenceLevel(StrEnum):
    """Confidence label attached to the final club recommendation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TargetMode(StrEnum):
    """Whether the player is aiming at the pin, green center, or layup area."""

    PIN = "pin"
    CENTER_GREEN = "center_green"
    LAYUP = "layup"


class PinPosition(StrEnum):
    """Fallback pin location when exact pin coordinates are unavailable."""

    FRONT = "front"
    MIDDLE = "middle"
    BACK = "back"


class ShotOutcome(StrEnum):
    """Post-shot outcome categories collected from user feedback."""

    GOOD_CONTACT = "good_contact"
    ON_TARGET = "on_target"
    SHORT = "short"
    LONG = "long"
    LEFT = "left"
    RIGHT = "right"
    THIN = "thin"
    FAT = "fat"


class RecommendationRating(StrEnum):
    """Whether the user thought the caddie recommendation was useful."""

    GOOD_CALL = "good_call"
    BAD_CALL = "bad_call"
