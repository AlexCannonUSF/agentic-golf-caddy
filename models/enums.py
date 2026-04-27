"""Shared enum types used across the project."""

from enum import StrEnum


class LieType(StrEnum):
    TEE = "tee"
    FAIRWAY = "fairway"
    ROUGH = "rough"
    DEEP_ROUGH = "deep_rough"
    BUNKER = "bunker"


class WindDirection(StrEnum):
    HEADWIND = "headwind"
    TAILWIND = "tailwind"
    CROSSWIND_LEFT = "crosswind_left"
    CROSSWIND_RIGHT = "crosswind_right"


class Elevation(StrEnum):
    FLAT = "flat"
    UPHILL = "uphill"
    DOWNHILL = "downhill"
    STEEP_UPHILL = "steep_uphill"
    STEEP_DOWNHILL = "steep_downhill"


class Strategy(StrEnum):
    SAFE = "safe"
    NEUTRAL = "neutral"
    AGGRESSIVE = "aggressive"


class SkillLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    SCRATCH = "scratch"


class PreferredShot(StrEnum):
    DRAW = "draw"
    FADE = "fade"
    STRAIGHT = "straight"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TargetMode(StrEnum):
    PIN = "pin"
    CENTER_GREEN = "center_green"
    LAYUP = "layup"


class PinPosition(StrEnum):
    FRONT = "front"
    MIDDLE = "middle"
    BACK = "back"


class ShotOutcome(StrEnum):
    GOOD_CONTACT = "good_contact"
    ON_TARGET = "on_target"
    SHORT = "short"
    LONG = "long"
    LEFT = "left"
    RIGHT = "right"
    THIN = "thin"
    FAT = "fat"


class RecommendationRating(StrEnum):
    GOOD_CALL = "good_call"
    BAD_CALL = "bad_call"
