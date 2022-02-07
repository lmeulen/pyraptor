"""Utility functions to create timetables for unit tests"""
from collections import defaultdict

import pandas as pd
from loguru import logger

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
    Routes,
)


def to_stops_and_trips(df: pd.DataFrame):
    """Parse stops and trips from input dataframe"""

    # Trips
    trips = df.filter(["treinnummer"]).drop_duplicates()
    trips["trip_id"] = range(len(trips))

    # Stops
    stops = df.filter(["code", "spoor"]).drop_duplicates().copy()

    # Split in parent and child stops, i.e. stations and platforms
    stops_parents = stops.copy()
    stops_parents["stop_id"] = stops_parents["code"]
    stops_parents["parent_stop_id"] = None
    stops_parents = stops_parents.drop(columns=["spoor"])

    stops_child = stops.copy()
    stops_child["parent_stop_id"] = stops_child["code"]
    stops_child["stop_id"] = stops_child.apply(lambda x: x["code"] + x["spoor"], axis=1)
    stops_child = stops_child.drop(columns=["spoor"])

    stops = pd.concat([stops_parents, stops_child]).drop_duplicates()
    stops = stops.loc[~stops.parent_stop_id.isna()]

    # Stop Times
    stop_times = df.copy()
    stop_times["stop_id"] = stop_times.apply(lambda x: x["code"] + x["spoor"], axis=1)
    stop_times = stop_times.filter(
        [
            "treinnummer",
            "stop_id",
            "dts_arr",
            "dts_dep",
            "trip_index",
            "fare",
        ]
    )
    stop_times = stop_times.merge(trips, how="left", on=["treinnummer"])

    return stops, stop_times, trips


def to_timetable(stops_df, stop_times_df, trips_df) -> Timetable:
    """Convert a pandas timetable to Raptor algorithm datatypes"""

    # Stations and stops, i.e. platforms
    stations = Stations()
    stops = Stops()

    for s in stops_df.itertuples():
        station = Station(s.stop_uic, s.stop_uic)
        station = stations.add(station)

        stop = Stop(s.stop_id, s.stop_id, station, s.stop_id)

        station.add_stop(stop)
        stops.add(stop)

    # Stop Times
    stop_times = defaultdict(list)
    for stop_time in stop_times_df.itertuples():
        stop_times[stop_time.trip_id].append(stop_time)

    # Trips and Trip Stop Times
    trips = Trips()
    trip_stop_times = TripStopTimes()

    for trip_row in trips_df.itertuples():
        trip = Trip()
        trip.hint = trip_row.treinnummer  # treinnummer

        # Iterate over stops
        sort_stop_times = sorted(
            stop_times[trip_row.trip_id], key=lambda s: int(s.vervoerstrajectindex)
        )
        for stopidx, stop_time in enumerate(sort_stop_times):

            # Timestamps
            dts_arr = stop_time.aankomstmoment_utc
            dts_dep = stop_time.vertrekmoment_utc
            # Fair
            fare = stop_time.toeslag

            # Trip Stop Times
            stop = stops.get(stop_time.stop_id)
            trip_stop_time = TripStopTime(trip, stopidx, stop, dts_arr, dts_dep, fare)

            # Trip Stop Times
            trip_stop_times.add(trip_stop_time)
            trip.add_stop_time(trip_stop_time)

        # Add trip
        if trip:
            trips.add(trip)

    routes = Routes()
    for trip in trips:
        routes.add(trip)

    timetable_ = Timetable()
    timetable_.stations = stations
    timetable_.stops = stops
    timetable_.trips = trips
    timetable_.trip_stop_times = trip_stop_times
    timetable_.routes = routes

    logger.debug("Counts:")
    logger.debug("Stations   : {}", len(stations))
    logger.debug("Routes     : {}", len(routes))
    logger.debug("Trips      : {}", len(trips))
    logger.debug("Stops      : {}", len(stops))
    logger.debug("Stop Times : {}", len(trip_stop_times))

    return timetable_
