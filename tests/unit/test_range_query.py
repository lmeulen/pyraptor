from pyraptor import range_query

from pyraptor.dao.timetable import Timetable
from pyraptor.range_query import (
    perform_recursive_raptor,
    add_journey_details,
    print_journeys,
)


def test_has_main():
    assert range_query.main


def test_perform_recursive_raptor(timetable: Timetable):
    origin_station = "HT"
    destination_station = "ZW"
    dep_secs_min = 60
    dep_secs_max = 60 * 60
    rounds = 4

    journeys_to_destination = perform_recursive_raptor(
        timetable,
        origin_station,
        dep_secs_min,
        dep_secs_max,
        rounds,
    )
    print_journeys(
        timetable, journeys_to_destination, destination_station=destination_station
    )

    assert len(journeys_to_destination.keys()) == 4, "should have 4 destinations"
    assert (
        len(journeys_to_destination[destination_station]) == 2
    ), "should have 2 travel options"

    for journey in journeys_to_destination[destination_station][::-1]:
        assert len(journey) == 4, "should use 4 trips from HT to ZW"
