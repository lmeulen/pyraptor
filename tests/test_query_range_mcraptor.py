"""Test Range Query or McRaptor"""
from pyraptor import query_range_mcraptor
from pyraptor.model.structures import Timetable


def test_has_main():
    """Has main"""
    assert query_range_mcraptor.main


def test_query_range_mcraptor(default_timetable: Timetable):
    """Test perform range query on McRaptor"""
    origin_station = "A"
    destination_station = "F"
    dep_secs_min = 60
    dep_secs_max = 4000
    rounds = 4

    journeys_to_destinations = query_range_mcraptor.run_range_mcraptor(
        default_timetable,
        origin_station,
        dep_secs_min,
        dep_secs_max,
        rounds,
    )
    for jrny in journeys_to_destinations[destination_station]:
        jrny.print()

    assert (
        len(journeys_to_destinations.keys()) == 3
    ), "should have 3 destinations (4 stations minus 1 origin station)"
    assert (
        len(journeys_to_destinations[destination_station]) == 2
    ), "should have 2 travel options"

    for journey in journeys_to_destinations[destination_station][::-1]:
        assert len(journey) == 2, "should use 2 trips from A to F"
