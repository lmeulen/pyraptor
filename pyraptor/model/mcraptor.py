"""McRAPTOR algorithm"""
from typing import List, Tuple, Dict
from pprint import pprint
from copy import deepcopy
from pdb import set_trace

from loguru import logger

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop, Route, Bag, Label, Leg, pareto_set_labels
from pyraptor.util import (
    sec2str,
    TRANSFER_COST,
    TRANSFER_TRIP,
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
            bag_round_stop[0][from_stop].add(
                Label(dep_secs, 0, TRANSFER_TRIP, from_stop)
            )

        marked_stops = from_stops

        # Run rounds
        for k in range(1, rounds + 1):

            logger.info(f"Analyzing possibilities round {k}")

            # Get list of stops to evaluate in the process
            logger.debug("Stops to evaluate count: {}".format(len(marked_stops)))

            # Copy bag
            bag_round_stop[k] = deepcopy(bag_round_stop[k-1])
            
            # Accumulate routes serving marked stops from previous round
            route_marked_stops = self.accumulate_routes(marked_stops)

            # Traverse each route
            bag_round_stop, marked_stops_trips = self.traverse_route(
                deepcopy(bag_round_stop), k, route_marked_stops
            )

            # pprint(bag_round_stop)

            logger.debug(f"{len(marked_stops_trips)} reachable stops added")

            # Now add footpath transfers and update
            # bag_round_stop = self.add_transfer_time(deepcopy(bag_round_stop), k)

            # pprint(bag_round_stop)

            # logger.debug("{} transferable stops added".format(len(new_stops_transfer)))

            marked_stops = set(marked_stops_trips)  # .union(new_stops_transfer)
            logger.debug(f"{len(marked_stops)} stops to evaluate in next round")

        logger.info("Output bag:")
        pprint(bag_round_stop)

        return bag_round_stop

    def accumulate_routes(self, marked_stops) -> List[Tuple[Route, Stop]]:
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
        logger.debug(f"Traverse route for round {k}")

        new_marked_stops = []

        for route_index, (marked_route, marked_stop) in enumerate(route_marked_stops):

            logger.debug(
                f"Traversing {marked_route}, {marked_stop} ({route_index+1}/{len(route_marked_stops)})"
            )

            # Get all stops after current stop within the current route
            marked_stop_index = marked_route.stop_index(marked_stop)
            remaining_stops_in_route = marked_route.stops[marked_stop_index:]

            # Lege route bag aanmaken
            route_bag = Bag()

            # Initialize earliest trip to None
            for current_stop_index, current_stop in enumerate(remaining_stops_in_route):
                logger.debug(
                    f"Processing stop {current_stop} ({current_stop_index+1}/{len(remaining_stops_in_route)})"
                )
                # set_trace()

                if current_stop != marked_stop and current_stop not in new_marked_stops:
                    new_marked_stops.append(current_stop)
                
                # step 1: update earliest arrival times and other criteria of every label L from Br
                logger.debug("Step 1: Update labels")
                for label in route_bag.labels:
                    logger.debug(f"> Updating label {label}")
                    trip_stop_time = label.trip.get_stop(current_stop)
                    label.update(
                        earliest_arrival_time=trip_stop_time.dts_arr, fare_addition=trip_stop_time.fare
                    )
                    logger.debug(f"> to {label}")

                # step 2: merge bag_route into bag_round_stop and remove dominated labels
                logger.debug(f"Step 2: Merge bag_route into bag_round_stop of round {k}")
                bag_round_stop[k][current_stop].merge(deepcopy(route_bag))
                pprint(bag_round_stop[k])

                # step 3: merge B_{k-1}(p) into B_r
                logger.debug(
                    f"Step 3: Merge bag_round_stop of previous round {k-1} into route_bag"
                )
                route_bag.merge(deepcopy(bag_round_stop[k - 1][current_stop]))

                pprint(route_bag)

                # assign trips to all newly added labels
                for label in route_bag.labels:
                    logger.debug(f"> Processing {label}")
                    earliest_trip = marked_route.earliest_trip(
                        label.earliest_arrival_time, current_stop
                    )
                    if earliest_trip is not None:
                        label.trip = earliest_trip
                        label.from_stop = current_stop
                        logger.debug(f"> Updating to {label}")
                pprint(bag_round_stop[k - 1])
            pprint(bag_round_stop)

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


def best_stops_at_target_station(
    to_stops: List[Stop], last_round_bag: Dict[Stop, Bag]
) -> List[Leg]:
    """
    Find the stop IDs of target station that are reached by non-dominated labels.
    """
    # Find all labels to target_stops
    best_labels = [(stop, label) for stop in to_stops for label in last_round_bag[stop].labels]

    # Pareto optimal labels
    pareto_optimal_labels = pareto_set_labels([label for (_, label) in best_labels])
    pareto_optimal_labels = [(stop, label) for (stop, label) in best_labels if label in pareto_optimal_labels]

    # Label to leg, i.e. add to_stop
    legs = [
        Leg(label.from_stop, to_stop, label.trip, label.earliest_arrival_time, label.fare) 
        for (to_stop, label) in pareto_optimal_labels
    ]
    return legs


def reconstruct_journeys(
    destination_legs: List[Leg], bag_round_stop: Dict[int, Dict[Stop, Bag]], k:int
) -> List[List[Leg]]:
    """Construct journeys for destinations from values in bag."""

    # Create journeys with list of legs
    def loop(last_round_bags: Dict[Stop, Bag], all_journeys: List[List[Leg]]):
        """Create journeys as list of Legs"""
        for jrny in all_journeys:
            current_leg = jrny[-1]
            current_stop = current_leg.from_stop

            # End of journey
            if current_leg.trip is not None:
                yield jrny
                break

            # Loop trough each new leg
            for new_label in last_round_bags[current_stop].labels:
                new_leg = Leg(
                    new_label.from_stop,
                    current_stop,
                    new_label.trip,
                    new_label.earliest_arrival_time,
                    new_label.fare,
                )
                new_jrny = [jrny + [new_leg]]
                for i in loop(last_round_bags, new_jrny):
                    yield i

    import pdb; pdb.set_trace()

    last_round_bags = bag_round_stop[k]
    journeys = [[l] for l in destination_legs]
    journeys = loop(last_round_bags, journeys)
    journeys = [jrn[::-1] for jrn in journeys]  # reverse
    journeys = [[leg for leg in jrny if leg.trip is not None] for jrny in journeys]

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
