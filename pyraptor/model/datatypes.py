"""Datatypes"""
from collections import defaultdict
from typing import List

import attr

from pyraptor.util import T6H


def same_type_and_id(first, second):
    """Same type and ID"""
    return type(first) is type(second) and first.id == second.id


@attr.s(repr=False, cmp=False)
class Stop:
    """Stop"""

    id = attr.ib(default=None)
    name = attr.ib(default=None)
    station = attr.ib(default=None)
    platform_code = attr.ib(default=None)
    index = attr.ib(default=None)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, stop):
        return same_type_and_id(self, stop)

    def __repr__(self):
        if self.id == self.name:
            return "<Stop {}>".format(self.id)
        return "<Stop {} [{}]>".format(self.name, self.id)


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

    def get_by_index(self, stop_index):
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
            return "<Station {}>".format(self.id)
        return "<Station {} [{}]>".format(self.name, self.id)

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
        if station.id in self.set_idx:
            station = self.set_idx[station.id]
        else:
            self.set_idx[station.id] = station
        return station

    def get(self, station: Station):
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

    trip = attr.ib(default=attr.NOTHING)
    stopidx = attr.ib(default=attr.NOTHING)
    stop = attr.ib(default=attr.NOTHING)
    dts_arr = attr.ib(default=attr.NOTHING)
    dts_dep = attr.ib(default=attr.NOTHING)

    def __hash__(self):
        return hash((self.trip, self.stopidx))

    def __repr__(self):
        return (
            "TripStopTime(trip_id={hint}{trip_id}, stopidx={0.stopidx},"
            " stop_id={0.stop.id}, dts_arr={0.dts_arr}, dts_dep={0.dts_dep})"
        ).format(
            self,
            trip_id=self.trip.id if self.trip else None,
            hint="{}:".format(self.trip.hint) if self.trip and self.trip.hint else "",
        )


class TripStopTimes:
    """Trip Stop Times"""

    def __init__(self):
        self.set_idx = dict()
        self.stop_trip_idx = defaultdict(list)

    def __repr__(self):
        return f"Trips(n_trips={len(self.set_idx)})"

    def __getitem__(self, trip_id):
        return self.set_idx[trip_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def add(self, trip_stop_time: TripStopTime):
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

    def get_trip_stop_times_for_stop(
        self, stop: Stop, dep_secs: int, forward: int = T6H
    ) -> List[TripStopTime]:
        """
        Takes a stop and departure time and get associated trip ids.
        The forward parameter limits the time frame starting at the departure time.
        Times are specified in seconds since midnight.

        :param stop_id: Stop
        :param dep_secs: Departure time
        :param forward: Period forward limitimg trips
        """
        trip_stop_times = self.stop_trip_idx[stop]
        in_window = [
            tst
            for tst in trip_stop_times
            if tst.dts_dep >= dep_secs and tst.dts_dep <= dep_secs + forward
        ]
        return in_window


@attr.s(repr=False, cmp=False)
class Trip:
    """Trip"""

    id = attr.ib(default=None)
    stop_times = attr.ib(default=attr.Factory(list))
    hint = attr.ib(default=None)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return "Trip(id={hint}:{0.id}, stop_times={stop_times}:{first_stop}-{last_stop})".format(
            self,
            stop_times=len(self.stop_times),
            first_stop=self.stop_times[0].stop.id,
            last_stop=self.stop_times[-1].stop.id,
            hint=self.hint,
        )

    def __getitem__(self, n):
        return self.stop_times[n]

    def __len__(self):
        return len(self.stop_times)

    def __iter__(self):
        return iter(self.stop_times)

    def add_stop_time(self, stop_time: TripStopTime):
        assert stop_time.dts_arr <= stop_time.dts_dep
        assert not self.stop_times or self.stop_times[-1].dts_dep <= stop_time.dts_arr
        self.stop_times.append(stop_time)

    def get_next_trip_stop_times(self, stop_idx: int):
        return [st for st in self.stop_times if st.stopidx > stop_idx]


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
        assert len(trip) >= 2, "must have 2 stop times"
        trip.id = self.last_id
        self.set_idx[trip.id] = trip
        self.last_id += 1
