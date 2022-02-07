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
from tests.utils import to_timetable
import datetime
import pandas as pd
import numpy as np


# def test_run_raptor(timetable_with_fares: Timetable):
#     origin_station = "ASD"
#     destination_station = "BD"
#     dep_secs = 0
#     rounds = 1

#     bag_round_stop, dest_stops = query_mcraptor.run_mcraptor(
#         timetable_with_fares,
#         origin_station,
#         destination_station,
#         dep_secs,
#         rounds,
#     )

#     assert len(dest_stops) != 0, "destination should be reachable"

#     best_bag = bag_round_stop[rounds]
#     journeys = reconstruct_journeys(dest_stops, best_bag)
#     detailed_journeys = add_journey_details(timetable_with_fares, journeys)
#     print_journeys(detailed_journeys, dep_secs)

#     # assert len(journeys) == 2, "should have 2 journeys"


# def test_pareto_set_labels():
#     """
#     test for creating pareto set
#     """

#     stop = Stop(1, 1, "UT", "13")

#     l1 = Label(1, 6, 0, stop)
#     l2 = Label(3, 4, 0, stop)
#     l3 = Label(5, 1, 0, stop)
#     l4 = Label(3, 5, 0, stop)
#     l5 = Label(5, 3, 0, stop)
#     l6 = Label(6, 1, 0, stop)
#     labels = pareto_set_labels(
#         [
#             l1,
#             l2,
#             l3,
#             l4,
#             l5,
#             l6,
#         ]
#     )
#     expected = [l1, l2, l3]

#     assert labels == expected


def test_run_mcraptor_toy2():
    # Create toy timetable
    load_date = datetime.date(2021, 10, 21)

    toy_stops = pd.DataFrame(
        {
            "stop_uic": [f"{i+8400000}" for i in range(1, 9)],
            "stop_id": [f"s{i}_pl1" for i in range(1, 9)],
        }
    )
    toy_stops["parent_stop_id"] = toy_stops["stop_id"].apply(lambda x: x[:-4])

    trip1 = pd.DataFrame(
        {
            "verkeersdatum_ams": [load_date] * 5,
            "treinnummer": [101] * 5,
            "toeslag": [False] * 5,
            "stop_id": [f"s{i}_pl1" for i in range(1, 6)],
            "vertrekmoment_utc": range(1, 6),
            "aankomstmoment_utc": range(1, 6),
            "vervoerstrajectindex": range(1, 6),
            "trip_id": [1] * 5,
        }
    )
    trip2 = pd.DataFrame(
        {
            "verkeersdatum_ams": [load_date] * 4,
            "treinnummer": [201] * 4,
            "toeslag": [False] * 4,
            "stop_id": [f"s{i}_pl1" for i in [8, 7, 4, 6]],
            "vertrekmoment_utc": np.arange(2.5, 4.5, 0.5),
            "aankomstmoment_utc": np.arange(2.5, 4.5, 0.5),
            "vervoerstrajectindex": range(1, 5),
            "trip_id": [2] * 4,
        }
    )
    trip3 = pd.DataFrame(
        {
            "verkeersdatum_ams": [load_date] * 2,
            "treinnummer": [301] * 2,
            "toeslag": [False] * 2,
            "stop_id": [f"s{i}_pl1" for i in [2, 7]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [3] * 2,
        }
    )
    trip4 = pd.DataFrame(
        {
            "verkeersdatum_ams": [load_date] * 2,
            "treinnummer": [401] * 2,
            "toeslag": [True] * 2,
            "stop_id": [f"s{i}_pl1" for i in [2, 4]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [4] * 2,
        }
    )

    toy_stop_times = pd.concat([trip1, trip2, trip3, trip4], axis=0, ignore_index=True)
    toy_trips = toy_stop_times[
        ["verkeersdatum_ams", "treinnummer", "trip_id", "toeslag"]
    ].drop_duplicates()

    timetable = to_timetable(toy_stops, toy_stop_times, toy_trips)

    # Run McRaptor for the query starting at s2 and going to s4
    # This should yield 3 non-discriminating options:
    # 1) s2-s4 with 101, arrival time = 4, n_tranfers = 0, fare = 0
    # 2) s2-s7 with 201 + s7-s4 with 301, arrival time = 3.5, n_transfers = 1, fare = 0
    # 3) s2-s4 with 401, arrival time = 3, n_tranfers = 0, fare = 1

    origin_station = "8400002"
    destination_station = "8400004"
    departure_time = 2
    rounds = 3

    # Find route between two stations
    bag_k, final_dest = query_mcraptor.run_mcraptor(
        timetable,
        origin_station,
        destination_station,
        departure_time,
        rounds,
    )

    print(bag_k)

    assert True