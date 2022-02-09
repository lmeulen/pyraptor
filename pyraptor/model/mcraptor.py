"""McRAPTOR algorithm"""
from typing import List, Tuple, Dict
from copy import deepcopy

from pdb import set_trace

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
        logger.debug(f"Starting from Stop IDs: {str(from_stops)}")

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

            for stop_idx, current_stop in enumerate(remaining_stops_in_route):

                # Mark stop
                if current_stop != marked_stop and current_stop not in new_marked_stops:
                    new_marked_stops.append(current_stop)

                # Step 1: update earliest arrival times and criteria for each label L in route-bag
                for label in route_bag.labels_with_trip():
                    trip_stop_time = label.trip.get_stop(current_stop)
                    if trip_stop_time is not None:
                        # Take fare of previous stop in trip as fare is defined on start
                        previous_stop = remaining_stops_in_route[stop_idx - 1]
                        from_fare = label.trip.get_fare(previous_stop)

                        label.update(
                            earliest_arrival_time=trip_stop_time.dts_arr,
                            fare_addition=from_fare,
                        )
                    else:
                        # Make label unusable as current_stop is not in trip
                        label.set_infinite()

                # Step 2: merge bag_route into bag_round_stop and remove dominated labels
                # The label contains the trip with which one arrives at current stop with k legs
                # and we boarded the trip at from_stop.
                bag_round_stop[k][current_stop].merge(route_bag)

                # Step 3: merge B_{k-1}(p) into B_r
                route_bag.merge(bag_round_stop[k - 1][current_stop])
                # set_trace()

                # Assign trips to all newly added labels in route_bag
                # This is the trip on which we 'hop-on'
                for label in route_bag.labels:
                    earliest_trip = marked_route.earliest_trip(
                        label.earliest_arrival_time, current_stop
                    )
                    if earliest_trip is not None:  #  and label.trip != earliest_trip:
                        # Update label with earliest trip in route leaving from this station
                        label.trip = earliest_trip
                        label.from_stop = current_stop
                    else:
                        # Make label unusable as there is no trip leaving from this stop
                        label.set_infinite()

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
        # import pdb; pdb.set_trace()

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
                    # earliest_trip = self.timetable.trip_stop_times.get_earliest_trip(
                    #     other_stop, transfer_arrival_time
                    # )
                    # if earliest_trip is not None:
                    # Update label with new earliest arrival time at other_stop
                    label.update(
                        earliest_arrival_time=transfer_arrival_time,
                    )
                    label.from_stop = stop
                    # label.trip = earliest_trip  # Seems redundant
                    # else:
                    #     # We update the bag in the next step so we need to set earliest arrival time to INF
                    #     label.set_infinite()

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


def best_legs_to_destination_station(
    to_stops: List[Stop], last_round_bag: Dict[Stop, Bag]
) -> List[Leg]:
    """
    Find the last legs to destination station that are reached by non-dominated labels.
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
                jrny.remove_transfer_legs()
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
    journeys = [jrny for jrny in loop(last_round_bags, journeys)]

    return journeys
