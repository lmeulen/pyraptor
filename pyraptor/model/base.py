"""Shared functionality between RAPTOR algorithms"""
from typing import List

from loguru import logger

from pyraptor.model.structures import Journey
from pyraptor.util import sec2str


def print_journeys(journeys: List[Journey], dep_secs=None):
    """Print list of journeys"""
    for jrny in journeys:
        print_journey(jrny, dep_secs)


def print_journey(journey: Journey, dep_secs=None):
    """Print the given journey to logger info"""

    logger.info("Journey:")

    if len(journey) == 0:
        logger.info("No journey available")
        return

    # Print all legs in journey
    for leg in journey:
        # Start and end stop of leg and trip
        msg = (
            str(sec2str(leg.dep))
            + " "
            + leg.from_stop.station.name.ljust(20)
            + "(p. "
            + str(leg.from_stop.platform_code).rjust(3)
            + ") TO "
            + str(sec2str(leg.arr))
            + " "
            + leg.to_stop.station.name.ljust(20)
            + "(p. "
            + str(leg.to_stop.platform_code).rjust(3)
            + ") WITH "
            + str(leg.trip.hint)
        )
        logger.info(msg)

    logger.info(f"Fare: €{journey.fare()}")

    msg = f"Duration: {sec2str(journey.arr() - journey.dep())}"
    if dep_secs:
        msg += " ({} from request time {})".format(
            sec2str(journey.arr() - dep_secs),
            sec2str(dep_secs),
        )
    logger.info(msg)
