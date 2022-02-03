"""Run query with RAPTOR algorithm"""
import argparse
from copy import copy

from loguru import logger

from pyraptor.dao.timetable import Timetable, read_timetable
from pyraptor.model.mcraptor import (
    McRaptorAlgorithm,
    reconstruct_journeys,
    add_journey_details,
    final_destination,
    print_journey,
)
from pyraptor.util import str2sec


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="output/optimized_timetable",
        help="Input directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output/results",
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
        default=1,
        help="Number of rounds to execute the RAPTOR algorithm",
    )
    arguments = parser.parse_args()
    return arguments


def main(
    input_folder,
    output_folder,
    origin_station,
    destination_station,
    departure_time,
    rounds,
):
    """Run RAPTOR algorithm"""

    logger.debug("Input directory     : {}", input_folder)
    logger.debug("Output directory    : {}", output_folder)
    logger.debug("Origin station      : {}", origin_station)
    logger.debug("Destination station : {}", destination_station)
    logger.debug("Departure time      : {}", departure_time)
    logger.debug("Rounds              : {}", str(rounds))

    timetable = read_timetable(input_folder)

    logger.info("Calculating network from : {}".format(origin_station))

    # Departure time seconds
    dep_secs = str2sec(departure_time)
    logger.debug("Departure time (s.)  : " + str(dep_secs))

    # Find route between two stations
    bag_k, final_dest = run_mcraptor(
        timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    # Output journey
    if final_dest != 0:
        journey = reconstruct_journeys(final_dest, bag=bag_k[rounds])
        detailed_journey = add_journey_details(timetable, journey)
        print_journey(timetable, detailed_journey, dep_secs)


def run_mcraptor(
    timetable: Timetable,
    origin_station: str,
    destination_station: str,
    dep_secs: int,
    rounds: int,
):
    """
    Perform the McRaptor algorithm.

    :param timetable: timetable
    :param origin_station: Name of origin station
    :param destination_station: Name of destation station
    :param dep_secs: Time of departure in seconds
    :param rounds: Number of iterations to perform
    """

    # Get stops for origins and destinations
    from_stops = timetable.stations.get(origin_station).stops
    to_stops = timetable.stations.get(destination_station).stops

    # Run Round-Based Algorithm
    raptor = McRaptorAlgorithm(timetable)
    bag_round_stop = raptor.run(from_stops, dep_secs, rounds)

    # Determine the best destination ID, destination is a platform
    best_bag = copy(bag_round_stop[rounds])
    dest_stops = final_destination(to_stops, best_bag)

    if len(dest_stops) != 0:
        logger.debug("Destination code(s)  : {} ".format(dest_stops))
    else:
        logger.info("Destination unreachable with given parameters")

    return bag_round_stop, dest_stops


if __name__ == "__main__":
    args = parse_arguments()
    main(
        args.input,
        args.output,
        args.origin,
        args.destination,
        args.time,
        args.rounds,
    )
