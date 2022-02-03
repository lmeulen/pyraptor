"""Test Query McRaptor"""
from pyraptor import query_mcraptor
from pyraptor.dao.timetable import Timetable
from pyraptor.model.mcraptor import (
    reconstruct_journeys,
    add_journey_details,
    print_journeys,
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


def test_is_pareto_efficient():
    # test for pareto set
    # labels = is_pareto_efficient(
    #             [
    #                 Label(10, 5, 0, stop), 
    #                 Label(10, 10, 0, stop),
    #                 Label(5, 11, 0, stop),
    #                 Label(6, 6, 0, stop),
    #                 Label(11, 12, 0, stop),
    #                 Label(7, 5, 0, stop)
    #             ]
    #         )
    # expected = [
    #     Label(5, 11, 0, stop),
    #     Label(6, 6, 0, stop),
    #     Label(7, 5, 0, stop)
    # ]

    return True
