"""conftest"""
import pytest
import pandas as pd

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

    df = get_data_with_fare()
    stops, stop_times, trips = to_stops_and_trips(df)
    timetable_ = to_timetable(stops, stop_times, trips)

    return timetable_


def get_data():
    """Get default data for timetable"""

    def data_with_offset(trip_offset, time_offset):
        return [
            [
                trip_offset + 101,
                "A",
                time_offset + 100,
                time_offset + 100,
                "14",
                1,
                0,
            ],
            [
                trip_offset + 101,
                "B",
                time_offset + 300,
                time_offset + 320,
                "6",
                2,
                0,
            ],
            [
                trip_offset + 101,
                "C",
                time_offset + 500,
                time_offset + 520,
                "1",
                3,
                0,
            ],
            [
                trip_offset + 202,
                "C",
                time_offset + 1000,
                time_offset + 1020,
                "2",
                1,
                0,
            ],
            [
                trip_offset + 202,
                "D",
                time_offset + 1200,
                time_offset + 1200,
                "4",
                2,
                0,
            ],
            [
                trip_offset + 202,
                "E",
                time_offset + 1400,
                time_offset + 1460,
                "14",
                3,
                0,
            ],
            [
                trip_offset + 202,
                "F",
                time_offset + 1800,
                time_offset + 1860,
                "7",
                4,
                0,
            ],
        ]

    data = data_with_offset(trip_offset=0, time_offset=0) + data_with_offset(
        trip_offset=10, time_offset=3400
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


def get_data_with_fare():
    data = [
        [
            964,
            "ASD",
            100,
            100,
            "14",
            1,
            0,
        ],
        [
            964,
            "SHL",
            300,
            320,
            "6",
            2,
            5,
        ],
        [
            964,
            "RTD",
            500,
            520,
            "4",
            3,
            0,
        ],
        [
            964,
            "BD",
            700,
            700,
            "4",
            4,
            0,
        ],
        [
            1964,
            "ASD",
            105,
            105,
            "14A",
            1,
            0,
        ],
        [
            1964,
            "SHL",
            330,
            350,
            "7",
            2,
            0,
        ],
        [
            1964,
            "BD",
            800,
            800,
            "4",
            3,
            0,
        ],
    ]
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
