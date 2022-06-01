"""Datatypes"""
from __future__ import annotations

from itertools import compress
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


def same_type_and_id2(first, second):
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
    """Stop

    A store of id, name, station, platform_code identifiers for PLATFORMS

    We shouldn't have an occupancy attribute per stop.
    Instead, we should perform an occupancy lookup where necessary using a custom function to which we pass:
    stop_time: TripStopTime,
    station: TBD (from stop: Stop)
    platform_code: TBD (from stop: Stop)
    """

    id = attr.ib(default=None) # EXAMPLE - '2427778'
    name = attr.ib(default=None) # EXAMPLE - 'Rotterdam Centraal-9'
    station: Station = attr.ib(default=None) # EXAMPLE - Station(Rotterdam Centraal)
    ### I want to see how this is handled:
    platform_code = attr.ib(default=None) # EXAMPLE - '9'
    index = attr.ib(default=None) # EXAMPLE - 41

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, stop):
        return type(self) is type(stop) and self.id == stop.id

    def __repr__(self):
        if self.id == self.name:
            return f"Stop({self.id})"
        return f"Stop({self.name} [{self.id}])"


class Stops:
    """Stops
    
    A collection (dictionary) of Stop class objects."""

    def __init__(self):
        self.set_idx = dict() # EXAMPLE - set_idx: {'2324635': Stop(Vlissingen-3 [2324635]), '2422053': Stop(Dordrecht-2 [2422053]), '2324687': Stop(Wijhe-2 [2324687]), ... }
        self.set_index = dict() # EXAMPLE - set_index: {1: Stop(Vlissingen-3 [2324635]), 2: Stop(Dordrecht-2 [2422053]), 3: Stop(Wijhe-2 [2324687]), ... }
        self.last_index = 1

    def __repr__(self):
        return f"Stops(n_stops={len(self.set_idx)})"

    def __getitem__(self, stop_id):
        """Get stop by stip_id
        
        EXAMPLE
        Args:
            - stop_id='2427778'
        
        Returns:
            - Stop(Rotterdam Centraal-9 [2427778])
        """
        return self.set_idx[stop_id]

    def __len__(self):
        return len(self.set_idx)

    def __iter__(self):
        return iter(self.set_idx.values())

    def get(self, stop_id):
        """Get stop by stop_id
        
        EXAMPLE
        Args:
            - stop_id='2427778'
        
        Returns:
            - Stop(Rotterdam Centraal-9 [2427778])
        """
        if stop_id not in self.set_idx:
            raise ValueError(f"Stop ID {stop_id} not present in Stops")
        stop = self.set_idx[stop_id]
        return stop

    def get_by_index(self, stop_index) -> Stop:
        """Get stop by index
        
        EXAMPLE
        Args:
            - stop_index=700
        
        Returns:
            - Stop(Lelystad Centrum-1 [2422110])
        """
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
    """Stop dataclass - a collection (list) of Stops class objects"""

    id = attr.ib(default=None) # EXAMPLE - 'Rotterdam Centraal'
    name = attr.ib(default=None) # EXAMPLE - 'Rotterdam Centraal'
    stops = attr.ib(default=attr.Factory(list)) # EXAMPLE - [Stop(Rotterdam Centraal-9 [2427778]), Stop(Rotterdam Centraal-14 [2427770]), Stop(Rotterdam Centraal-16 [2422141]), Stop(Rotterdam Centraal-2 [2427775]), Stop(Rotterdam Centraal-15 [2422140]), Stop(Rotterdam Centraal-13 [2427769]), Stop(Rotterdam Centraal-12 [2427768]), Stop(Rotterdam Centraal-6 [2324348]), Stop(Rotterdam Centraal-11 [2427767]), Stop(Rotterdam Centraal-7 [2427776]), Stop(Rotterdam Centraal-8 [2427777]), Stop(Rotterdam Centraal-3 [2324346]), Stop(Rotterdam Centraal-4 [2324347])]

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
    """Stations - a collection (Dict[common_name: str, station: Station]) of Station instances"""

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

    # def get(self, station: Station):
    def get(self, station: str):
        """Get station
        
        EXAMPLE
        Args:
            -   station='Rotterdam Centraal'
            
        Returns:
            -   Station(Rotterdam Centraal)
        """
        if isinstance(station, Station):
            station = station.id
        if station not in self.set_idx:
            return None
        return self.set_idx[station]

    def get_stops(self, station_name):
        """Get all stop ids from station, i.e. platform stop ids belonging to station
        
        EXAMPLE
        Args:
            -   station_name='Rotterdam Centraal'

        Returns:
            -   [Stop(Rotterdam Centraal-9 [2427778]), Stop(Rotterdam Centraal-14 [2427770]), Stop(Rotterdam Centraal-16 [2422141]), Stop(Rotterdam Centraal-2 [2427775]), Stop(Rotterdam Centraal-15 [2422140]), Stop(Rotterdam Centraal-13 [2427769]), Stop(Rotterdam Centraal-12 [2427768]), Stop(Rotterdam Centraal-6 [2324348]), Stop(Rotterdam Centraal-11 [2427767]), Stop(Rotterdam Centraal-7 [2427776]), Stop(Rotterdam Centraal-8 [2427777]), Stop(Rotterdam Centraal-3 [2324346]), Stop(Rotterdam Centraal-4 [2324347])]
        """
        return self.set_idx[station_name].stops


@attr.s(repr=False)
class TripStopTime:
    """Trip Stop
    
    A store of trip, stopidx, stop, arrival, departure annd fare attributes for a trip stop
    
    COULD INCLUDE OCCUPANCY HERE"""

    trip: Trip = attr.ib(default=attr.NOTHING) # EXAMPLE: Trip(hint=1178, stop_times=7)
    stopidx = attr.ib(default=attr.NOTHING) # EXAMPLE: 3
    stop = attr.ib(default=attr.NOTHING) # EXAMPLE: Stop(Rotterdam Centraal-9 [2427778])
    dts_arr = attr.ib(default=attr.NOTHING) # EXAMPLE: 81960
    dts_dep = attr.ib(default=attr.NOTHING) # EXAMPLE: 82080
    fare = attr.ib(default=0.0) # EXAMPLE: 0

    # def __init__(self):
    #     self.__class__.__hash__ = TripStopTime.__hash__  # <----- SOLUTION

    def __hash__(self):
        return hash((self.trip, self.stopidx))

    def hash(self):
        # print((self.trip, self.stopidx))
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
    """Trip Stop Times
    
    A collection (dict) of TripStopTime objects - used for indexing/finding trips in time range(s)"""

    def __init__(self):
        self.set_idx: Dict[Tuple[Trip, int], TripStopTime] = dict()
        self.stop_trip_idx: Dict[Stop, List[TripStopTime]] = defaultdict(list)

    def __repr__(self):
        return f"TripStoptimes(n_tripstoptimes={len(self.set_idx)})"

    ### DOESN'T WORK
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
        """Returns all trip stop times with departure time within range

        EXAMPLE
        Args:
            -   stops=timetable.stations.get_stops('Rotterdam Centraal')
            -   dep_secs_min=str2sec('10:00:00')
            -   dep_secs_max=str2sec('10:04:00')

        Returns:
            -   [TripStopTime(trip_id=4031:545, stopidx=22, stop_id=2422141, dts_arr=36240, dts_dep=36240, fare=0), TripStopTime(trip_id=3237:2088, stopidx=0, stop_id=2427778, dts_arr=36060, dts_dep=36060, fare=0)]
        """
        in_window = [
            tst # TripStop/time
            for tst in self
            if tst.dts_dep >= dep_secs_min
            and tst.dts_dep <= dep_secs_max
            and tst.stop in stops
        ]
        return in_window

    def get_earliest_trip(self, stop: Stop, dep_secs: int) -> Trip:
        """Earliest trip
        
        EXAMPLE
        Args:
            -   stop=timetable.stations.get_stops('Rotterdam Centraal')[0]
            -   dep_secs=str2sec('10:00')
        
        Returns:
            -   Trip(hint=1178, stop_times=7)
        """
        trip_stop_times = self.stop_trip_idx[stop]
        in_window = [tst for tst in trip_stop_times if tst.dts_dep >= dep_secs]
        return in_window[0].trip if len(in_window) > 0 else None

    def get_earliest_trip_stop_time(self, stop: Stop, dep_secs: int) -> TripStopTime:
        """Earliest trip stop time
        
        EXAMPLE
        Args:
            -   stop=timetable.stations.get_stops('Rotterdam Centraal')[0]
            -   dep_secs=str2sec('10:00')
        
        Returns:
            -   TripStopTime(trip_id=1178:50, stopidx=3, stop_id=2427778, dts_arr=81960, dts_dep=82080, fare=0)
        """
        trip_stop_times = self.stop_trip_idx[stop]
        in_window = [tst for tst in trip_stop_times if tst.dts_dep >= dep_secs]
        return in_window[0] if len(in_window) > 0 else None


@attr.s(repr=False, cmp=False)
class Trip:
    """Trip
    
    Details trip id, stop_times and index for a trip"""

    id = attr.ib(default=None) # EXAMPLE - 50
    stop_times = attr.ib(default=attr.Factory(list)) # EXAMPLE - [TripStopTime(trip_id=1178:50, stopidx=0, stop_id=2323599, dts_arr=78240, dts_dep=78240, fare=0), TripStopTime(trip_id=1178:50, stopidx=1, stop_id=2324474, dts_arr=79500, dts_dep=79740, fare=0), ... ]
    stop_times_index = attr.ib(default=attr.Factory(dict)) # EXAMPLE - Stop(Eindhoven Centraal-5 [2323599]): 0, Stop(Tilburg-2 [2324474]): 1, ... }
    hint = attr.ib(default=None) # EXAMPLE - 1178
    long_name = attr.ib(default=None) # EXAMPLE1 - 'Intercity' EXAMPLE2 - 'Sprinter'

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return "Trip(hint={hint}, stop_times={stop_times})".format(
            hint=self.hint if self.hint is not None else self.id,
            stop_times=len(self.stop_times),
        )

    # def __getitem__(self, n):
    def __getitem__(self, n: int) -> TripStopTime:
        """
        EXAMPLE
        Args:
            -   n=1
        
        Returns:
            -   TripStopTime(trip_id=1178:50, stopidx=1, stop_id=2324474, dts_arr=79500, dts_dep=79740, fare=0)
        """
        return self.stop_times[n]

    def __len__(self):
        return len(self.stop_times)

    def __iter__(self):
        return iter(self.stop_times)

    def trip_stop_ids(self):
        """Tuple of all stop ids in trip
        
        EXAMPLE
        Returns:
            -   ('2323599', '2324474', '2422045', '2427778', '2422319', '2422082', '2423310')
        """
        return tuple([s.stop.id for s in self.stop_times])

    def add_stop_time(self, stop_time: TripStopTime):
        """Add stop time"""
        if np.isfinite(stop_time.dts_arr) and np.isfinite(stop_time.dts_dep):
            assert stop_time.dts_arr <= stop_time.dts_dep
            assert (
                not self.stop_times or self.stop_times[-1].dts_dep <= stop_time.dts_arr
            )
        self.stop_times.append(stop_time)
        self.stop_times_index[stop_time.stop] = len(self.stop_times) - 1

    def get_stop(self, stop: Stop) -> TripStopTime:
        """Get stop
        
        EXAMPLE
        Args:
            -   stop=timetable.stations.get_stops('Rotterdam Centraal')[0]
        
        Returns:
            -   TripStopTime(trip_id=1178:50, stopidx=3, stop_id=2427778, dts_arr=81960, dts_dep=82080, fare=0)
        """
        return self.stop_times[self.stop_times_index[stop]]
    
    def get_fare(self, depart_stop: Stop) -> int:
        """Get fare from depart_stop
        
        EXAMPLE
        Args:
            -   stop=timetable.stations.get_stops('Rotterdam Centraal')[0]
        
        Returns:
            -   0
        """
        stop_time = self.get_stop(depart_stop)
        return 0 if stop_time is None else stop_time.fare
    
    ### LOOK AT STOP CLASS FIRST
    # def get_stop_occupancy(self, depart_stop: Stop) -> int:
    #     """Get stop occupancy from depart_stop"""
    #     stop_occupancy = self.get_stop(depart_stop)
    #     return 0 if stop_time is None else stop_time.occupancy


class Trips:
    """Trips
    
    A collection (dict) of Trip instances and store (int) of last index"""

    def __init__(self):
        self.set_idx = dict() # EXAMPLE - 1: Trip(hint=3984, stop_times=2), 2: Trip(hint=3983, stop_times=2), 3: Trip(hint=3988, stop_times=2), 4: Trip(hint=7054, stop_times=9), 5: Trip(hint=3980, stop_times=2), ... }
        self.last_id = 1

    def __repr__(self):
        return f"Trips(n_trips={len(self.set_idx)})"

    # def __getitem__(self, trip_id):
    def __getitem__(self, trip_id: int):
        """
        EXAMPLE
        Args:
            -   trip_id=1
        
        Returns:
            -   Trip(hint=3984, stop_times=2)
        """
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
    """Route
    
    A collection (list) of trips and stops, and a collection (dict) of stop orders."""

    id = attr.ib(default=None)
    trips = attr.ib(default=attr.Factory(list))
    stops = attr.ib(default=attr.Factory(list))
    stop_order = attr.ib(default=attr.Factory(dict))

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return "Route(id={0.id}, trips={trips})".format(self, trips=len(self.trips),)

    # def __getitem__(self, n):
    def __getitem__(self, n: int) -> Trip:
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
    """Routes
    
    A collection of Route class objects.
    You can get the routes that serve any given stop."""

    def __init__(self):
        self.set_idx = dict() # EXAMPLE - {1: Route(id=1, trips=4), 2: Route(id=2, trips=5), 3: Route(id=3, trips=22), 4: Route(id=4, trips=24), 5: Route(id=5, trips=3), ... }
        self.set_stops_idx = dict() # EXAMPLE - {('2323896', '2324446'): Route(id=1, trips=4), ('2324446', '2323896'): Route(id=2, trips=5), ('2422000', '2324675', '2324317', '2323884', '2323536', '2422066', '2423717', '2323186', '2422569'): Route(id=3, trips=22), ('2323875', '2323872', '2324252', '2324255', '2324258', '2324750', '2324748', '2323264', '2422025', '2422148', '2422334', '2422220', '2422223', '2324040', '2323547', '2324640', '2323757', '2423355', '2423318'): Route(id=4, trips=24), ('2422147', '2422029', '2422282', '2422163', '2323925', '2423303', '2323857', '2323493', '2323906', '2323377', '2324608'): Route(id=5, trips=3), ... }
        self.stop_to_routes = defaultdict(list) # {Stop: [Route]}  EXAMPLE - {Stop(Heerlen-5 [2323896]): [Route(id=1, trips=4), Route(id=2, trips=5), Route(id=26, trips=1), Route(id=198, trips=1), Route(id=211, trips=14), Route(id=237, trips=2), Route(id=296, trips=17), Route(id=371, trips=3), Route(id=428, trips=1), Route(id=466, trips=1), Route(id=528, trips=1), Route(id=534, trips=2), Route(id=558, trips=1), Route(id=564, trips=2), Route(id=571, trips=3), Route(id=701, trips=5), Route(id=723, trips=1), Route(id=853, trips=1)], ... }
        self.last_id = 1

    def __repr__(self):
        return f"Routes(n_routes={len(self.set_idx)})"

    def __getitem__(self, route_id: int):
        """
        EXAMPLE
        Args:
            -   route_id=1
        
        Returns:
            -   Route(id=1, trips=4)
        """
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
        """Get routes of stop
        
        EXAMPLE
        Args:
            -   stop=timetable.stations.get_stops('Heerlen')[0]
            
        Returns:
            -   [Route(id=1, trips=4), Route(id=2, trips=5), Route(id=26, trips=1), Route(id=198, trips=1), Route(id=211, trips=14), Route(id=237, trips=2), Route(id=296, trips=17), Route(id=371, trips=3), Route(id=428, trips=1), Route(id=466, trips=1), Route(id=528, trips=1), Route(id=534, trips=2), Route(id=558, trips=1), Route(id=564, trips=2), Route(id=571, trips=3), Route(id=701, trips=5), Route(id=723, trips=1), Route(id=853, trips=1)]
        """
        return self.stop_to_routes[stop]


@attr.s(repr=False, cmp=False)
class Transfer:
    """Transfer
    
    Details id, from/to stop and layovertime
    
    LAYOVER TIME IS USEFUL FOR OCCUPANCY PENALTY"""

    id = attr.ib(default=None) # EXAMPLE - 1
    from_stop = attr.ib(default=None) # EXAMPLE - Stop(Vlissingen-3 [2324635])
    to_stop = attr.ib(default=None) # EXAMPLE - Stop(Vlissingen-1 [2324633])
    layovertime = attr.ib(default=300) # EXAMPLE - 120

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, trip):
        return same_type_and_id(self, trip)

    def __repr__(self):
        return f"Transfer(from_stop={self.from_stop}, to_stop={self.to_stop}, layovertime={self.layovertime})"


class Transfers:
    """Transfers
    
    A collection (dict) of idxs, stop_to_stop_idxs and last id (int)"""

    def __init__(self):
        self.set_idx = dict() # EAMPLE - {1: Transfer(from_stop=Stop(Vlissingen-3 [2324635]), to_stop=Stop(Vlissingen-1 [2324633]), layovertime=120), ... }
        self.stop_to_stop_idx = dict() # EXAMPLE - {(Stop(Vlissingen-3 [2324635]), Stop(Vlissingen-1 [2324633])): Transfer(from_stop=Stop(Vlissingen-3 [2324635]), to_stop=Stop(Vlissingen-1 [2324633]), layovertime=120), ... }
        self.last_id = 1 # EXAMPLE - 3037

    def __repr__(self):
        return f"Transfers(n_transfers={len(self.set_idx)})"

    def __getitem__(self, transfer_id):
        """
        EXAMPLE
        Args:
            -   transfer_id=1
        
        Returns:
            -   Transfer(from_stop=Stop(Vlissingen-3 [2324635]), to_stop=Stop(Vlissingen-1 [2324633]), layovertime=120)
        """
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


###############################################################################

# ROUTING STUFF

###############################################################################
@dataclass
class Leg:
    """Leg
    
    Details from, to (Stop), Trip, earliest arrival, n_trips and fare
    
    MAY HELP WITH OCCUPANCY"""

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
        return [ # tst = TripStopTime
            tst.dts_dep for tst in self.trip.stop_times if self.from_stop == tst.stop
        ][0]

    @property
    def arr(self):
        """Arrival time"""
        return [ # tst = TripStopTime
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
    """Label
    
    INTEGRAL TO OCCUPANCY"""

    earliest_arrival_time: int
    fare: int  # total fare
    trip: Trip  # trip to take to obtain travel_time and fare
    from_stop: Stop  # stop to hop-on the trip
    # occupancy: int  # 25/05/2022
    n_trips: int = 0
    infinite: bool = False

    @property
    def criteria(self):
        """Criteria"""
        return [self.earliest_arrival_time, self.fare, self.n_trips]
        # return [self.earliest_arrival_time, self.fare, self.n_trips, self.occupancy]

    def update(self, earliest_arrival_time=None, fare_addition=None, from_stop=None):
    # def update(self, earliest_arrival_time=None, fare_addition=None, from_stop=None, occupancy_addition=None):
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

                # occupancy=self.occupancy + occupancy_addition
                # if occupancy_addition is not None
                # else self.occupancy

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
                # occupancy=self.occupancy
                n_trips=self.n_trips + 1 if self.trip != trip else self.n_trips,
                infinite=self.infinite,
            )
        )


@dataclass(frozen=True)
class Bag:
    """
    Bag B(k,p) or route bag B_r

    A collection (list) of labels
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

    INTEGRAL TO OCCUPANCY
    """

    legs: List[Leg] = field(default_factory=list)

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
                # and (self.occupancy() <= jrny.occupancy)
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
                sec2str(self.arr() - dep_secs), sec2str(dep_secs),
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

    return list(compress(labels, is_efficient))
