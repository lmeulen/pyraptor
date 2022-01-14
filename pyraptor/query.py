"""Run query with RAPTOR algorithm"""
import argparse
from time import perf_counter

import numpy as np
from loguru import logger

from pyraptor.dao.timetable import Timetable, read_timetable
from pyraptor.dao.results import write_results
from pyraptor.model.raptor import (
    print_journey,
    traverse_trips,
    reconstruct_journey,
    final_destination,
    add_transfer_time,
)
from pyraptor.util import (
    str2sec,
    SAVE_RESULTS,
    T24H,
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
        print_journey(timetable, journey, dep_secs)

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

    start = perf_counter()

    from_stops = timetable.stations.get(origin_station).stops
    to_stops = timetable.stations.get(destination_station).stops

    # Initialize lookup with start node taking 0 seconds to reach
    # Bag contains per stop (travel_time, trip_id, previous_stop), trip_id is 0 in case of a transfer
    number_stops = len(timetable.stops) + 1
    bag = np.full(
        shape=(number_stops, 3),
        fill_value=(T24H, 0, -1),
        dtype=np.dtype(np.int32, np.int32, np.int32),
    )

    # Add origin stops to bag
    logger.debug("Starting from Stop IDs: {}".format(str(from_stops)))

    new_stops = []
    for from_stop in from_stops:
        bag[from_stop.index] = (0, 0, 0)
        new_stops.append(from_stop)

    # Run Round-Based Algorithm
    bag_k = {}
    evaluations = []

    for k in range(1, rounds + 1):

        logger.info("Analyzing possibilities round {}".format(k))

        # Get list of stops to evaluate in the process
        logger.debug("Stops to evaluate count: {}".format(len(new_stops)))

        # Update time to stops calculated based on stops reachable
        t = perf_counter()
        new_stops_travel, bag, evaluations = traverse_trips(
            timetable, evaluations, k, new_stops, bag, dep_secs
        )
        logger.debug(
            "Travel stops  calculated in {:0.4f} seconds".format(perf_counter() - t)
        )
        logger.debug("{} reachable stops added".format(len(new_stops_travel)))

        # Now add footpath transfers and update
        t = perf_counter()
        new_stops_transfer, bag = add_transfer_time(new_stops_travel, bag)
        logger.debug(
            "Transfers calculated in {:0.4f} seconds".format(perf_counter() - t)
        )
        logger.debug("{} transferable stops added".format(len(new_stops_transfer)))

        new_stops = set(new_stops_travel).union(new_stops_transfer)
        logger.debug("{} stops to evaluate in next round".format(len(new_stops)))

        # Store the results for this round
        bag_k[k] = np.copy(bag)

    # Determine the best destination ID, destination is a platform
    dest_stop = final_destination(to_stops, bag)
    if dest_stop != 0:
        logger.debug("Destination code   : {} ".format(dest_stop))
        logger.info(
            "Time to destination: {} minutes".format(bag[dest_stop.index][0] / 60)
        )
    else:
        logger.info("Destination unreachable with given parameters")

    logger.debug("Performing RAPTOR took {} seconds", perf_counter() - start)

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
