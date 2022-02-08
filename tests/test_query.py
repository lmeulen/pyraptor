"""Test Query"""
from pyraptor import query
from pyraptor.dao.timetable import Timetable


def test_has_main():
    """Has main"""
    assert query.main


def test_query_raptor(default_timetable: Timetable):
    """Test query raptor"""
    origin_station = "A"
    destination_station = "F"
    dep_secs = 0
    rounds = 4

    journey = query.run_raptor(
        default_timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    assert journey is not None, "destination should be reachable"

    query.print_journey(journey, dep_secs)

    assert len(journey) == 3, "should have 2 trips in journey"
