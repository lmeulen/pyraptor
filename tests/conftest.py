"""conftest"""
import pytest
import datetime

import pandas as pd
import numpy as np

from pyraptor.dao.timetable import Timetable
from .utils import to_stops_and_trips, to_timetable


@pytest.fixture(scope="session")
def timetable() -> Timetable:
    """Default timetable"""

    df = get_data()
    stops, stop_times, trips = to_stops_and_trips(df)
    timetable_ = to_timetable(stops, stop_times, trips)

    return timetable_


@pytest.fixture(scope="session")
def timetable_with_fares() -> Timetable:
    """Timetable with fares"""
    stops, stop_times, trips = get_stop_times_with_fare()
    timetable_ = to_timetable(stops, stop_times, trips)
    return timetable_


@pytest.fixture(scope="session")
def timetable_with_transfers_and_fares() -> Timetable:
    """Timetable with fares"""
    stops, stop_times, trips = get_stop_times_with_transfers_and_fare()
    timetable_ = to_timetable(stops, stop_times, trips)
    return timetable_


def get_data():
    """Get default data for timetable"""

    def data_with_offset(trip_offset, time_offset):
        return [
            # First trip
            [
                trip_offset + 101,
                "A",
                time_offset + 100,
                time_offset + 100,
                "0",
                1,
                0,
            ],
            [
                trip_offset + 101,
                "C",
                time_offset + 600,
                time_offset + 600,
                "1",
                2,
                0,
            ],
            # Second trip
            [
                trip_offset + 202,
                "C",
                time_offset + 660,
                time_offset + 660,
                "2",
                1,
                0,
            ],
            [
                trip_offset + 202,
                "F",
                time_offset + 1500,
                time_offset + 1500,
                "0",
                2,
                0,
            ],
            # Third trip
            [
                trip_offset + 303,
                "C",
                time_offset + 900,
                time_offset + 900,
                "2",
                1,
                0,
            ],
            [
                trip_offset + 303,
                "X",
                time_offset + 1200,
                time_offset + 1200,
                "0",
                2,
                0,
            ],
            [
                trip_offset + 303,
                "F",
                time_offset + 1800,
                time_offset + 1800,
                "0",
                2,
                0,
            ],
            # Crossing route
            # [
            #     trip_offset + 404,
            #     "B",
            #     time_offset + 300,
            #     time_offset + 300,
            #     "0",
            #     1,
            #     0,
            # ],
            # [
            #     trip_offset + 404,
            #     "C",
            #     time_offset + 800,
            #     time_offset + 800,
            #     "3",
            #     2,
            #     0,
            # ],
            # [
            #     trip_offset + 404,
            #     "F",
            #     time_offset + 1900,
            #     time_offset + 1900,
            #     "0",
            #     3,
            #     0,
            # ],
        ]

    data = data_with_offset(trip_offset=0, time_offset=0) + data_with_offset(
        trip_offset=10, time_offset=3600
    )
    df = pd.DataFrame(
        data,
        columns=[
            "treinnummer",
            "code",
            "dts_arr",
            "dts_dep",
            "spoor",
            "trip_index",
            "fare",
        ],
    )
    return df


def get_stop_times_with_fare():
    """Create timetable with fare"""
    traffic_date = datetime.date(2021, 10, 21)

    stops = pd.DataFrame(
        {
            "stop_uic": [f"{i+8400000}" for i in range(1, 9)],
            "stop_id": [f"st{i}_sp1" for i in range(1, 9)],
        }
    )
    stops["parent_stop_id"] = stops["stop_id"].apply(lambda x: x[:-4])

    trip1 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 5,
            "treinnummer": [101] * 5,
            "toeslag": [0] * 5,
            "stop_id": [f"st{i}_sp1" for i in range(1, 6)],
            "vertrekmoment_utc": range(1, 6),
            "aankomstmoment_utc": range(1, 6),
            "vervoerstrajectindex": range(1, 6),
            "trip_id": [1] * 5,
        }
    )
    trip2 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 4,
            "treinnummer": [201] * 4,
            "toeslag": [0] * 4,
            "stop_id": [f"st{i}_sp1" for i in [8, 7, 4, 6]],
            "vertrekmoment_utc": np.arange(2.5, 4.5, 0.5),
            "aankomstmoment_utc": np.arange(2.5, 4.5, 0.5),
            "vervoerstrajectindex": range(1, 5),
            "trip_id": [2] * 4,
        }
    )
    trip3 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 2,
            "treinnummer": [301] * 2,
            "toeslag": [0] * 2,
            "stop_id": [f"st{i}_sp1" for i in [2, 7]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [3] * 2,
        }
    )
    trip4 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 2,
            "treinnummer": [401] * 2,
            "toeslag": [7] * 2,
            "stop_id": [f"st{i}_sp1" for i in [2, 4]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [4] * 2,
        }
    )

    stop_times = pd.concat([trip1, trip2, trip3, trip4], axis=0, ignore_index=True)
    stop_times["vertrekmoment_utc"] *= 600
    stop_times["aankomstmoment_utc"] *= 600
    trips = stop_times[
        ["verkeersdatum_ams", "treinnummer", "trip_id", "toeslag"]
    ].drop_duplicates()

    return stops, stop_times, trips



def get_stop_times_with_transfers_and_fare():
    """Create timetable with fare"""
    traffic_date = datetime.date(2021, 10, 21)

    stops = pd.DataFrame(
        {
            "stop_uic": [f"{i+8400000}" for i in range(1, 9)] + [f"{7+8400000}"],
            "stop_id": [f"st{i}_sp1" for i in range(1, 9)] + ["st7_sp2"],
        }
    )
    stops["parent_stop_id"] = stops["stop_id"].apply(lambda x: x[:-4])

    trip1 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 5,
            "treinnummer": [101] * 5,
            "toeslag": [0] * 5,
            "stop_id": [f"st{i}_sp1" for i in range(1, 6)],
            "vertrekmoment_utc": range(1, 6),
            "aankomstmoment_utc": range(1, 6),
            "vervoerstrajectindex": range(1, 6),
            "trip_id": [1] * 5,
        }
    )
    trip2 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 4,
            "treinnummer": [201] * 4,
            "toeslag": [0] * 4,
            "stop_id": [f"st{i}_sp1" for i in [8, 7, 4, 6]],
            "vertrekmoment_utc": np.arange(2.75, 4.75, 0.5),  # np.arange(2.5, 4.5, 0.5),
            "aankomstmoment_utc": np.arange(2.75, 4.75, 0.5),  # np.arange(2.5, 4.5, 0.5),
            "vervoerstrajectindex": range(1, 5),
            "trip_id": [2] * 4,
        }
    )
    trip3 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 2,
            "treinnummer": [301] * 2,
            "toeslag": [0] * 2,
            "stop_id": ["st2_sp1", "st7_sp2"],  # [f"st{i}_sp1" for i in [2, 7]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [3] * 2,
        }
    )
    trip4 = pd.DataFrame(
        {
            "verkeersdatum_ams": [traffic_date] * 2,
            "treinnummer": [401] * 2,
            "toeslag": [7] * 2,
            "stop_id": [f"st{i}_sp1" for i in [2, 4]],
            "vertrekmoment_utc": [2, 3],
            "aankomstmoment_utc": [2, 3],
            "vervoerstrajectindex": range(1, 3),
            "trip_id": [4] * 2,
        }
    )

    stop_times = pd.concat([trip1, trip2, trip3, trip4], axis=0, ignore_index=True)
    stop_times["vertrekmoment_utc"] *= 600
    stop_times["aankomstmoment_utc"] *= 600
    trips = stop_times[
        ["verkeersdatum_ams", "treinnummer", "trip_id", "toeslag"]
    ].drop_duplicates()

    return stops, stop_times, trips
