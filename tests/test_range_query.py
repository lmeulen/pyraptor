"""Test Range Query"""
from pyraptor import range_query
from pyraptor.dao.timetable import Timetable


def test_has_main():
    """Has main"""
    assert range_query.main


def test_perform_range_raptor(default_timetable: Timetable):
    """Test perform range raptor"""
    origin_station = "A"
    destination_station = "F"
    dep_secs_min = 60
    dep_secs_max = 4000
    rounds = 4

    journeys_to_destination = range_query.run_range_raptor(
        default_timetable,
        origin_station,
        dep_secs_min,
        dep_secs_max,
        rounds,
    )
    range_query.print_journeys(journeys_to_destination, destination_station)

    assert (
        len(journeys_to_destination.keys()) == 3
    ), "should have 3 destinations (4 stations minus 1 origin station)"
    assert (
        len(journeys_to_destination[destination_station]) == 2
    ), "should have 2 travel options"

    for journey in journeys_to_destination[destination_station][::-1]:
        assert len(journey) == 3, "should use 3 trips from A to E"
