"""conftest"""
import pytest

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import (
    Stop,
    Stops,
    Trip,
    Trips,
    TripStopTime,
    TripStopTimes,
    Station,
    Stations,
)


@pytest.fixture(scope="session")
def timetable() -> Timetable:
    """Load timetable"""

    station_names = ["HT", "UT", "TB", "RTD", "ZW"]

    timetable = Timetable()

    # Stations and stops, i.e. platforms
    stations = Stations()
    stops = Stops()

    for name in station_names:
        station = Station(name, name)
        station = stations.add(station)

        for i in range(1, 4):
            stop_id = f"{name}{i}"
            stop = Stop(stop_id, stop_id, station, name)

            station.add_stop(stop)
            stops.add(stop)

    # Trips and Trip Stop Times
    trips = Trips()
    trip_stop_times = TripStopTimes()

    # Iterate over trips
    trip_number = 1

    for offset in range(0, 2):
        for tripidx in range(4):
            random_stations = station_names[tripidx : tripidx + 2]

            trip = Trip()
            trip.hint = trip_number

            for stopidx in range(len(random_stations)):
                # Trip Stop Times
                dts_arr = (1000 * tripidx) + stopidx * 80 + 120 + offset * 1800
                dts_dep = dts_arr + 20
                stop_id = f"{random_stations[stopidx]}{stopidx+1}"
                stop = stops.get(stop_id)
                trip_stop_time = TripStopTime(trip, stopidx, stop, dts_arr, dts_dep)

                trip_stop_times.add(trip_stop_time)
                trip.add_stop_time(trip_stop_time)

            # Add trip
            if trip:
                trips.add(trip)

            trip_number += 1

    # Timetable
    timetable.stations = stations
    timetable.stops = stops
    timetable.trips = trips
    timetable.trip_stop_times = trip_stop_times

    return timetable
