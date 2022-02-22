"""Run range query on RAPTOR algorithm"""
import argparse
from typing import Dict, List
from copy import copy
from time import perf_counter

from loguru import logger

from pyraptor.dao.timetable import read_timetable
from pyraptor.model.structures import Timetable, Journey, pareto_set
from pyraptor.model.mcraptor import (
    McRaptorAlgorithm,
    best_legs_to_destination_station,
    reconstruct_journeys,
)
from pyraptor.util import str2sec, sec2str


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="data/output",
        help="Input directory",
    )
    parser.add_argument(
        "-or",
        "--origin",
        type=str,
        default="Hertogenbosch ('s)",
        help="Origin station of the journey",
    )
    parser.add_argument(
        "-d",
        "--destination",
        type=str,
        default="Rotterdam Centraal",
        help="Destination station of the journey for logging purposes",
    )
    parser.add_argument(
        "-st",
        "--starttime",
        type=str,
        default="08:00:00",
        help="Start departure time (hh:mm:ss)",
    )
    parser.add_argument(
        "-et",
        "--endtime",
        type=str,
        default="08:30:00",
        help="End departure time (hh:mm:ss)",
    )
    parser.add_argument(
        "-r",
        "--rounds",
        type=int,
        default=5,
        help="Number of rounds to execute the RAPTOR algorithm",
    )
    arguments = parser.parse_args()

    return arguments


def main(
    input_folder: str,
    origin_station: str,
    destination_station: str,
    departure_start_time: str,
    departure_end_time: str,
    rounds: int,
):
    """Run RAPTOR algorithm"""

    logger.debug("Input directory      : {}", input_folder)
    logger.debug("Origin station       : {}", origin_station)
    logger.debug("Destination station  : {}", destination_station)
    logger.debug("Departure start time : {}", departure_start_time)
    logger.debug("Departure end time   : {}", departure_end_time)
    logger.debug("Rounds               : {}", str(rounds))

    timetable = read_timetable(input_folder)

    logger.info(f"Calculating network from : {origin_station}")

    # Departure time seconds for time range
    dep_secs_min = str2sec(departure_start_time)
    dep_secs_max = str2sec(departure_end_time)
    logger.debug(f"Departure time range (s.)  : ({dep_secs_min}, {dep_secs_max})")

    # Find route between two stations for time range, i.e. Range Query
    journeys_to_destinations = run_range_mcraptor(
        timetable,
        origin_station,
        dep_secs_min,
        dep_secs_max,
        rounds,
    )

    # All destinations are calculated, however, we only print one for logging purposes
    logger.info(f"Journeys to destination station '{destination_station}'")
    for jrny in journeys_to_destinations[destination_station]:
        jrny.print()


def run_range_mcraptor(
    timetable: Timetable,
    origin_station: str,
    dep_secs_min: int,
    dep_secs_max: int,
    rounds: int,
) -> Dict[str, List[Journey]]:
    """
    Perform the McRAPTOR algorithm for a range query
    """

    # Get stops for origins and destinations
    from_stops = timetable.stations.get_stops(origin_station)
    destination_stops = {
        st.name: timetable.stations.get_stops(st.name) for st in timetable.stations
    }
    destination_stops.pop(origin_station, None)

    # Find all trips leaving from stops within time range
    potential_trip_stop_times = timetable.trip_stop_times.get_trip_stop_times_in_range(
        from_stops, dep_secs_min, dep_secs_max
    )
    potential_dep_secs = sorted(
        list(set([tst.dts_dep for tst in potential_trip_stop_times])), reverse=True
    )

    logger.info(
        "Potential departure times : {}".format(
            [sec2str(x) for x in potential_dep_secs]
        )
    )

    journeys_to_destinations = {
        station_name: [] for station_name, _ in destination_stops.items()
    }

    # Find Pareto-optimal journeys for all possible departure times
    for dep_index, dep_secs in enumerate(potential_dep_secs):
        logger.info(f"Processing {dep_index} / {len(potential_dep_secs)}")
        logger.info(f"Analyzing best journey for departure time {sec2str(dep_secs)}")

        # Run Round-Based Algorithm
        mcraptor = McRaptorAlgorithm(timetable)
        bag_round_stop = mcraptor.run(from_stops, dep_secs, rounds)
        last_round_bag = copy(bag_round_stop[rounds])

        # Determine the best destination ID, destination is a platform
        logger.info("Calculating journeys to all destinations")
        s = perf_counter()

        for destination_station_name, to_stops in destination_stops.items():
            destination_legs = best_legs_to_destination_station(
                to_stops, last_round_bag
            )

            if len(destination_legs) != 0:
                journeys = reconstruct_journeys(
                    from_stops, destination_legs, bag_round_stop, k=rounds
                )
                journeys_to_destinations[destination_station_name].extend(journeys)

        logger.info(f"Journey calculation time: {perf_counter() - s}")

    # Keep Pareto-optimal journeys
    for destination_station_name, journeys in journeys_to_destinations.items():
        best_journeys = pareto_set(journeys, keep_equal=True)
        journeys_to_destinations[destination_station_name] = best_journeys

    return journeys_to_destinations


if __name__ == "__main__":
    args = parse_arguments()
    main(
        args.input,
        args.origin,
        args.destination,
        args.starttime,
        args.endtime,
        args.rounds,
    )
