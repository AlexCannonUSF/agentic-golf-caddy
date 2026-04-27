from utils.course_manager import CourseManager


def test_course_manager_saves_loads_and_indexes_course(tmp_path, torrey_course) -> None:
    manager = CourseManager(tmp_path / "courses")
    saved_path = manager.save_course(torrey_course)
    loaded_course = manager.load_course("torrey_pines_south")
    records = manager.list_course_records()

    assert saved_path.exists()
    assert loaded_course.name == torrey_course.name
    assert len(records) == 1
    assert records[0]["id"] == "torrey_pines_south"
    assert records[0]["hole_count"] == 18
