"""Test Query McRaptor"""
from pyraptor import query_mcraptor
from pyraptor.model.mcraptor import print_journeys, pareto_set_labels
from pyraptor.model.datatypes import Stop, Label


def test_run_mcraptor(timetable_with_transfers_and_fares):
    """Test run mcraptor"""

    # Run McRaptor for the query starting at s2 and going to s4
    # This should yield 2 non-discriminating options for the timetable_with_fares
    # 1) s2-s7 with 201 + s7-s4 with 301, arrival time = 3.5, n_transfers = 1, fare = 0
    # 2) s2-s4 with 401, arrival time = 3, n_tranfers = 0, fare = 1

    # Note that the option with less transfers and longer duration is not considered currently
    # 3) s2-s4 with 101, arrival time = 4, n_transfers = 0, fare = 0

    origin_station = "8400002"
    destination_station = "8400004"
    departure_time = 2
    rounds = 2

    # Find route between two stations
    journeys = query_mcraptor.run_mcraptor(
        timetable_with_transfers_and_fares,
        origin_station,
        destination_station,
        departure_time,
        rounds,
    )
    # pprint(bag_round_stop)
    print_journeys(journeys, departure_time)

    assert len(journeys) == 2, "should have 2 journeys"


def test_pareto_set_labels():
    """test creating pareto set"""

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
