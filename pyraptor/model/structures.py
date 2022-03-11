"""Datatypes"""
from __future__ import annotations

from collections import defaultdict
from operator import attrgetter
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from copy import copy

import attr
import numpy as np
from loguru import logger

from pyraptor.util import sec2str


def same_type_and_id(first, second):
    """Same type and ID"""
    return type(first) is type(second) and first.id == second.id


@dataclass
class Timetable:
    """Timetable data"""

    stations: Stations = None
    stops: Stops = None
    trips: Trips = None
    trip_stop_times: TripStopTimes = None
    routes: Routes = None
    transfers: Transfers = None

    def counts(self) -> None:
        """Print timetable counts"""
        logger.debug("Counts:")
        logger.debug("Stations   : {}", len(self.stations))
        logger.debug("Routes     : {}", len(self.routes))
        logger.debug("Trips      : {}", len(self.trips))
        logger.debug("Stops      : {}", len(self.stops))
        logger.debug("Stop Times : {}", len(self.trip_stop_times))
        logger.debug("Transfers  : {}", len(self.transfers))


@attr.s(repr=False, cmp=False)
class Stop:
    """Stop"""

    id = attr.ib(default=None)
    name = attr.ib(default=None)
    station: Station = attr.ib(default=None)
    platform_code = attr.ib(default=None)
    index = attr.ib(default=None)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, stop):
        return same_type_and_id(self, stop)

    def __repr__(self):
        if self.id == self.name:
            return f"Stop({self.id})"
        return f"Stop({self.name} [{self.id}])"


class Stops:
    """Stops"""

    def __init__(self):
        self.set_idx = dict()
        self.set_index = dict()
        self.last_index = 1

    def __repr__(self):
        return f"Stops(n_stops={len(self.set_idx)})"

    def __getitem__(self, stop_id):
        return self.set_idx[stop_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def get(self, stop_id):
        """Get stop"""
        if stop_id not in self.set_idx:
            raise ValueError(f"Stop ID {stop_id} not present in Stops")
        stop = self.set_idx[stop_id]
        return stop

    def get_by_index(self, stop_index) -> Stop:
        """Get stop by index"""
        return self.set_index[stop_index]

    def add(self, stop):
        """Add stop"""
        if stop.id in self.set_idx:
            stop = self.set_idx[stop.id]
        else:
            stop.index = self.last_index
            self.set_idx[stop.id] = stop
            self.set_index[stop.index] = stop
            self.last_index += 1
        return stop


@attr.s(repr=False, cmp=False)
class Station:
    """Stop dataclass"""

    id = attr.ib(default=None)
    name = attr.ib(default=None)
    stops = attr.ib(default=attr.Factory(list))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, stop):
        return same_type_and_id(self, stop)

    def __repr__(self):
        if self.id == self.name:
            return "Station({})".format(self.id)
        return "Station({} [{}])>".format(self.name, self.id)

    def add_stop(self, stop: Stop):
        self.stops.append(stop)


class Stations:
    """Stations"""

    def __init__(self):
        self.set_idx = dict()

    def __repr__(self):
        return f"<Stations(n_stations={len(self.set_idx)})>"

    def __getitem__(self, station_id):
        return self.set_idx[station_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, station: Station):
        """Add station"""
        if station.id in self.set_idx:
            station = self.set_idx[station.id]
        else:
            self.set_idx[station.id] = station
        return station

    def get(self, station: Station):
        """Get station"""
        if isinstance(station, Station):
            station = station.id
        if station not in self.set_idx:
            return None
        return self.set_idx[station]

    def get_stops(self, station_name):
        """Get all stop ids from station, i.e. platform stop ids belonging to station"""
        return self.set_idx[station_name].stops


@attr.s(repr=False)
class TripStopTime:
    """Trip Stop"""

    trip: Trip = attr.ib(default=attr.NOTHING)
    stopidx = attr.ib(default=attr.NOTHING)
    stop = attr.ib(default=attr.NOTHING)
    dts_arr = attr.ib(default=attr.NOTHING)
    dts_dep = attr.ib(default=attr.NOTHING)
    fare = attr.ib(default=0)

    def __hash__(self):
        return hash((self.trip, self.stopidx))

    def __repr__(self):
        return (
            "TripStopTime(trip_id={hint}{trip_id}, stopidx={0.stopidx},"
            " stop_id={0.stop.id}, dts_arr={0.dts_arr}, dts_dep={0.dts_dep}, fare={0.fare})"
        ).format(
            self,
            trip_id=self.trip.id if self.trip else None,
            hint="{}:".format(self.trip.hint) if self.trip and self.trip.hint else "",
        )


class TripStopTimes:
    """Trip Stop Times"""

    def __init__(self):
        self.set_idx: Dict[Tuple[Trip, int], TripStopTime] = dict()
        self.stop_trip_idx: Dict[Stop, List[TripStopTime]] = defaultdict(list)

    def __repr__(self):
        return f"Trips(n_trips={len(self.set_idx)})"

    def __getitem__(self, trip_id):
        return self.set_idx[trip_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, trip_stop_time: TripStopTime):
        """Add trip stop time"""
        self.set_idx[(trip_stop_time.trip, trip_stop_time.stopidx)] = trip_stop_time
        self.stop_trip_idx[trip_stop_time.stop].append(trip_stop_time)

    def get_trip_stop_times_in_range(self, stops, dep_secs_min, dep_secs_max):
        """Returns all trip stop times with departure time within range"""
        in_window = [
            tst
            for tst in self
            if tst.dts_dep >= dep_secs_min
            and tst.dts_dep <= dep_secs_max
            and tst.stop in stops
        ]
        return in_window

    def get_earliest_trip(self, stop: Stop, dep_secs: int) -> Trip:
        """Earliest trip"""
        trip_stop_times = self.stop_trip_idx[stop]
        in_window = [tst for tst in trip_stop_times if tst.dts_dep >= dep_secs]
        return in_window[0].trip if len(in_window) > 0 else None

    def get_earliest_trip_stop_time(self, stop: Stop, dep_secs: int) -> TripStopTime:
        """Earliest trip stop time"""
        trip_stop_times = self.stop_trip_idx[stop]
        in_window = [tst for tst in trip_stop_times if tst.dts_dep >= dep_secs]
        return in_window[0] if len(in_window) > 0 else None


@attr.s(repr=False, cmp=False)
class Trip:
    """Trip"""

    id = attr.ib(default=None)
    stop_times = attr.ib(default=attr.Factory(list))
    hint = attr.ib(default=None)
    long_name = attr.ib(default=None)  # e.g., Sprinter

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return "Trip(hint={hint}, stop_times={stop_times})".format(
            hint=self.hint if self.hint is not None else self.id,
            stop_times=len(self.stop_times),
        )

    def __getitem__(self, n):
        return self.stop_times[n]

    def __len__(self):
        return len(self.stop_times)

    def __iter__(self):
        return iter(self.stop_times)

    def trip_stop_ids(self):
        """Tuple of all stop ids in trip"""
        return tuple([s.stop.id for s in self.stop_times])

    def add_stop_time(self, stop_time: TripStopTime):
        """Add stop time"""
        assert stop_time.dts_arr <= stop_time.dts_dep
        assert not self.stop_times or self.stop_times[-1].dts_dep <= stop_time.dts_arr
        self.stop_times.append(stop_time)

    def get_stop(self, stop: Stop) -> TripStopTime:
        """Get stop"""
        stop_times = [st for st in self.stop_times if st.stop == stop]
        return stop_times[0] if len(stop_times) > 0 else None

    def get_fare(self, depart_stop: Stop) -> int:
        """Get fare from depart_stop"""
        stop_time = self.get_stop(depart_stop)
        return 0 if stop_time is None else stop_time.fare


class Trips:
    """Trips"""

    def __init__(self):
        self.set_idx = dict()
        self.last_id = 1

    def __repr__(self):
        return f"Trips(n_trips={len(self.set_idx)})"

    def __getitem__(self, trip_id):
        return self.set_idx[trip_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, trip):
        """Add trip"""
        assert len(trip) >= 2, "must have 2 stop times"
        trip.id = self.last_id
        self.set_idx[trip.id] = trip
        self.last_id += 1


@attr.s(repr=False, cmp=False)
class Route:
    """Route"""

    id = attr.ib(default=None)
    trips = attr.ib(default=attr.Factory(list))
    stops = attr.ib(default=attr.Factory(list))
    stop_order = attr.ib(default=attr.Factory(dict))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return "Route(id={0.id}, trips={trips})".format(
            self,
            trips=len(self.trips),
        )

    def __getitem__(self, n):
        return self.trips[n]

    def __len__(self):
        return len(self.trips)

    def __iter__(self):
        return iter(self.trips)

    def add_trip(self, trip: Trip) -> None:
        """Add trip"""
        self.trips.append(trip)

    def add_stop(self, stop: Stop) -> None:
        """Add stop"""
        self.stops.append(stop)
        # (re)make dict to save the order of the stops in the route
        self.stop_order = {stop: index for index, stop in enumerate(self.stops)}

    def stop_index(self, stop: Stop):
        """Stop index"""
        return self.stop_order[stop]

    def earliest_trip(self, dts_arr: int, stop: Stop) -> Trip:
        """Returns earliest trip after time dts (sec)"""
        stop_idx = self.stop_index(stop)
        trip_stop_times = [trip.stop_times[stop_idx] for trip in self.trips]
        trip_stop_times = [tst for tst in trip_stop_times if tst.dts_dep >= dts_arr]
        trip_stop_times = sorted(trip_stop_times, key=attrgetter("dts_dep"))
        return trip_stop_times[0].trip if len(trip_stop_times) > 0 else None

    def earliest_trip_stop_time(self, dts_arr: int, stop: Stop) -> TripStopTime:
        """Returns earliest trip stop time after time dts (sec)"""
        stop_idx = self.stop_index(stop)
        trip_stop_times = [trip.stop_times[stop_idx] for trip in self.trips]
        trip_stop_times = [tst for tst in trip_stop_times if tst.dts_dep >= dts_arr]
        trip_stop_times = sorted(trip_stop_times, key=attrgetter("dts_dep"))
        return trip_stop_times[0] if len(trip_stop_times) > 0 else None


class Routes:
    """Routes"""

    def __init__(self):
        self.set_idx = dict()
        self.set_stops_idx = dict()
        self.stop_to_routes = defaultdict(list)  # {Stop: [Route]}
        self.last_id = 1

    def __repr__(self):
        return f"Routes(n_routes={len(self.set_idx)})"

    def __getitem__(self, route_id):
        return self.set_idx[route_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, trip: Trip):
        """Add trip to route. Make route if not exists."""
        trip_stop_ids = trip.trip_stop_ids()

        if trip_stop_ids in self.set_stops_idx:
            # Route already exists
            route = self.set_stops_idx[trip_stop_ids]
        else:
            # Route does not exist yet, make new route
            route = Route()
            route.id = self.last_id

            # Maintain stops in route and list of routes per stop
            for trip_stop_time in trip:
                route.add_stop(trip_stop_time.stop)
                self.stop_to_routes[trip_stop_time.stop].append(route)

            # Efficient lookups
            self.set_stops_idx[trip_stop_ids] = route
            self.set_idx[route.id] = route
            self.last_id += 1

        # Add trip
        route.add_trip(trip)
        return route

    def get_routes_of_stop(self, stop: Stop):
        """Get routes of stop"""
        return self.stop_to_routes[stop]


@attr.s(repr=False, cmp=False)
class Transfer:
    """Transfer"""

    id = attr.ib(default=None)
    from_stop = attr.ib(default=None)
    to_stop = attr.ib(default=None)
    layovertime = attr.ib(default=300)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return f"Transfer(from_stop={self.from_stop}, to_stop={self.to_stop}, layovertime={self.layovertime})"


class Transfers:
    """Transfers"""

    def __init__(self):
        self.set_idx = dict()
        self.stop_to_stop_idx = dict()
        self.last_id = 1

    def __repr__(self):
        return f"Transfers(n_transfers={len(self.set_idx)})"

    def __getitem__(self, transfer_id):
        return self.set_idx[transfer_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, transfer: Transfer):
        """Add trip"""
        transfer.id = self.last_id
        self.set_idx[transfer.id] = transfer
        self.stop_to_stop_idx[(transfer.from_stop, transfer.to_stop)] = transfer
        self.last_id += 1


@dataclass
class Leg:
    """Leg"""

    from_stop: Stop
    to_stop: Stop
    trip: Trip
    earliest_arrival_time: int
    fare: int = 0
    n_trips: int = 0

    @property
    def criteria(self):
        """Criteria"""
        return [self.earliest_arrival_time, self.fare, self.n_trips]

    @property
    def dep(self):
        """Departure time"""
        return [
            tst.dts_dep for tst in self.trip.stop_times if self.from_stop == tst.stop
        ][0]

    @property
    def arr(self):
        """Arrival time"""
        return [
            tst.dts_arr for tst in self.trip.stop_times if self.to_stop == tst.stop
        ][0]

    def is_transfer(self):
        """Is transfer leg"""
        return self.from_stop.station == self.to_stop.station

    def is_compatible_before(self, other_leg: Leg):
        """
        Check if Leg is allowed before another leg. That is,
        - It is possible to go from current leg to other leg concerning arrival time
        - Number of trips of current leg differs by > 1, i.e. a differen trip,
          or >= 0 when the other_leg is a transfer_leg
        - The accumulated value of a criteria of current leg is larger or equal to the accumulated value of
          the other leg (current leg is instance of this class)
        """
        arrival_time_compatible = (
            other_leg.earliest_arrival_time >= self.earliest_arrival_time
        )
        n_trips_compatible = (
            other_leg.n_trips >= self.n_trips
            if other_leg.is_transfer()
            else other_leg.n_trips > self.n_trips
        )
        criteria_compatible = np.all(
            np.array([c for c in other_leg.criteria])
            >= np.array([c for c in self.criteria])
        )

        return all([arrival_time_compatible, n_trips_compatible, criteria_compatible])

    def to_dict(self, leg_index: int = None) -> Dict:
        """Leg to readable dictionary"""
        return dict(
            trip_leg_idx=leg_index,
            departure_time=self.dep,
            arrival_time=self.arr,
            from_stop=self.from_stop.name,
            from_station=self.from_stop.station.name,
            to_stop=self.to_stop.name,
            to_station=self.to_stop.station.name,
            trip_hint=self.trip.hint,
            trip_long_name=self.trip.long_name,
            from_platform_code=self.from_stop.platform_code,
            to_platform_code=self.to_stop.platform_code,
            fare=self.fare,
        )


@dataclass(frozen=True)
class Label:
    """Label"""

    earliest_arrival_time: int
    fare: int  # total fare
    trip: Trip  # trip to take to obtain travel_time and fare
    from_stop: Stop  # stop to hop-on the trip
    n_trips: int = 0
    infinite: bool = False

    @property
    def criteria(self):
        """Criteria"""
        return [self.earliest_arrival_time, self.fare, self.n_trips]

    def update(self, earliest_arrival_time=None, fare_addition=None, from_stop=None):
        """Update earliest arrival time and add fare_addition to fare"""
        return copy(
            Label(
                earliest_arrival_time=earliest_arrival_time
                if earliest_arrival_time is not None
                else self.earliest_arrival_time,
                fare=self.fare + fare_addition
                if fare_addition is not None
                else self.fare,
                trip=self.trip,
                from_stop=from_stop if from_stop is not None else self.from_stop,
                n_trips=self.n_trips,
                infinite=self.infinite,
            )
        )

    def update_trip(self, trip: Trip, current_stop: Stop):
        """Update trip"""
        return copy(
            Label(
                earliest_arrival_time=self.earliest_arrival_time,
                fare=self.fare,
                trip=trip,
                from_stop=current_stop if self.trip != trip else self.from_stop,
                n_trips=self.n_trips + 1 if self.trip != trip else self.n_trips,
                infinite=self.infinite,
            )
        )


@dataclass(frozen=True)
class Bag:
    """
    Bag B(k,p) or route bag B_r
    """

    labels: List[Label] = field(default_factory=list)
    update: bool = False

    def __len__(self):
        return len(self.labels)

    def __repr__(self):
        return f"Bag({self.labels}, update={self.update})"

    def add(self, label: Label):
        """Add"""
        self.labels.append(label)

    def merge(self, other_bag: Bag) -> Bag:
        """Merge other bag in bag and return true if bag is updated"""
        pareto_labels = self.labels + other_bag.labels
        if len(pareto_labels) == 0:
            return Bag(labels=[], update=False)
        pareto_labels = pareto_set(pareto_labels)
        bag_update = True if pareto_labels != self.labels else False
        return Bag(labels=pareto_labels, update=bag_update)

    def labels_with_trip(self):
        """All labels with trips, i.e. all labels that are reachable with a trip with given criterion"""
        return [l for l in self.labels if l.trip is not None]

    def earliest_arrival(self) -> int:
        """Earliest arrival"""
        return min([self.labels[i].earliest_arrival_time for i in range(len(self))])


@dataclass(frozen=True)
class Journey:
    """
    Journey from origin to destination specified as Legs
    """

    legs: List[Leg] = field(default_factory=list)

    @property
    def criteria(self):
        """Criteria"""
        return [self.travel_time(), self.fare(), self.number_of_trips()]

    def __len__(self):
        return len(self.legs)

    def __repr__(self):
        return f"Journey(n_legs={len(self.legs)})"

    def __getitem__(self, index):
        return self.legs[index]

    def __iter__(self):
        return iter(self.legs)

    def __lt__(self, other):
        return self.dep() < other.dep()

    def number_of_trips(self):
        """Return number of distinct trips"""
        trips = set([l.trip for l in self.legs])
        return len(trips)

    def prepend_leg(self, leg: Leg) -> Journey:
        """Add leg to journey"""
        legs = self.legs
        legs.insert(0, leg)
        jrny = Journey(legs=legs)
        return jrny

    def remove_transfer_legs(self) -> Journey:
        """Remove all transfer legs"""
        legs = [
            leg
            for leg in self.legs
            if (leg.trip is not None) and (leg.from_stop.station != leg.to_stop.station)
        ]
        jrny = Journey(legs=legs)
        return jrny

    def is_valid(self) -> bool:
        """Is valid journey"""
        for index in range(len(self.legs) - 1):
            if self.legs[index].arr > self.legs[index + 1].dep:
                return False
        return True

    def from_stop(self) -> Stop:
        """Origin stop of Journey"""
        return self.legs[0].from_stop

    def to_stop(self) -> Stop:
        """Destination stop of Journey"""
        return self.legs[-1].to_stop

    def fare(self) -> float:
        """Total fare of Journey"""
        return self.legs[-1].fare

    def dep(self) -> int:
        """Departure time"""
        return self.legs[0].dep

    def arr(self) -> int:
        """Arrival time"""
        return self.legs[-1].arr

    def travel_time(self) -> int:
        """Travel time in seconds"""
        return self.arr() - self.dep()

    def dominates(self, jrny: Journey):
        """Dominates other Journey"""
        return (
            True
            if (
                (self.dep() >= jrny.dep())
                and (self.arr() <= jrny.arr())
                and (self.fare() <= jrny.fare())
                and (self.number_of_trips() <= jrny.number_of_trips())
            )
            and (self != jrny)
            else False
        )

    def print(self, dep_secs=None):
        """Print the given journey to logger info"""

        logger.info("Journey:")

        if len(self) == 0:
            logger.info("No journey available")
            return

        # Print all legs in journey
        for leg in self:
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

        logger.info(f"Fare: €{self.fare()}")

        msg = f"Duration: {sec2str(self.travel_time())}"
        if dep_secs:
            msg += " ({} from request time {})".format(
                sec2str(self.arr() - dep_secs),
                sec2str(dep_secs),
            )
        logger.info(msg)
        logger.info("")

    def to_list(self) -> List[Dict]:
        """Convert journey to list of legs as dict"""
        return [leg.to_dict(leg_index=idx) for idx, leg in enumerate(self.legs)]


def pareto_set(labels: List[Label], keep_equal=False):
    """
    Find the pareto-efficient points
    :param labels: list with labels
    :keep_equal return also labels with equal criteria
    :return: list with pairwise non-dominating labels
    """

    is_efficient = np.ones(len(labels), dtype=bool)
    labels_criteria = np.array([label.criteria for label in labels])
    for i, label in enumerate(labels_criteria):
        if is_efficient[i]:
            # Keep any point with a lower cost
            if keep_equal:
                # keep point with all labels equal or one lower
                is_efficient[is_efficient] = np.any(
                    labels_criteria[is_efficient] < label, axis=1
                ) + np.all(labels_criteria[is_efficient] == label, axis=1)
            else:
                is_efficient[is_efficient] = np.any(
                    labels_criteria[is_efficient] < label, axis=1
                )

            is_efficient[i] = True  # And keep self

    return [copy(label) for i, label in enumerate(labels) if is_efficient[i]]
