from pyraptor import query

from pyraptor.dao.timetable import Timetable
from pyraptor.model.raptor import reconstruct_journey, add_journey_details
from pyraptor.query import perform_raptor, print_journey


def test_has_main():
    assert query.main


def test_perform_raptor(timetable: Timetable):
    origin_station = "HT"
    destination_station = "ZW"
    dep_secs = 60
    rounds = 4

    bag_k, final_dest, _ = perform_raptor(
        timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    assert final_dest != 0, "destination should be reachable"

    journey = reconstruct_journey(final_dest, bag=bag_k[rounds])
    detailed_journey = add_journey_details(timetable, journey)
    print_journey(timetable, detailed_journey, dep_secs)

    assert len(journey) == 4, "should have 4 trips"
