"""Environmental (temperature + altitude) adjustment calculators."""


def calculate_temperature_adjustment(temperature_f: float) -> float:
    """
    Return distance adjustment in yards from temperature.

    - Below 60F: +0.3 yards per degree below 60
    - Above 90F: -0.15 yards per degree above 90
    - Between 60F and 90F inclusive: 0
    """

    temperature = float(temperature_f)
    if temperature < 60.0:
        return round((60.0 - temperature) * 0.3, 1)
    if temperature > 90.0:
        return round((temperature - 90.0) * -0.15, 1)
    return 0.0


def calculate_altitude_adjustment(altitude_ft: float) -> float:
    """
    Return distance adjustment in yards from altitude.

    Ball flies farther at altitude, so this is a negative adjustment.
    Rule: -1 yard per 500 ft above sea level.
    """

    altitude = max(0.0, float(altitude_ft))
    return round(-(altitude / 500.0), 1)
