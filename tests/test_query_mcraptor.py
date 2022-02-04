"""Test Query McRaptor"""
from pyraptor import query_mcraptor
from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop
from pyraptor.model.mcraptor import (
    reconstruct_journeys,
    add_journey_details,
    print_journeys,
    pareto_set_labels,
    Label,
)


def test_run_raptor(timetable_with_fares: Timetable):
    origin_station = "ASD"
    destination_station = "BD"
    dep_secs = 0
    rounds = 1

    bag_round_stop, dest_stops = query_mcraptor.run_mcraptor(
        timetable_with_fares,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    assert len(dest_stops) != 0, "destination should be reachable"

    best_bag = bag_round_stop[rounds]
    journeys = reconstruct_journeys(dest_stops, best_bag)
    detailed_journeys = add_journey_details(timetable_with_fares, journeys)
    print_journeys(detailed_journeys, dep_secs)

    # assert len(journeys) == 2, "should have 2 journeys"


def test_pareto_set_labels():
    """
    test for creating pareto set
    """

    stop = Stop(1, 1, "UT", "13")

    l1 = Label(1, 6, 0, stop)
    l2 = Label(3, 4, 0, stop)
    l3 = Label(5, 1, 0, stop)
    l4 = Label(3, 5, 0, stop)
    l5 = Label(5, 3, 0, stop)
    l6 = Label(6, 1, 0, stop)
    labels = pareto_set_labels(
        [
            l1,
            l2,
            l3,
            l4,
            l5,
            l6,
        ]
    )
    expected = [l1, l2, l3]

    assert labels == expected