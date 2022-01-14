"""Parse timetable from GTFS files"""
import os
import argparse
from typing import List
from dataclasses import dataclass
from collections import defaultdict

import pandas as pd
from loguru import logger

from pyraptor.dao.timetable import Timetable, write_timetable
from pyraptor.util import mkdir_if_not_exists, str2sec
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


@dataclass
class GtfsTimetable:
    """Gtfs Timetable data"""

    routes = None
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
        default="data/NL-gtfs",
        help="Input directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output/optimized_timetable",
        help="Input directory",
    )
    parser.add_argument(
        "-d", "--date", type=str, default="20210906", help="Departure date (yyyymmdd)"
    )
    parser.add_argument("-a", "--agencies", nargs="+", default=["NS"])
    arguments = parser.parse_args()
    return arguments


def main(
    input_folder: str, output_folder: str, departure_date: str, agencies: List[str]
):
    """Main function"""

    logger.info("Parse timetable from GTFS files")
    mkdir_if_not_exists(output_folder)

    gtfs_timetable = read_gtfs_timetable(input_folder, departure_date, agencies)
    timetable = gtfs_to_pyraptor_timetable(gtfs_timetable)
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
    stops = stops.append(stops_full.loc[stops_full["stop_id"].isin(stopareas)].copy())

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

    logger.debug("Counts:")
    logger.debug("Routes     : {}", len(routes))
    logger.debug("Trips      : {}", len(trips))
    logger.debug("Stops      : {}", len(stops))
    logger.debug("Stop Times : {}", len(stop_times))

    gtfs_timetable = GtfsTimetable()
    gtfs_timetable.routes = routes
    gtfs_timetable.trips = trips
    gtfs_timetable.stop_times = stop_times
    gtfs_timetable.stops = stops

    return gtfs_timetable


def gtfs_to_pyraptor_timetable(gtfs_timetable: GtfsTimetable) -> Timetable:
    """
    Convert timetable for usage in Raptor algorithm.
    """
    logger.info("Convert GTFS timetable to timetable for PyRaptor algorithm")

    # Stations and stops, i.e. platforms
    stations = Stations()
    stops = Stops()

    for s in gtfs_timetable.stops.itertuples():
        # TODO parent_station instead of name as id
        station = Station(s.stop_name, s.stop_name)
        station = stations.add(station)

        stop = Stop(s.stop_id, s.stop_id, station, s.platform_code)

        station.add_stop(stop)
        stops.add(stop)

    # Stop Times
    stop_times = defaultdict(list)
    for stop_time in gtfs_timetable.stop_times.itertuples():
        stop_times[stop_time.trip_id].append(stop_time)

    # Trips and Trip Stop Times
    trips = Trips()
    trip_stop_times = TripStopTimes()

    for trip_row in gtfs_timetable.trips.itertuples():
        trip = Trip()
        trip.hint = trip_row.trip_short_name  # i.e. treinnummer

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
            trip_stop_time = TripStopTime(trip, stopidx, stop, dts_arr, dts_dep)

            trip_stop_times.add(trip_stop_time)
            trip.add_stop_time(trip_stop_time)

        # Add trip
        if trip:
            trips.add(trip)

    timetable = Timetable()
    timetable.stations = stations
    timetable.stops = stops
    timetable.trips = trips
    timetable.trip_stop_times = trip_stop_times

    return timetable


if __name__ == "__main__":
    args = parse_arguments()
    main(args.input, args.output, args.date, args.agencies)
