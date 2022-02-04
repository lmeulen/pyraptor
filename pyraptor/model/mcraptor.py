"""McRAPTOR algorithm"""
from __future__ import annotations
from typing import List, Tuple, Dict
from collections import namedtuple
from pprint import pprint
from copy import copy, deepcopy

from dataclasses import dataclass, field
from loguru import logger
import numpy as np

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop, Trip, Routes, Route
from pyraptor.util import (
    sec2str,
    TRANSFER_COST,
)

Leg = namedtuple("Leg", ["from_stop", "trip_id", "to_stop", "travel_time", "fare"])
LegDetails = namedtuple(
    "LegDetails", ["leg_index", "from_stop", "to_stop", "trip", "dep", "arr"]
)


def pareto_set_labels(labels: List[Label]):
    """
    Find the pareto-efficient points
    :param labels: list with labels
    :return: list with pairwise non-dominating labels
    """

    is_efficient = np.ones(len(labels), dtype=bool)
    labels_criteria = np.array([label.criteria for label in labels])
    for i, label in enumerate(labels_criteria):
        if is_efficient[i]:
            # Keep any point with a lower cost
            is_efficient[is_efficient] = np.any(
                labels_criteria[is_efficient] < label, axis=1
            )
            is_efficient[i] = True  # And keep self

    return [labels for i, labels in enumerate(labels) if is_efficient[i]]


@dataclass
class Label:
    travel_time: int
    fare: int
    trip_id: int  # trip_id of trip to take to obtain travel_time and fare
    from_stop: Stop  # stop at which we hop-on trip with trip_id

    @property
    def criteria(self):
        return [self.travel_time, self.fare]

    def update(self, travel_time=None, fare=None):
        if travel_time:
            self.travel_time = travel_time
        if fare:
            self.fare = fare

    def __lt__(self, other: Label):
        return self.travel_time < other.travel_time and self.fare < other.fare

    def __gt__(self, other: Label):
        return self.travel_time > other.travel_time and self.fare > other.fare

    def __le__(self, other: Label):
        return self.travel_time <= other.travel_time and self.fare <= other.fare

    def __ge__(self, other: Label):
        return self.travel_time >= other.travel_time and self.fare >= other.fare


@dataclass
class Bag:
    """
    Bag B(k,p) or route bag B_r
    """

    labels: List[Label] = field(default_factory=list)

    def __len__(self):
        return len(self.labels)

    def add(self, label: Label):
        self.labels.append(label)

    def merge(self, bag: Bag) -> None:
        self.labels.extend(bag.labels)
        self.labels = pareto_set_labels(self.labels)


class McRaptorAlgorithm:
    """McRAPTOR Algorithm"""

    def __init__(self, timetable: Timetable):
        self.timetable = timetable

    def run(self, from_stops, dep_secs, rounds):
        """Run Round-Based Algorithm"""

        # Initialize empty bag, i.e. B_k(p) = [] for every k and p
        # number_stops = len(self.timetable.stops) + 1
        bag_round_stop: Dict[int, Dict[Stop, Bag]] = {}
        for k in range(0, rounds + 1):
            bag_round_stop[k] = {}
            for p in self.timetable.stops:
                bag_round_stop[k][p] = Bag()

        # Print all stops for debugging
        for stop in self.timetable.stops:
            logger.debug(f"{stop}")

        # Add origin stops to bag
        logger.debug("Starting from Stop IDs: {}".format(str(from_stops)))

        # Initialize bag for round 0, i.e. add Labels with criterion 0 for all from stops
        for from_stop in from_stops:
            bag_round_stop[0][from_stop].add(Label(0, 0, 0, from_stop))

        marked_stops = from_stops

        # Run rounds
        for k in range(1, rounds + 1):

            logger.info("Analyzing possibilities round {}".format(k))

            # Get list of stops to evaluate in the process
            logger.debug("Stops to evaluate count: {}".format(len(marked_stops)))

            # Accumulate routes serving marked stops from previous round
            route_marked_stops = {}  # i.e. Q
            for marked_stop in marked_stops:
                routes_serving_stop = self.timetable.routes.get_routes_of_stop(
                    marked_stop
                )
                for route in routes_serving_stop:
                    # Check if new_stop is before existing stop in Q
                    current_stop_for_route = route_marked_stops.get(route, None)  # p'
                    if (current_stop_for_route is None) or (
                        route.stop_index(current_stop_for_route)
                        > route.stop_index(marked_stop)
                    ):
                        route_marked_stops[route] = marked_stop
            route_marked_stops = [(r, p) for r, p in route_marked_stops.items()]

            # Traverse each route
            bag_round_stop, new_marked_stops = self.traverse_trips(
                deepcopy(bag_round_stop), k, route_marked_stops, dep_secs
            )

            pprint(bag_round_stop)

            # logger.debug("{} reachable stops added".format(len(new_stops_travel)))

            # Now add footpath transfers and update
            # bag_round_stop = self.add_transfer_time(deepcopy(bag_round_stop), k)

            # pprint(bag_round_stop)

            # logger.debug("{} transferable stops added".format(len(new_stops_transfer)))

            # new_stops = set(new_stops_travel).union(new_stops_transfer)
            # logger.debug("{} stops to evaluate in next round".format(len(new_stops)))

        return bag_round_stop

    def traverse_trips(
        self,
        bag_round_stop: Dict[int, Dict[int, Bag]],
        k: int,
        route_marked_stops: List[Tuple[Route, Stop]],
        dep_secs: int,
    ) -> Tuple:
        """
        Iterator through the stops reachable and add all new reachable stops
        by following all trips from the reached stations. Trips are only followed
        in the direction of travel and beyond already added points.

        :param bag_round_stop: Bag per round per stop
        :param k: current round
        :param route_marked_stops: list of marked (route, stop) for evaluation
        :param dep_secs: Departure time in seconds
        """
        logger.debug(f"Traverse trips for round {k}")

        n_evaluations = 0
        n_improvements = 0

        # TODO: Fill
        new_marked_stops = []

        for (marked_route, marked_stop) in route_marked_stops:

            logger.debug(f"Route {marked_route}, Stop {marked_stop}")

            # Get all stops after current stop within the current route
            current_stop_index = marked_route.stop_index(marked_stop)
            remaining_stops_in_route = marked_route.stops[current_stop_index:]

            # Lege route bag aanmaken
            route_bag = Bag()

            for next_stop_index, current_stop in enumerate(remaining_stops_in_route):
                # step 1: update arrival times and other criteria of every label L from Br
                for label in route_bag.labels:
                    trip = self.timetable.trips[label.trip_id]
                    trip_stop_idx = current_stop_index + next_stop_index
                    trip_stop_time = self.timetable.trip_stop_times.set_idx[
                        (trip, trip_stop_idx)
                    ]
                    label.update(
                        travel_time=trip_stop_time.dts_arr, fare=trip_stop_time.fare
                    )

                # step 2: merge bag_route into bag_round_stop and remove dominated labels
                bag_round_stop[k][current_stop].merge(route_bag)

                # step 3: merge B_{k-1}(p) into B_r
                route_bag.merge(bag_round_stop[k - 1][current_stop])

                # assign trips to all newly added labels
                for label in route_bag.labels:
                    pass

        logger.debug("- Evaluations    : {}".format(n_evaluations))
        logger.debug("- Improvements   : {}".format(n_improvements))

        return bag_round_stop, new_marked_stops

    def add_transfer_time(
        self, bag_round_stop: Dict[int, Dict[int, List[Label]]], k: int
    ) -> Tuple:
        """Add transfers between platforms."""

        logger.debug("Add transfer times...")

        # Add in transfers to other platforms

        return bag_round_stop

    def get_transfer_time(
        self, stop_from: int, stop_to: int, time_sec: int, dow: int
    ) -> int:
        """
        Calculate the transfer time from a stop to another stop (usually two platforms at one station
        :param stop_from: Origin platform
        :param stop_to: Destination platform
        :param time_sec: Time of day (seconds since midnight)
        :param dow: day of week (Monday = 0, Tuesday = 1, ...)
        """
        return TRANSFER_COST


def final_destination(
    to_stops: List[Stop], best_bag: Dict[int, List[Label]]
) -> List[Leg]:
    """
    Find the destination IDs that are not dominated by other journeys.
    Required in order to prevent adding travel time to the arrival time.
    """
    destinations = []

    for stop in to_stops:
        for label in best_bag[stop.index]:

            # Label to leg
            leg = Leg(
                label.previous_stop, label.trip_id, stop, label.travel_time, label.fare
            )

            # TODO: Filter with pareto function

    return destinations


def reconstruct_journeys(
    destination_labels: List[Leg], best_bag: Dict[int, List[Label]]
) -> List[List[Leg]]:
    """Construct journeys for destinations from values in bag."""

    # Create journeys with list of legs
    def loop(best_bag: Dict[int, List[Label]], all_journeys: List[List[Leg]]):
        """Create journeys as list of Legs"""
        for jrny in all_journeys:
            current_leg = jrny[-1]
            current_stop = current_leg.previous_stop

            # End of journey
            if current_leg.trip_id == 0:
                yield jrny
                break

            # Loop trough each new leg
            for new_label in best_bag[current_stop.index]:
                new_leg = Leg(
                    new_label.previous_stop,
                    new_label.trip_id,
                    current_stop,
                    new_label.travel_time,
                    new_label.fare,
                )
                new_jrny = [jrny + [new_leg]]
                # print("new_jrny", new_jrny)
                for i in loop(best_bag, new_jrny):
                    yield i

    journeys = [[l] for l in destination_labels]
    journeys = loop(best_bag, journeys)
    journeys = [jrn[::-1] for jrn in journeys]  # reverse
    journeys = [[leg for leg in jrny if leg.trip_id != 0] for jrny in journeys]

    return journeys


def add_journey_details(
    timetable: Timetable, journeys: List[List[Leg]]
) -> List[List[LegDetails]]:
    """Add details to journey. More computational expensive so not done before."""

    detailed_journeys = []
    for journey in journeys:
        detailed = []
        for index, leg in enumerate(journey):
            # Get stop, trip and time information
            from_stop = leg.previous_stop
            to_stop = leg.to_stop
            trip = timetable.trips.set_idx[leg.trip_id]
            dep = [tst.dts_dep for tst in trip.stop_times if from_stop == tst.stop][0]
            arr = [tst.dts_arr for tst in trip.stop_times if to_stop == tst.stop][0]

            leg_details = LegDetails(
                leg_index=index,
                from_stop=from_stop,
                to_stop=to_stop,
                trip=trip,
                dep=dep,
                arr=arr,
            )
            detailed.append(leg_details)

        detailed_journeys.append(detailed)
    return detailed_journeys


def print_journeys(journeys: List[List[LegDetails]], dep_secs=None):
    """Print list of journeys"""
    for jrny in journeys:
        print_journey(jrny, dep_secs)


def print_journey(journey: List[LegDetails], dep_secs=None):
    """Print the given journey to logger info"""
    logger.info("Journey:")

    if len(journey) == 0:
        logger.info("No journey available")
        return

    # Print all legs in journey
    for leg in journey:
        # Stop and trip
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

    # Departure time of first leg
    depart_leg = journey[0]
    depart_stop_time = [
        st for st in depart_leg.trip.stop_times if st.stop == depart_leg.from_stop
    ][0]

    # Arrival time of last leg
    arrival_leg = journey[-1]
    arrival_stop_time = [
        st for st in arrival_leg.trip.stop_times if st.stop == arrival_leg.to_stop
    ][0]

    msg = "Duration : {}".format(
        sec2str(arrival_stop_time.dts_arr - depart_stop_time.dts_dep)
    )
    if dep_secs:
        msg += " ({} from request time {})".format(
            sec2str(arrival_stop_time.dts_arr - dep_secs),
            sec2str(dep_secs),
        )
    logger.info(msg)
