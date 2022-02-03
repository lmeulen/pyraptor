"""Test Range Query"""
from pyraptor import range_query
from pyraptor.dao.timetable import Timetable


def test_has_main():
    assert range_query.main


def test_perform_recursive_raptor(timetable: Timetable):
    origin_station = "A"
    destination_station = "E"
    dep_secs_min = 60
    dep_secs_max = 4000
    rounds = 4

    journeys_to_destination = range_query.run_recursive_raptor(
        timetable,
        origin_station,
        dep_secs_min,
        dep_secs_max,
        rounds,
    )
    range_query.print_journeys(journeys_to_destination, destination_station)

    assert len(journeys_to_destination.keys()) == 5, "should have 4 destinations"
    assert (
        len(journeys_to_destination[destination_station]) == 2
    ), "should have 2 travel options"

    for journey in journeys_to_destination[destination_station][::-1]:
        assert len(journey) == 2, "should use 2 trips from A to E"
