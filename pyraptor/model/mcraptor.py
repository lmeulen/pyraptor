"""McRAPTOR algorithm"""
from typing import List, Tuple, Dict
from copy import deepcopy

from loguru import logger

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import (
    Stop,
    Route,
    Bag,
    Label,
    Leg,
    Journey,
    pareto_set_labels,
)
from pyraptor.util import (
    sec2str,
    LARGE_NUMBER,
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
        bag_round_stop: Dict[int, Dict[Stop, Bag]] = {}
        for k in range(0, rounds + 1):
            bag_round_stop[k] = {}
            for p in self.timetable.stops:
                bag_round_stop[k][p] = Bag()

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
            logger.debug(f"Stops to evaluate count: {len(marked_stops)}")

            # Copy bag from previous round
            bag_round_stop[k] = deepcopy(bag_round_stop[k - 1])

            # Accumulate routes serving marked stops from previous round
            route_marked_stops = self.accumulate_routes(marked_stops)

            # Traverse each route
            bag_round_stop, marked_stops_trips = self.traverse_route(
                deepcopy(bag_round_stop), k, route_marked_stops
            )

            logger.debug(f"{len(marked_stops_trips)} reachable stops added")

            # Now add footpath transfers and update
            bag_round_stop, marked_stops_transfers = self.add_transfer_time(
                deepcopy(bag_round_stop), k, marked_stops_trips
            )

            logger.debug(f"{len(marked_stops_transfers)} transferable stops added")

            marked_stops = set(marked_stops_trips).union(marked_stops_transfers)
            logger.debug(f"{len(marked_stops)} stops to evaluate in next round")

        return bag_round_stop

    def accumulate_routes(self, marked_stops) -> List[Tuple[Route, Stop]]:
        """Accumulate routes serving marked stops from previous round, i.e. Q"""
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
    ) -> Tuple[Dict[int, Dict[int, Bag]], List[Stop]]:
        """
        Iterator through the stops reachable and add all new reachable stops
        by following all trips from the reached stations. Trips are only followed
        in the direction of travel and beyond already added points.

        :param bag_round_stop: Bag per round per stop
        :param k: current round
        :param route_marked_stops: list of marked (route, stop) for evaluation
        """
        logger.debug(f"Traverse routes for round {k}")

        new_marked_stops = []

        for (marked_route, marked_stop) in route_marked_stops:
            # Traversing through route from marked stop
            route_bag = Bag()

            # Get all stops after current stop within the current route
            marked_stop_index = marked_route.stop_index(marked_stop)
            remaining_stops_in_route = marked_route.stops[marked_stop_index:]

            for current_stop in remaining_stops_in_route:

                # Mark stop
                if current_stop != marked_stop and current_stop not in new_marked_stops:
                    new_marked_stops.append(current_stop)

                # Step 1: update earliest arrival times and criteria for each label L in route-bag
                for label in route_bag.labels:
                    if label.trip is None:
                        label.update(
                            earliest_arrival_time=LARGE_NUMBER,
                            fare_addition=LARGE_NUMBER,
                        )
                    else:
                        trip_stop_time = label.trip.get_stop(current_stop)
                        if trip_stop_time is not None:
                            # Take fare of from_stop in trip
                            from_fare = label.trip.get_fare(label.from_stop)
                            label.update(
                                earliest_arrival_time=trip_stop_time.dts_arr,
                                fare_addition=from_fare,
                            )
                        else:
                            label.update(
                                earliest_arrival_time=LARGE_NUMBER,
                                fare_addition=LARGE_NUMBER,
                            )

                # Step 2: merge bag_route into bag_round_stop and remove dominated labels
                bag_round_stop[k][current_stop].merge(deepcopy(route_bag))

                # Step 3: merge B_{k-1}(p) into B_r
                route_bag.merge(deepcopy(bag_round_stop[k - 1][current_stop]))

                # Assign trips to all newly added labels in route_bag
                for label in route_bag.labels:
                    earliest_trip = marked_route.earliest_trip(
                        label.earliest_arrival_time, current_stop
                    )
                    if earliest_trip is not None:
                        label.trip = earliest_trip
                        label.from_stop = current_stop

        return bag_round_stop, new_marked_stops

    def add_transfer_time(
        self,
        bag_round_stop: Dict[int, Dict[Stop, Bag]],
        k: int,
        marked_stops: List[Stop],
    ) -> Tuple:
        """Add transfers between platforms."""

        logger.debug("Add transfer times...")

        marked_stops_transfers = []

        # Add in transfers to other platforms
        for stop in marked_stops:
            other_station_stops = [st for st in stop.station.stops if st != stop]

            for other_stop in other_station_stops:
                # Create temp copy of B_k(p_i)
                temp_bag = deepcopy(bag_round_stop[k][stop])
                for label in temp_bag.labels:
                    # Add arrival time to each label
                    transfer_arrival_time = (
                        label.earliest_arrival_time
                        + self.get_transfer_time(
                            stop, other_stop, label.earliest_arrival_time, 0
                        )
                    )
                    # Find earliest trip at other stop
                    earliest_trip = self.timetable.trip_stop_times.get_earliest_trip(
                        other_stop, transfer_arrival_time
                    )
                    if earliest_trip is not None:
                        # Update label
                        label.update(
                            earliest_arrival_time=transfer_arrival_time,
                        )
                        label.trip = earliest_trip
                        label.from_stop = stop
                    else:
                        # We update the bag in the next step so we need to set earliest arrival time to INF
                        label.update(
                            earliest_arrival_time=LARGE_NUMBER,
                            fare_addition=LARGE_NUMBER,
                        )

                # Merg temp bag into B_k(p_j)
                bag_round_stop[k][other_stop].merge(temp_bag)

                # Mark stop
                if other_stop not in marked_stops_transfers:
                    marked_stops_transfers.append(other_stop)

        return bag_round_stop, marked_stops_transfers

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
    Find the stops of destinatination station that are reached by non-dominated labels.
    """

    # Find all labels to target_stops
    best_labels = [
        (stop, label) for stop in to_stops for label in last_round_bag[stop].labels
    ]

    # Pareto optimal labels
    pareto_optimal_labels = pareto_set_labels([label for (_, label) in best_labels])
    pareto_optimal_labels = [
        (stop, label) for (stop, label) in best_labels if label in pareto_optimal_labels
    ]

    # Label to leg, i.e. add to_stop
    legs = [
        Leg(
            label.from_stop,
            to_stop,
            label.trip,
            label.earliest_arrival_time,
            label.fare,
        )
        for (to_stop, label) in pareto_optimal_labels
    ]
    return legs


def reconstruct_journeys(
    from_stops: List[Stop],
    destination_legs: List[Leg],
    bag_round_stop: Dict[int, Dict[Stop, Bag]],
    k: int,
) -> List[Journey]:
    """
    Construct Journeys for destinations from bags by recursively
    looping from destination to origin.
    """

    # Create journeys with list of legs
    def loop(last_round_bags: Dict[Stop, Bag], all_journeys: List[Journey]):
        """Create journeys as list of Legs"""

        for jrny in all_journeys:
            current_leg = jrny[0]

            # End of journey
            if current_leg.trip is None or current_leg.from_stop in from_stops:
                yield jrny
                continue

            # Loop trough each new leg
            for new_label in last_round_bags[current_leg.from_stop].labels:
                new_leg = Leg(
                    new_label.from_stop,
                    current_leg.from_stop,
                    new_label.trip,
                    new_label.earliest_arrival_time,
                    new_label.fare,
                )
                # Only add if arrival time is earlier and fare is lower or equal
                if (
                    new_label.earliest_arrival_time <= current_leg.earliest_arrival_time
                    and new_label.fare <= current_leg.fare
                ):
                    new_jrny = deepcopy(jrny)
                    new_jrny.prepend_leg(new_leg)
                    for i in loop(last_round_bags, [new_jrny]):
                        yield i

    last_round_bags = bag_round_stop[k]
    journeys = [Journey(legs=[leg]) for leg in destination_legs]
    journeys = loop(last_round_bags, journeys)
    journeys = [
        Journey(
            legs=[
                leg
                for leg in jrny.legs
                if (leg.trip is not None)
                and (leg.from_stop.station != leg.to_stop.station)
            ]
        )
        for jrny in journeys
    ]

    return journeys


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
