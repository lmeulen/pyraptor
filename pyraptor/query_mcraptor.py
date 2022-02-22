"""Run query with RAPTOR algorithm"""
import argparse
from typing import List, Dict
from copy import copy
from time import perf_counter

from loguru import logger

from pyraptor.dao.timetable import read_timetable
from pyraptor.model.structures import Timetable, Journey, Station
from pyraptor.model.mcraptor import (
    McRaptorAlgorithm,
    reconstruct_journeys,
    best_legs_to_destination_station,
)
from pyraptor.util import str2sec


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
        help="Destination station of the journey",
    )
    parser.add_argument(
        "-t", "--time", type=str, default="08:35:00", help="Departure time (hh:mm:ss)"
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
    input_folder,
    origin_station,
    destination_station,
    departure_time,
    rounds,
):
    """Run RAPTOR algorithm"""

    logger.debug("Input directory     : {}", input_folder)
    logger.debug("Origin station      : {}", origin_station)
    logger.debug("Destination station : {}", destination_station)
    logger.debug("Departure time      : {}", departure_time)
    logger.debug("Rounds              : {}", str(rounds))

    timetable = read_timetable(input_folder)

    logger.info(f"Calculating network from : {origin_station}")

    # Departure time seconds
    dep_secs = str2sec(departure_time)
    logger.debug("Departure time (s.)  : " + str(dep_secs))

    # Find route between two stations
    journeys_to_destinations = run_mcraptor(
        timetable,
        origin_station,
        dep_secs,
        rounds,
    )

    # Output journey
    journeys = journeys_to_destinations[destination_station]
    if len(journeys) != 0:
        for jrny in journeys:
            jrny.print(dep_secs=dep_secs)


def run_mcraptor(
    timetable: Timetable,
    origin_station: str,
    dep_secs: int,
    rounds: int,
) -> Dict[Station, List[Journey]]:
    """
    Perform the McRaptor algorithm.

    :param timetable: timetable
    :param origin_station: Name of origin station
    :param dep_secs: Time of departure in seconds
    :param rounds: Number of iterations to perform
    """

    # Run Round-Based Algorithm for an origin station
    from_stops = timetable.stations.get(origin_station).stops
    raptor = McRaptorAlgorithm(timetable)
    bag_round_stop = raptor.run(from_stops, dep_secs, rounds)
    last_round_bag = copy(bag_round_stop[rounds])

    # Calculate journets to all destinations
    logger.info("Calculating journeys to all destinations")
    s = perf_counter()

    destination_stops = {
        st.name: timetable.stations.get_stops(st.name) for st in timetable.stations
    }
    destination_stops.pop(origin_station, None)

    journeys_to_destinations = dict()
    for destination_station_name, to_stops in destination_stops.items():
        destination_legs = best_legs_to_destination_station(to_stops, last_round_bag)

        if len(destination_legs) == 0:
            logger.info("Destination unreachable with given parameters")
            continue

        journeys = reconstruct_journeys(
            from_stops, destination_legs, bag_round_stop, k=rounds
        )
        journeys_to_destinations[destination_station_name] = journeys

    logger.info(f"Journey calculation time: {perf_counter() - s}")

    return journeys_to_destinations


if __name__ == "__main__":
    args = parse_arguments()
    main(
        args.input,
        args.origin,
        args.destination,
        args.time,
        args.rounds,
    )
