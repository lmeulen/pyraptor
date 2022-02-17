"""Parse timetable from GTFS files"""
import os
import argparse
from typing import List
from dataclasses import dataclass
from collections import defaultdict

import pandas as pd
from loguru import logger

from pyraptor.dao import write_timetable
from pyraptor.util import mkdir_if_not_exists, str2sec, TRANSFER_COST
from pyraptor.model.structures import (
    Timetable,
    Stop,
    Stops,
    Trip,
    Trips,
    TripStopTime,
    TripStopTimes,
    Station,
    Stations,
    Routes,
    Transfer,
    Transfers,
)


@dataclass
class GtfsTimetable:
    """Gtfs Timetable data"""

    trips = None
    calendar = None
    stop_times = None
    stops = None


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="data/input/NL-gtfs",
        help="Input directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="data/output",
        help="Input directory",
    )
    parser.add_argument(
        "-d", "--date", type=str, default="20210906", help="Departure date (yyyymmdd)"
    )
    parser.add_argument("-a", "--agencies", nargs="+", default=["NS"])
    parser.add_argument("--icd", action="store_true", help="Add ICD fare(s)")
    arguments = parser.parse_args()
    return arguments


def main(
    input_folder: str,
    output_folder: str,
    departure_date: str,
    agencies: List[str],
    icd_fix: bool = False,
):
    """Main function"""

    logger.info("Parse timetable from GTFS files")
    mkdir_if_not_exists(output_folder)

    gtfs_timetable = read_gtfs_timetable(input_folder, departure_date, agencies)
    timetable = gtfs_to_pyraptor_timetable(gtfs_timetable, icd_fix)
    write_timetable(output_folder, timetable)


def read_gtfs_timetable(
    input_folder: str, departure_date: str, agencies: List[str]
) -> GtfsTimetable:
    """Extract operators from GTFS data"""

    logger.info("Read GTFS data")

    # Read agencies
    logger.debug("Read Agencies")

    agencies_df = pd.read_csv(os.path.join(input_folder, "agency.txt"))
    agencies_df = agencies_df.loc[agencies_df["agency_name"].isin(agencies)][
        ["agency_id", "agency_name"]
    ]
    agency_ids = agencies_df.agency_id.values

    # Read routes
    logger.debug("Read Routes")

    routes = pd.read_csv(os.path.join(input_folder, "routes.txt"))
    routes = routes[routes.agency_id.isin(agency_ids)]
    routes = routes[
        ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"]
    ]

    # Read trips
    logger.debug("Read Trips")

    trips = pd.read_csv(os.path.join(input_folder, "trips.txt"))
    trips = trips[trips.route_id.isin(routes.route_id.values)]
    trips = trips[
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_short_name",
            "trip_long_name",
        ]
    ]
    trips["trip_short_name"] = trips["trip_short_name"].astype(int)

    # Read calendar
    logger.debug("Read Calendar")

    calendar = pd.read_csv(
        os.path.join(input_folder, "calendar_dates.txt"), dtype={"date": str}
    )
    calendar = calendar[calendar.service_id.isin(trips.service_id.values)]

    # Add date to trips and filter on departure date
    trips = trips.merge(calendar[["service_id", "date"]], on="service_id")
    trips = trips[trips.date == departure_date]

    # Read stop times
    logger.debug("Read Stop Times")

    stop_times = pd.read_csv(
        os.path.join(input_folder, "stop_times.txt"), dtype={"stop_id": str}
    )
    stop_times = stop_times[stop_times.trip_id.isin(trips.trip_id.values)]
    stop_times = stop_times[
        [
            "trip_id",
            "stop_sequence",
            "stop_id",
            "arrival_time",
            "departure_time",
        ]
    ]
    # Convert times to seconds
    stop_times["arrival_time"] = stop_times["arrival_time"].apply(str2sec)
    stop_times["departure_time"] = stop_times["departure_time"].apply(str2sec)

    # Read stops (platforms)
    logger.debug("Read Stops")

    stops_full = pd.read_csv(
        os.path.join(input_folder, "stops.txt"), dtype={"stop_id": str}
    )
    stops = stops_full.loc[
        stops_full["stop_id"].isin(stop_times.stop_id.unique())
    ].copy()

    # Read stopareas, i.e. stations
    stopareas = stops["parent_station"].unique()
    # stops = stops.append(.copy())
    stops = pd.concat([stops, stops_full.loc[stops_full["stop_id"].isin(stopareas)]])

    # stops["zone_id"] = stops["zone_id"].str.replace("IFF:", "").str.upper()
    stops["stop_code"] = stops.stop_code.str.upper()
    stops = stops[
        [
            "stop_id",
            "stop_name",
            "parent_station",
            "platform_code",
        ]
    ]

    # Filter out the general station codes
    stops = stops.loc[~stops.parent_station.isna()]

    gtfs_timetable = GtfsTimetable()
    gtfs_timetable.trips = trips
    gtfs_timetable.stop_times = stop_times
    gtfs_timetable.stops = stops

    return gtfs_timetable


def gtfs_to_pyraptor_timetable(
    gtfs_timetable: GtfsTimetable, icd_fix: bool = False
) -> Timetable:
    """
    Convert timetable for usage in Raptor algorithm.
    """
    logger.info("Convert GTFS timetable to timetable for PyRaptor algorithm")

    # Stations and stops, i.e. platforms
    logger.debug("Add stations and stops")

    stations = Stations()
    stops = Stops()

    gtfs_timetable.stops.platform_code = gtfs_timetable.stops.platform_code.fillna("?")

    for s in gtfs_timetable.stops.itertuples():
        station = Station(s.stop_name, s.stop_name)
        station = stations.add(station)

        stop_id = f"{s.stop_name}-{s.platform_code}"
        stop = Stop(s.stop_id, stop_id, station, s.platform_code)

        station.add_stop(stop)
        stops.add(stop)

    # Stop Times
    stop_times = defaultdict(list)
    for stop_time in gtfs_timetable.stop_times.itertuples():
        stop_times[stop_time.trip_id].append(stop_time)

    # Trips and Trip Stop Times
    logger.debug("Add trips and trip stop times")

    trips = Trips()
    trip_stop_times = TripStopTimes()

    for trip_row in gtfs_timetable.trips.itertuples():
        trip = Trip()
        trip.hint = trip_row.trip_short_name  # i.e. treinnummer
        trip.long_name = trip_row.trip_long_name  # e.g., Sprinter

        # Iterate over stops
        sort_stop_times = sorted(
            stop_times[trip_row.trip_id], key=lambda s: int(s.stop_sequence)
        )
        for stopidx, stop_time in enumerate(sort_stop_times):
            # Timestamps
            dts_arr = stop_time.arrival_time
            dts_dep = stop_time.departure_time

            # Trip Stop Times
            stop = stops.get(stop_time.stop_id)

            # GTFS files do not contain ICD supplement fare, so hard-coded here
            fare = calculate_icd_fare(trip, stop, stations) if icd_fix is True else 0
            trip_stop_time = TripStopTime(trip, stopidx, stop, dts_arr, dts_dep, fare)

            trip_stop_times.add(trip_stop_time)
            trip.add_stop_time(trip_stop_time)

        # Add trip
        if trip:
            trips.add(trip)

    # Routes
    logger.debug("Add routes")

    routes = Routes()
    for trip in trips:
        routes.add(trip)

    # Transfers
    logger.debug("Add transfers")

    transfers = Transfers()
    for station in stations:
        station_stops = station.stops
        station_transfers = [
            Transfer(from_stop=stop_i, to_stop=stop_j, layovertime=TRANSFER_COST)
            for stop_i in station_stops
            for stop_j in station_stops
            if stop_i != stop_j
        ]
        for st in station_transfers:
            transfers.add(st)

    # Timetable
    timetable = Timetable(
        stations=stations,
        stops=stops,
        trips=trips,
        trip_stop_times=trip_stop_times,
        routes=routes,
        transfers=transfers,
    )
    timetable.counts()

    return timetable


def calculate_icd_fare(trip: Trip, stop: Stop, stations: Stations) -> int:
    """Get supplemental fare for ICD"""
    fare = 0
    if 900 <= trip.hint <= 1099:
        if (
            trip.hint % 2 == 0 and stop.station == stations.get("Schiphol Airport")
        ) or (
            trip.hint % 2 == 1 and stop.station == stations.get("Rotterdam Centraal")
        ):
            fare = 1.67
        else:
            fare = 0
    return fare


if __name__ == "__main__":
    args = parse_arguments()
    main(args.input, args.output, args.date, args.agencies, args.icd)
