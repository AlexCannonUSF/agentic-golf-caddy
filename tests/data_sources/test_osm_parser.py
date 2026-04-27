from models import Course
from utils.geometry import haversine_yards


def test_parse_course_payload_builds_18_hole_course(torrey_course_payload) -> None:
    from utils.data_sources.osm_parser import parse_course_payload

    course = parse_course_payload(
        torrey_course_payload,
        course_id="torrey_pines_south",
        osm_ref="way/35679036",
    )

    assert isinstance(course, Course)
    assert course.name == "Torrey Pines South Course"
    assert len(course.holes) == 18
    assert sum(len(hole.hazards) for hole in course.holes) / len(course.holes) >= 1.0


def test_parsed_holes_have_reasonable_geometry_and_tees(torrey_course: Course) -> None:
    hole_1 = torrey_course.holes[0]
    hole_3 = next(hole for hole in torrey_course.holes if hole.number == 3)

    assert hole_1.par == 4
    assert len(hole_1.tees) >= 1
    assert len(hole_1.hazards) >= 1
    assert haversine_yards(hole_1.tees[0].center, hole_1.green.center) >= 150.0

    assert hole_3.par == 3
    assert len(hole_3.fairway_polygon) >= 3
    assert len(hole_3.green.polygon) >= 3
