"""Test Query"""
from pyraptor import query
from pyraptor.dao.timetable import Timetable
from pyraptor.model.raptor import reconstruct_journey, add_journey_details


def test_has_main():
    assert query.main


def test_run_raptor(timetable: Timetable):
    origin_station = "HT"
    destination_station = "ZW"
    dep_secs = 60
    rounds = 3

    bag_k, final_dest, _ = query.run_raptor(
        timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    assert final_dest != 0, "destination should be reachable"

    journey = reconstruct_journey(final_dest, bag=bag_k[rounds])
    detailed_journey = add_journey_details(timetable, journey)
    query.print_journey(timetable, detailed_journey, dep_secs)

    assert len(journey) == 2, "should have 2 trips in journey"
