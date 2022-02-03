"""RAPTOR algorithm"""
from __future__ import annotations
from typing import List, Tuple, Dict
from dataclasses import dataclass
from copy import deepcopy
from pprint import pprint

from loguru import logger

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop, Trip, Route
from pyraptor.util import (
    sec2str,
    T24H,
    TRANSFER_TRIP,
    TRANSFER_COST,
)


@dataclass
class Label:
    travel_time: int = T24H
    trip: Trip = None  # trip to take to obtain travel_time
    from_stop: Stop = None  # stop at which we hop-on trip with trip

    def update(self, travel_time=None, trip=None, from_stop=None):
        if travel_time is not None:
            self.travel_time = travel_time
        if trip is not None:
            self.trip = trip
        if travel_time is not None:
            self.from_stop = from_stop

    def is_dominating(self, other: Label):
        return self.travel_time <= other.travel_time

    def __repr__(self) -> str:
        return f"Label(travel_time={self.travel_time}, trip={self.trip}, from_stop={self.from_stop})"


@dataclass
class Leg:
    from_stop: Stop
    to_stop: Stop
    trip: Trip

    @property
    def dep(self):
        return [
            tst.dts_dep for tst in self.trip.stop_times if self.from_stop == tst.stop
        ][0]

    @property
    def arr(self):
        return [
            tst.dts_arr for tst in self.trip.stop_times if self.to_stop == tst.stop
        ][0]


class RaptorAlgorithm:
    """RAPTOR Algorithm"""

    def __init__(self, timetable: Timetable):
        self.timetable = timetable

    def run(self, from_stops, dep_secs, rounds) -> Dict[int, Dict[Stop, Label]]:
        """Run Round-Based Algorithm"""

        # Initialize empty bag of labels, i.e. B_k(p) = Label() for every k and p
        bag_round_stop: Dict[int, Dict[Stop, Label]] = {}
        for k in range(0, rounds + 1):
            bag_round_stop[k] = {}
            for p in self.timetable.stops:
                bag_round_stop[k][p] = Label()

        # Initialize lookup with start node taking 0 seconds to reach
        logger.debug("Starting from Stop IDs: {}".format(str(from_stops)))
        marked_stops = []
        for from_stop in from_stops:
            bag_round_stop[0][from_stop].update(dep_secs, None, None)
            marked_stops.append(from_stop)

        # Run rounds
        for k in range(1, rounds + 1):
            logger.info("Analyzing possibilities round {}".format(k))
            bag_round_stop[k] = deepcopy(bag_round_stop[k - 1])

            # Get list of stops to evaluate in the process
            logger.debug("Stops to evaluate count: {}".format(len(marked_stops)))

            # Get marked route stops
            route_marked_stops = self.accumulate_marked_routes(marked_stops)

            # Update time to stops calculated based on stops reachable
            bag_round_stop, marked_stops_trips = self.traverse_routes(
                bag_round_stop, k, route_marked_stops, dep_secs
            )
            logger.debug("{} reachable stops added".format(len(marked_stops_trips)))

            pprint(bag_round_stop)

            # Add footpath transfers and update
            bag_round_stop, marked_stops_transfers = self.add_transfer_time(
                bag_round_stop, k, marked_stops_trips
            )
            logger.debug(
                "{} transferable stops added".format(len(marked_stops_transfers))
            )

            pprint(bag_round_stop)

            marked_stops = set(marked_stops_trips).union(marked_stops_transfers)
            logger.debug("{} stops to evaluate in next round".format(len(marked_stops)))

        return bag_round_stop

    def accumulate_marked_routes(self, marked_stops):
        """Get marked route-stops, i.e. Q"""

        # Accumulate routes serving marked stops from previous round
        route_marked_stops = {}  # i.e. Q

        for marked_stop in marked_stops:
            routes_serving_stop = self.timetable.routes.get_routes_of_stop(marked_stop)
            for route in routes_serving_stop:
                # Check if new_stop is before existing stop in Q
                current_stop_for_route = route_marked_stops.get(route, None)  # i.e. p'
                if (current_stop_for_route is None) or (
                    route.stop_index(current_stop_for_route)
                    > route.stop_index(marked_stop)
                ):
                    route_marked_stops[route] = marked_stop
        route_marked_stops = [(r, p) for r, p in route_marked_stops.items()]

        return route_marked_stops

    def traverse_routes(
        self,
        bag_round_stop: Dict[int, Dict[Stop, Label]],
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

        bag_star = deepcopy(bag_round_stop[k])

        new_stops = []

        n_evaluations = 0
        n_improvements = 0

        for (marked_route, marked_stop) in route_marked_stops:

            logger.debug(f"Route {marked_route}, Stop {marked_stop}")

            # Current trip for this stop
            current_trip = bag_round_stop[k][marked_stop].trip

            # How long it took to get to the stop so far
            marked_label = bag_round_stop[k][marked_stop]
            time_sofar = marked_label.travel_time

            # Iterate over all stops after current stop within the current route
            current_stop_index = marked_route.stop_index(marked_stop)
            remaining_stops_in_route = marked_route.stops[current_stop_index:]
            for next_stop in remaining_stops_in_route:
                n_evaluations += 1

                previous_arrival_time = bag_round_stop[k - 1][next_stop].travel_time

                if current_trip is not None:
                    # Time to reach is diff from start time to arrival
                    arrival_stop_time = current_trip.get_arrival_at_stop(next_stop)
                    if arrival_stop_time is not None:
                        new_arrival_time = arrival_stop_time.dts_arr - dep_secs

                        if new_arrival_time < previous_arrival_time:
                            # Update arrival by trip
                            bag_round_stop[k][next_stop].update(
                                new_arrival_time, current_trip, marked_stop
                            )
                            n_improvements += 1
                            new_stops.append(next_stop)

                # Possibility to find a new / earlier trip
                if current_trip is None or new_arrival_time < previous_arrival_time:
                    earliest_trip = marked_route.earliest_trip(time_sofar, next_stop)
                    if earliest_trip is not None and current_trip != earliest_trip:
                        current_trip = earliest_trip

        logger.debug("- Evaluations    : {}".format(n_evaluations))
        logger.debug("- Improvements   : {}".format(n_improvements))

        return bag_round_stop, new_stops

    def add_transfer_time(
        self,
        bag_round_stop: Dict[int, Dict[Stop, Label]],
        k: int,
        marked_stops: List[Stop],
    ) -> Tuple:
        """
        Add transfers between platforms.

        :param bag_round_stop: Label per round per stop
        :param k: current round
        :param marked_stops: list of marked stops for evaluation
        """

        new_stops = []

        # Add in transfers to other platforms
        for stop in marked_stops:

            other_station_stops = [st for st in stop.station.stops if st != stop]

            time_sofar = bag_round_stop[k][stop].travel_time
            for arrive_stop in other_station_stops:
                arrive_time_adjusted = time_sofar + self.get_transfer_time(
                    stop, arrive_stop, time_sofar, 0
                )
                previous_arrival_value = bag_round_stop[k][arrive_stop].travel_time

                # Domination criteria
                if arrive_time_adjusted < previous_arrival_value:
                    bag_round_stop[k][arrive_stop].update(
                        arrive_time_adjusted,
                        TRANSFER_TRIP,
                        stop,
                    )
                    new_stops.append(arrive_stop)

        return bag_round_stop, new_stops

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


def final_destination(to_stops: List[Stop], bag: Dict[Stop, Label]) -> Stop:
    """
    Find the destination Stop with the shortest distance.
    Required in order to prevent adding travel time to the arrival time.
    """
    final_stop = 0
    distance = T24H
    for stop in to_stops:
        if bag[stop].travel_time < distance:
            distance = bag[stop].travel_time
            final_stop = stop
    return final_stop


def reconstruct_journey(destination: Stop, bag: Dict[Stop, Label]) -> List[Leg]:
    """Construct journey for destination from values in bag."""

    # Create journey with list of legs
    jrny = []
    current = destination
    while current is not None:
        from_stop = bag[current].from_stop
        trip = bag[current].trip
        leg = Leg(from_stop, current, trip)
        jrny.append(leg)
        current = from_stop
    jrny.reverse()

    # Filter transfer legs
    reached_journey = []
    for leg in jrny:
        if leg.trip is not None:
            reached_journey.append(leg)

    return reached_journey


def print_journey(journey: List[Leg], dep_secs=None):
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

    # Departure time of first leg and arrival time of last leg
    depart_stop_time = journey[0].dep
    arrival_stop_time = journey[-1].arr

    msg = "Duration : {}".format(sec2str(arrival_stop_time - depart_stop_time))
    if dep_secs:
        msg += " ({} from request time {})".format(
            sec2str(arrival_stop_time - dep_secs),
            sec2str(dep_secs),
        )
    logger.info(msg)


def is_dominated(original_journey: List[Leg], new_journey: List[Leg]) -> bool:
    """Check if new journey is dominated by another journey"""
    # First journey
    if not original_journey:
        return False

    # No improvement
    if original_journey == new_journey:
        return True

    def depart(jrny: List[Leg]) -> int:
        depart_leg = jrny[0] if jrny[0].trip is not None else jrny[1]
        return depart_leg.dep

    def arrival(jrny: List[Leg]) -> int:
        return jrny[-1].arr

    original_depart = depart(original_journey)
    new_depart = depart(new_journey)

    original_arrival = arrival(original_journey)
    new_arrival = arrival(new_journey)

    # Is dominated
    return (
        True
        if original_depart > new_depart and original_arrival < new_arrival
        else False
    )
