"""Run RAPTOR algorithm"""
from typing import List, Tuple

from loguru import logger

from pyraptor.dao.timetable import Timetable
from pyraptor.model.datatypes import Stop, Trip, TripStopTime
from pyraptor.util import (
    str2sec,
    sec2str,
    SAVE_RESULTS,
    T1H,
    T6H,
    T24H,
    TRANSFER_COST,
)


def traverse_trips(
    timetable: Timetable, evaluations: List, k: int, ids: List, bag, dep_secs: int
) -> Tuple:
    """
    Iterator through the stops reachable and add all new reachable stops
    by following all trips from the reached stations. Trips are only followed
    in the direction of travel and beyond already added points.

    :param k: current round
    :param ids: current stops reached
    :param bag: numpy array with info over reached stops
    :param dep_secs: Departure time in seconds
    """

    new_stops = []

    n_evaluations = 0
    n_improvements = 0

    for start_stop in ids:

        # how long it took to get to the stop so far (0 for start node)
        time_sofar = bag[start_stop.index][0]

        # get list of all trips associated with this stop
        trips = get_trip_ids_for_stop(timetable, start_stop, dep_secs + time_sofar, T1H)

        for (trip, current_stopidx) in trips:

            # get all following stop times for this trip
            stop_times = trip.get_next_trip_stop_times(current_stopidx)

            # for all following stops, calculate time to reach
            for arrive_stop_time in stop_times:
                n_evaluations += 1

                if SAVE_RESULTS:
                    evaluations.append((k, start_stop, trip, arrive_stop_time))

                # time to reach is diff from start time to arrival (plus any baseline cost)
                arrive_time_adjusted = arrive_stop_time.dts_arr - dep_secs

                # only update if does not exist yet or is faster
                old_value = bag[arrive_stop_time.stop.index][0]
                if arrive_time_adjusted < old_value:
                    n_improvements += 1
                    bag[arrive_stop_time.stop.index] = (
                        arrive_time_adjusted,
                        trip.id,
                        start_stop.index,
                    )
                    new_stops.append(arrive_stop_time.stop)

    logger.debug("- Evaluations    : {}".format(n_evaluations))
    logger.debug("- Improvements   : {}".format(n_improvements))

    return new_stops, bag, evaluations


def get_trip_ids_for_stop(
    timetable: Timetable,
    stop_id: Stop,
    dep_secs: int,
    forward: int = T6H,
) -> List[Tuple[Trip, int]]:
    """
    Takes a stop and departure time and get associated trip ids.
    The forward parameter limits the time frame starting at the departure time.
    Default framesize is 60 minutes.
    Times are specified in seconds since midnight.

    :param stop_id: Stop
    :param dep_time: Departure time
    :param forward: Period forward limitimg trips
    """
    trip_stop_times = timetable.trip_stop_times.get_trip_stop_times_for_stop(
        stop_id, dep_secs, forward
    )
    trips = list(set([(tst.trip, tst.stopidx) for tst in trip_stop_times]))
    return trips


def add_transfer_time(stops: List[Stop], bag) -> Tuple:
    """Add transfers between platforms."""

    # TODO Implement transfer station boolean

    new_stops = []

    # add in transfers to other platforms
    for stop in stops:

        station = stop.station
        other_station_stops = [st for st in station.stops if st != stop]

        time_sofar = bag[stop.index][0]
        for arrive_stop in other_station_stops:
            arrive_time_adjusted = time_sofar + get_transfer_time(
                stop, arrive_stop, time_sofar, 0
            )
            old_value = bag[arrive_stop.index][0]
            if arrive_time_adjusted < old_value:
                bag[arrive_stop.index] = (arrive_time_adjusted, 0, stop.index)
                new_stops.append(arrive_stop)

    return new_stops, bag


def get_transfer_time(stop_from: int, stop_to: int, time_sec: int, dow: int) -> int:
    """
    Calculate the transfer time from a stop to another stop (usually two platforms at one station
    :param stop_from: Origin platform
    :param stop_to: Destination platform
    :param time_sec: Time of day (seconds since midnight)
    :param dow: day of week (Monday = 0, Tuesday = 1, ...)
    """
    return TRANSFER_COST


def is_dominated(timetable: Timetable, original_journey, new_journey) -> bool:
    """Check if new journey is dominated by another journey"""
    # First journey
    if not original_journey:
        return False

    # No improvement
    if original_journey == new_journey:
        return True

    def depart(jrny) -> int:
        depart_leg = jrny[0] if jrny[0][1] != 0 else jrny[1]
        depart_stop = timetable.stops.get_by_index(depart_leg[0])
        depart_trip = timetable.trips.set_idx[depart_leg[1]]
        depart_stop_time = [
            st for st in depart_trip.stop_times if st.stop == depart_stop
        ][0]
        return depart_stop_time.dts_dep

    def arrival(jrny) -> int:
        arrival_leg = jrny[-1]
        arrival_stop = timetable.stops.get_by_index(arrival_leg[2])
        arrival_trip = timetable.trips.set_idx[arrival_leg[1]]
        arrival_stop_time = [
            st for st in arrival_trip.stop_times if st.stop == arrival_stop
        ][0]
        return arrival_stop_time.dts_arr

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


def final_destination(to_stops: List[Stop], bag) -> Stop:
    """
    Find the destination ID with the shortest distance.
    Required in order to prevent adding travel time to the arrival time.

    :param to_ids:
    :param bag:
    """
    final_stop = 0
    distance = T24H
    for stop in to_stops:
        if bag[stop.index][0] < distance:
            distance = bag[stop.index][0]
            final_stop = stop
    return final_stop


def reconstruct_journey(destination: Stop, bag):
    """Construct journey for destination from values in bag."""
    jrny = []
    current = destination.index
    while current != 0:
        # bag = (travel_time, trip_id, previous_stop.index)
        # journey = (previous_stop.index, trip.id, to_stop.index)
        jrny.append((bag[current][2], bag[current][1], current))
        current = bag[current][2]
    jrny.reverse()
    return jrny


def print_journey(timetable, journey, dep_secs=None):
    """
    Print the given journey to logger info
    """
    logger.info("Journey:")

    if len(journey) == 0:
        logger.info("No journey available")
        return

    # Print all legs in journey
    # leg = (previous_stop.index, trip.id, to_stop.index)
    for leg in journey:
        if leg[1] != 0:
            # Stop and trip
            from_stop = timetable.stops.get_by_index(leg[0])
            to_stop = timetable.stops.get_by_index(leg[2])
            trip = timetable.trips.set_idx[leg[1]]

            dep = [tst.dts_dep for tst in trip.stop_times if from_stop == tst.stop][0]
            arr = [tst.dts_arr for tst in trip.stop_times if to_stop == tst.stop][0]

            msg = (
                str(sec2str(dep))
                + " "
                + from_stop.station.name.ljust(20)
                + "(p. "
                + str(from_stop.platform_code).rjust(3)
                + ") TO "
                + str(sec2str(arr))
                + " "
                + to_stop.station.name.ljust(20)
                + "(p. "
                + str(to_stop.platform_code).rjust(3)
                + ") WITH "
                + str(trip.hint)
            )
            logger.info(msg)

    # Departure time of first leg
    depart_leg = journey[0] if journey[0][1] != 0 else journey[1]
    depart_stop = timetable.stops.get_by_index(depart_leg[0])
    depart_trip = timetable.trips.set_idx[depart_leg[1]]
    depart_stop_time = [st for st in depart_trip.stop_times if st.stop == depart_stop][
        0
    ]

    # Arrival time of last leg
    arrival_leg = journey[-1]
    arrival_stop = timetable.stops.get_by_index(arrival_leg[2])
    arrival_trip = timetable.trips.set_idx[arrival_leg[1]]
    arrival_stop_time = [
        st for st in arrival_trip.stop_times if st.stop == arrival_stop
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
