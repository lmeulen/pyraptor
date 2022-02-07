"""McRAPTOR algorithm"""
from typing import List, Tuple, Dict
from pprint import pprint
from copy import deepcopy

from loguru import logger

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop, Route, Bag, Label, Leg
from pyraptor.util import (
    sec2str,
    TRANSFER_COST,
)


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
            route_marked_stops = self.acculumate_routes(marked_stops)

            # Traverse each route
            bag_round_stop, marked_stops_trips = self.traverse_route(
                deepcopy(bag_round_stop), k, route_marked_stops, dep_secs
            )

            pprint(bag_round_stop)

            logger.debug("{} reachable stops added".format(len(marked_stops_trips)))

            # Now add footpath transfers and update
            # bag_round_stop = self.add_transfer_time(deepcopy(bag_round_stop), k)

            # pprint(bag_round_stop)

            # logger.debug("{} transferable stops added".format(len(new_stops_transfer)))

            marked_stops = set(marked_stops_trips)  # .union(new_stops_transfer)
            logger.debug("{} stops to evaluate in next round".format(len(marked_stops)))

        return bag_round_stop

    def acculumate_routes(self, marked_stops) -> List[Tuple[Route, Stop]]:
        """Accumulate routes serving marked stops from previous round"""
        route_marked_stops = {}  # i.e. Q
        for marked_stop in marked_stops:
            routes_serving_stop = self.timetable.routes.get_routes_of_stop(marked_stop)
            for route in routes_serving_stop:
                # Check if new_stop is before existing stop in Q
                current_stop_for_route = route_marked_stops.get(route, None)  # p'
                if (current_stop_for_route is None) or (
                    route.stop_index(current_stop_for_route)
                    > route.stop_index(marked_stop)
                ):
                    route_marked_stops[route] = marked_stop
        route_marked_stops = [(r, p) for r, p in route_marked_stops.items()]

        return route_marked_stops

    def traverse_route(
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

            # bepaal earliest trip? om label mee te updaten?
            earliest_arrival_marked_stop = bag_round_stop[k - 1][
                marked_stop
            ].earliest_arrival()  # plus transfer buffer?
            earliest_trip = marked_route.earliest_trip(
                earliest_arrival_marked_stop, marked_stop
            )

            for next_stop_index, current_stop in enumerate(remaining_stops_in_route):
                # step 1: update arrival times and other criteria of every label L from Br
                for label in route_bag.labels:
                    trip = self.timetable.trips[
                        label.trip_id
                    ]  # waarom op dezelfde trip door?
                    trip_stop_idx = current_stop_index + next_stop_index
                    trip_stop_time = self.timetable.trip_stop_times.set_idx[
                        (trip, trip_stop_idx)
                    ]  # key error?
                    label.update(
                        travel_time=trip_stop_time.dts_arr, fare=trip_stop_time.fare
                    )  # kan hier trip ook al bij?

                # step 2: merge bag_route into bag_round_stop and remove dominated labels
                bag_round_stop[k][current_stop].merge(route_bag)

                # step 3: merge B_{k-1}(p) into B_r
                route_bag.merge(bag_round_stop[k - 1][current_stop])

                # assign trips to all newly added labels
                for label in route_bag.labels:
                    label.trip_id = earliest_trip.id  # dubbel werk?

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
                # trip = timetable.trips.set_idx[leg.trip_id]
                new_leg = Leg(
                    new_label.previous_stop,
                    current_stop,
                    new_label.trip_id,  # TODO: Trip
                    new_label.travel_time,
                    new_label.fare,
                )
                new_jrny = [jrny + [new_leg]]
                for i in loop(best_bag, new_jrny):
                    yield i

    journeys = [[l] for l in destination_labels]
    journeys = loop(best_bag, journeys)
    journeys = [jrn[::-1] for jrn in journeys]  # reverse
    journeys = [[leg for leg in jrny if leg.trip_id != 0] for jrny in journeys]

    return journeys


def print_journeys(journeys: List[List[Leg]], dep_secs=None):
    """Print list of journeys"""
    for jrny in journeys:
        print_journey(jrny, dep_secs)


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
