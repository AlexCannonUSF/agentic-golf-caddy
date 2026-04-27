from datetime import date

from models import LatLon
from utils.pin_manager import PinManager


def test_pin_manager_saves_and_loads_daily_hole_pin(tmp_path) -> None:
    manager = PinManager(tmp_path / "pins")
    saved_path = manager.save_pin(
        "torrey_pines_south",
        3,
        LatLon(lat=32.896, lon=-117.247),
        pin_date=date(2026, 4, 15),
        source="preset",
    )
    loaded_pin = manager.get_pin("torrey_pines_south", 3, date(2026, 4, 15))

    assert saved_path.exists()
    assert loaded_pin is not None
    assert loaded_pin.hole_number == 3
    assert loaded_pin.pin_lat_lon.lat == 32.896
    assert loaded_pin.source == "preset"
