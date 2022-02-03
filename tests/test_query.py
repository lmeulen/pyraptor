"""Test Query"""
from pyraptor import query
from pyraptor.dao.timetable import Timetable
from pyraptor.model.raptor import reconstruct_journey


def test_has_main():
    assert query.main


def test_run_raptor(timetable: Timetable):
    origin_station = "A"
    destination_station = "E"
    dep_secs = 180
    rounds = 2

    best_labels, final_dest = query.run_raptor(
        timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    assert final_dest != 0, "destination should be reachable"

    journey = reconstruct_journey(final_dest, best_labels)
    query.print_journey(journey, dep_secs)

    assert len(journey) == 2, "should have 2 trips in journey"
