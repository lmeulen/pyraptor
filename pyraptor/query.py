"""Run query with RAPTOR algorithm"""
import argparse
from time import perf_counter

from loguru import logger

from pyraptor.dao.timetable import Timetable, read_timetable
from pyraptor.dao.results import write_results
from pyraptor.model.raptor import (
    RaptorAlgorithm,
    reconstruct_journey,
    add_journey_details,
    final_destination,
    print_journey,
)
from pyraptor.util import (
    str2sec,
    SAVE_RESULTS,
)


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
        default=4,
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
    start = perf_counter()
    bag_k, final_dest, evaluations = perform_raptor(
        timetable,
        origin_station,
        destination_station,
        dep_secs,
        rounds,
    )

    # Output journey
    if final_dest != 0:
        journey = reconstruct_journey(final_dest, bag=bag_k[rounds])
        detailed_journey = add_journey_details(timetable, journey)
        print_journey(timetable, detailed_journey, dep_secs)

    logger.info(
        "RAPTOR Algorithm executed in {:.4f} seconds".format(perf_counter() - start)
    )

    if SAVE_RESULTS:
        write_results(output_folder, timetable, bag_k, evaluations)


def perform_raptor(
    timetable: Timetable,
    origin_station: str,
    destination_station: str,
    dep_secs: int,
    rounds: int,
):
    """
    Perform the Raptor algorithm.

    :param origin_station: Name of origin station
    :param destination_station: Name of destation station
    :param dep_secs: Time of departure in seconds
    :param rounds: Number of iterations to perform
    """

    # Get stops for origins and destinations
    from_stops = timetable.stations.get(origin_station).stops
    to_stops = timetable.stations.get(destination_station).stops

    # Run Round-Based Algorithm
    raptor = RaptorAlgorithm(timetable)
    bag_k, evaluations = raptor.run(from_stops, dep_secs, rounds)

    # Determine the best destination ID, destination is a platform
    bag = bag_k[rounds]
    dest_stop = final_destination(to_stops, bag)
    if dest_stop != 0:
        logger.debug("Destination code   : {} ".format(dest_stop))
        logger.info(
            "Time to destination: {} minutes".format(bag[dest_stop.index][0] / 60)
        )
    else:
        logger.info("Destination unreachable with given parameters")

    return bag_k, dest_stop, evaluations


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
