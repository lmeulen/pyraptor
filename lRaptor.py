import os
import io
import sys
import pandas as pd
import time
import logging
import argparse
from datetime import datetime
from copy import copy
from dataclasses import dataclass

# Default transfer time is 3 minutes
TRANSFER_COST = (3 * 60)
SAVE_RESULTS = False

T24H = 24 * 60 * 60
T6H = 6 * 60 * 60
T30M = 30 * 60
T3M = 3 * 60

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)


@dataclass
class Timetable:
    agencies = None
    routes = None
    trips = None
    calendar = None
    stop_times = None
    stop_times_filtered = None
    stops = None
    station2stops = None
    stop_times_for_trips = None
    transfers = None


def parse_time_to_sec(time_str):
    """
    Convert hh:mm:ss to seconds since midnight
    :param time_str: String in format hh:mm:ss
    """
    spl = time_str.strip().split(":")
    if len(spl) == 3:
        h, m, s = spl
        return int(h) * 3600 + int(m) * 60 + int(s)
    m, s = spl
    return int(m) * 60 + int(s)


def parse_sec_to_time(scnds, show_sec=False):
    """
    Convert hh:mm:ss to seconds since midnight
    :param show_sec: only show :ss if True
    :param scnds: Seconds to translate to hh:mm:ss
    """
    h = int(scnds / 3600)
    m = int((scnds % 3600) / 60)
    s = int(scnds % 60)
    return "{:02d}:{:02d}:{:02d}".format(h, m, s) if show_sec else "{:02d}:{:02d}".format(h, m)


def stop_time_to_str(stop):
    """
    Convert a GTFS stoptime location to a human readable string
    :param stop:
    :return:
    """
    s = str(stop['trip_id']) + '-' + str(stop['stop_sequence']) + ' ' + str(stop['stop_id']).ljust(2) + ' '
    s += str(stop['arrival_time']) + '-' + str(stop['departure_time']) + ' ' + str(stop['shape_dist_traveled'])
    return s


def stop_to_str(loc):
    """
    Convert a GTFS stop location location to a human readable string
    :param loc:
    :return:
    """
    s = str(loc['stop_id']) + ' - ' + str(loc['stop_name']) + ' - ' + str(loc['platform_code'])
    s += ' - ' + str(loc['stop_code']) + ' - ' + str(loc['parent_station'])
    return s


def str2bool(v):
    """
    Convert a string to bool, function for the argument parser
    :param v: string representing true or false value in any format
    :return: bool
    """
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def read_timetable(gtfs_dir, use_cache):
    """
    Read the timetable information from either cache or GTFS directory
    Global parameter READ_GTFS determines cache or reading original GTFS files
    :return:
    """

    start_time = time.perf_counter()
    tt = Timetable()
    if use_cache & os.path.exists(os.path.join('timetable_cache', 'stop_times.pcl')):
        tt.agencies = pd.read_pickle(os.path.join('timetable_cache', 'agencies.pcl'))
        tt.routes = pd.read_pickle(os.path.join('timetable_cache', 'routes.pcl'))
        tt.trips = pd.read_pickle(os.path.join('timetable_cache', 'trips.pcl'))
        tt.calendar = pd.read_pickle(os.path.join('timetable_cache', 'calendar.pcl'))
        tt.stop_times = pd.read_pickle(os.path.join('timetable_cache', 'stop_times.pcl'))
        tt.stops = pd.read_pickle(os.path.join('timetable_cache', 'stops.pcl'))
    else:
        tt.agencies = pd.read_csv(os.path.join(gtfs_dir, 'agency.txt'))

        tt.routes = pd.read_csv(os.path.join(gtfs_dir, 'routes.txt'))

        tt.trips = pd.read_csv(os.path.join(gtfs_dir, 'trips.txt'))
        tt.trips.trip_short_name = tt.trips.trip_short_name.astype(int)
        tt.trips.shape_id = tt.trips.shape_id.astype('Int64')

        tt.calendar = pd.read_csv(os.path.join(gtfs_dir, 'calendar_dates.txt'))
        tt.calendar.date = tt.calendar.date.astype(str)

        tt.stop_times = pd.read_csv(os.path.join(gtfs_dir, 'stop_times.txt'))
        tt.stop_times.arrival_time = tt.stop_times.apply(lambda x: parse_time_to_sec(x['arrival_time']), axis=1)
        tt.stop_times.departure_time = tt.stop_times.apply(lambda x: parse_time_to_sec(x['departure_time']), axis=1)
        tt.stop_times.stop_id = tt.stop_times.stop_id.astype(str)
        tt.stop_times_filtered = None

        tt.stops = pd.read_csv(os.path.join(gtfs_dir, 'stops.txt'))
        # Filter out the general station codes
        tt.stops = tt.stops[~tt.stops.stop_id.str.startswith('stoparea')]

        tt.agencies.to_pickle(os.path.join('timetable_cache', 'agencies.pcl'))
        tt.routes.to_pickle(os.path.join('timetable_cache', 'routes.pcl'))
        tt.trips.to_pickle(os.path.join('timetable_cache', 'trips.pcl'))
        tt.calendar.to_pickle(os.path.join('timetable_cache', 'calendar.pcl'))
        tt.stop_times.to_pickle(os.path.join('timetable_cache', 'stop_times.pcl'))
        tt.stops.to_pickle(os.path.join('timetable_cache', 'stops.pcl'))

    logger.info("Reading GTFS took {:0.4f} seconds".format(time.perf_counter() - start_time))
    logger.debug('Agencies  : {}'.format(len(tt.agencies)))
    logger.debug('Routes    : {}'.format(len(tt.routes)))
    logger.debug('Stops     : {}'.format(len(tt.stops)))
    logger.debug('Trips     : {}'.format(len(tt.trips)))
    logger.debug('Stoptimes : {}'.format(len(tt.stop_times)))
    return tt


def get_trip_ids_for_stop(timetable, stop_id, departure_time, forward=60 * 60 * 6, tripfilter=None):
    """Takes a stop and departure time and get associated trip ids.
       The forward parameter limits the time frame starting at the departure time.
       Default framesize is 60 minutes
       Times asre specified in seconds sincs midnight
    """

    mask_1 = timetable.stop_times_filtered.index == stop_id
    mask_2 = timetable.stop_times_filtered.departure_time.between(departure_time, departure_time + forward)
    mask_3 = True
    if tripfilter:
        mask_3 = ~timetable.stop_times_filtered.trip_id.isin(tripfilter)
    # extract the list of qualifying trip ids
    potential_trips = timetable.stop_times_filtered[mask_1 & mask_2 & mask_3].trip_id.unique()
    return potential_trips.tolist()


def traverse_trips(timetable, current_ids, time_to_stops_orig, last_leg_orig, departure_time, filter_trips):
    """ Iterator through the stops reachable and add all new reachable stops
        by following all trips from the reached stations. Trips are only followed
        in the direction of travel and beyond already added points
    :param timetable: Timetable data
    :param current_ids: Current stops reached
    :param time_to_stops_orig: List of departure locations (e.g. multiple platforms for one station)
    :param last_leg_orig: List of last leg to reached stations
    :param departure_time: Departure time
    :param filter_trips: trips to filter from the list of potential trips
    """

    # prevent upstream mutation of dictionary
    extended_time_to_stops = copy(time_to_stops_orig)
    extended_last_leg = copy(last_leg_orig)
    new_stops = []

    baseline_filter_trips = copy(filter_trips)
    logger.debug('        Filtered  trips: {}'.format(len(baseline_filter_trips)))
    filter_trips = []
    i = 0
    for ref_stop_id in current_ids:
        # how long it took to get to the stop so far (0 for start node)
        baseline_cost = extended_time_to_stops[ref_stop_id]
        # get list of all trips associated with this stop
        reachable_trips = get_trip_ids_for_stop(timetable, ref_stop_id, departure_time + baseline_cost,
                                                forward=3600, tripfilter=None)
        filter_trips.extend(reachable_trips)
        for potential_trip in reachable_trips:

            # get all the stop time arrivals for that trip
            stop_times_trip = timetable.stop_times_for_trips[timetable.stop_times_for_trips.index == potential_trip]

            # get the "hop on" point
            from_here = stop_times_trip[stop_times_trip.stop_id == ref_stop_id].iloc[0]['stop_sequence']
            # get all following stops
            stop_times_after = stop_times_trip[stop_times_trip.stop_sequence > from_here]

            # for all following stops, calculate time to reach
            arrivals_zip = zip(stop_times_after.arrival_time, stop_times_after.stop_id)
            for arrive_time, arrive_stop_id in arrivals_zip:
                i += 1
                # time to reach is diff from start time to arrival (plus any baseline cost)
                arrive_time_adjusted = arrive_time - departure_time

                # only update if does not exist yet or is faster
                old_value = extended_time_to_stops.get(arrive_stop_id, T24H)
                if old_value == T24H:
                    extended_time_to_stops[arrive_stop_id] = arrive_time_adjusted
                    extended_last_leg[arrive_stop_id] = (potential_trip, ref_stop_id)
                    new_stops.append(arrive_stop_id)
                if arrive_time_adjusted < old_value:
                    extended_last_leg[arrive_stop_id] = (potential_trip, ref_stop_id)
                    extended_time_to_stops[arrive_stop_id] = arrive_time_adjusted

    logger.debug('         Evaluations    : {}'.format(i))
    filter_trips = list(set(filter_trips))
    return extended_time_to_stops, extended_last_leg, new_stops, filter_trips


def add_transfer_time(timetable, current_ids, time_to_stops_orig, last_leg_orig, transfer_cost=TRANSFER_COST):
    """
    Add transfers between platforms
    :param timetable:
    :param current_ids:
    :param time_to_stops_orig:
    :param last_leg_orig:
    :param transfer_cost:
    :return:
    """

    # prevent upstream mutation of dictionary
    extended_time_to_stops = copy(time_to_stops_orig)
    extended_last_leg = copy(last_leg_orig)
    new_stops = []

    # add in transfers to other platforms
    for stop_id in current_ids:
        stopdata = timetable.stops[timetable.stops.index == stop_id].iloc[0]
        stoparea = stopdata['parent_station']

        # Only add transfers if it is a transfer station
        if stopdata['transfer_station']:
            # time to reach new nearby stops is the transfer cost plus arrival at last stop
            arrive_time_adjusted = extended_time_to_stops[stop_id] + transfer_cost

            # only update if currently inaccessible or faster than currrent option
            # for arrive_stop_id in timetable.stops[timetable.stops.parent_station == stoparea]['stop_id'].values:
            for arrive_stop_id in timetable.station2stops[timetable.station2stops.index == stoparea]['stop_id'].values:
                old_value = extended_time_to_stops.get(arrive_stop_id, T24H)
                if old_value == T24H:
                    extended_time_to_stops[arrive_stop_id] = arrive_time_adjusted
                    extended_last_leg[arrive_stop_id] = (0, stop_id)
                    new_stops.append(arrive_stop_id)
                if arrive_time_adjusted < old_value:
                    extended_time_to_stops[arrive_stop_id] = arrive_time_adjusted
                    extended_last_leg[arrive_stop_id] = (0, stop_id)

    return extended_time_to_stops, extended_last_leg, new_stops


def determine_parameters(timetable, start_name, end_name, departure_time):
    """ Determine algorithm paramters based upon human readable information
        start_name : Location to start journey
        end_name: Endpoint of the journey
        departure_time: Time of the departure in hh:mm:ss
    """

    # look at all trips from that stop that are after the depart time
    departure = parse_time_to_sec(departure_time)

    # get all information, including the stop ids, for the start and end nodes
    from_loc = timetable.stops[timetable.stops.stop_name == start_name].index.to_list()
    to_loc = timetable.stops[timetable.stops.stop_name == end_name].index.to_list()

    return from_loc, to_loc, departure


def final_destination(to_ids, reached_ids):
    """ Find the destination ID with the shortest distance
        Required in order to prevent adding travel time to the arrival time
    :param to_ids:
    :param reached_ids:
    :return:
    """

    final_id = ''
    distance = 999999
    for to_id in to_ids:
        if to_id in reached_ids:
            if reached_ids[to_id] < distance:
                distance = reached_ids[to_id]
                final_id = to_id
    return final_id


def perform_lraptor(timetable, departure_name, arrival_name, departure_time, iterations):
    """
    Perform the Raptor algorithm
    :param timetable: Time table
    :param departure_name: Name of departure location
    :param arrival_name: Name of arrival location
    :param departure_time: Time of departure, str format (hh:mm:sss)
    :param iterations: Number of iterations to perform
    :return:
    """

    # Determine start and stop area
    (from_stops, to_stops, dep_secs) = determine_parameters(timetable, departure_name, arrival_name, departure_time)
    logger.debug('Departure ID : ' + str(from_stops))
    logger.debug('Arrival ID   : ' + str(to_stops))
    logger.debug('Time         : ' + str(dep_secs))

    # initialize lookup with start node taking 0 seconds to reach
    k_results = {}
    reached_stops = {}
    reached_stops_last_leg = {}
    new_stops_total = []
    filter_trips = []
    mask = timetable.stop_times.departure_time.between(dep_secs, dep_secs + T6H)
    timetable.stop_times_filtered = timetable.stop_times[mask].copy()

    for from_stop in from_stops:
        reached_stops[from_stop] = 0
        reached_stops_last_leg[from_stop] = (0, '')
        new_stops_total.append(from_stop)
    logger.debug('Starting from IDS : '.format(str(reached_stops)))

    for k in range(1, iterations + 1):
        logger.info("Analyzing possibilities round {}".format(k))

        # get list of stops to evaluate in the process
        stops_to_evaluate = list(new_stops_total)
        logger.info("    Stops to evaluate count: {}".format(len(stops_to_evaluate)))

        # update time to stops calculated based on stops accessible
        t = time.perf_counter()
        reached_stops, reached_stops_last_leg, new_stops_travel, filter_trips = \
            traverse_trips(timetable, stops_to_evaluate, reached_stops, reached_stops_last_leg, dep_secs, filter_trips)
        logger.info("    Travel stops  calculated in {:0.4f} seconds".format(time.perf_counter() - t))
        logger.debug("    {} stops added".format(len(new_stops_travel)))

        # now add footpath transfers and update
        t = time.perf_counter()
        stops_to_evaluate = list(reached_stops.keys())
        reached_stops, reached_stops_last_leg, new_stops_transfer = \
            add_transfer_time(timetable, stops_to_evaluate, reached_stops, reached_stops_last_leg)
        logger.info("    Transfers calculated in {:0.4f} seconds".format(time.perf_counter() - t))
        logger.info("    {} stops added".format(len(new_stops_transfer)))

        new_stops_total = set(new_stops_travel).union(new_stops_transfer)

        logger.info("    {} stops to evaluate in next round".format(len(new_stops_total)))

        # Store the results for this round
        k_results[k] = reached_stops
        mask = ~timetable.stop_times_filtered.trip_id.isin(filter_trips)
        timetable.stop_times_filtered = timetable.stop_times_filtered[mask]

    # Determine the best destionation ID, destination is a platform.
    dest_id = final_destination(to_stops, reached_stops)
    if dest_id != '':
        logger.info("Destination code   : {} ".format(dest_id))
        logger.info("Time to destination: {} minutes".format(reached_stops[dest_id] / 60))
    else:
        logger.info("Destination unreachable with given parameters")
    return k_results, dest_id, reached_stops_last_leg


def export_results(k, fd, tt):
    """
    Export results to a CSV file with stations and traveltimes (per iteration)
    :param k: datastructure with results per iteration
    :param fd: Final destination last leg
    :param tt: Timetable
    :return: DataFrame with the results exported
    """
    filename1 = 'res_{date:%Y%m%d_%H%M%S}_traveltime.csv'.format(date=datetime.now())
    logger.debug('Export results to {}'.format(filename1))
    datastring = 'round,stop_id,stop_name,platform_code,travel_time\n'
    for i in list(k.keys()):
        locations = k[i]
        for destination in locations:
            traveltime = locations[destination]
            stop = tt.stops[tt.stops.stop_id == destination]
            name = stop['stop_name'].values[0]
            platform = stop['platform_code'].values[0]
            datastring += (str(i) + ',' + str(destination) + ',' + str(name) + ',' + str(platform) + ',' +
                           str(traveltime) + '\n')
    df = pd.read_csv(io.StringIO(datastring), sep=",")
    df = df[['round', 'stop_name', 'travel_time']].groupby(['round', 'stop_name']).min().sort_values('travel_time')
    df.travel_time = df.apply(lambda x: parse_sec_to_time(x.travel_time), axis=1)
    df.to_csv(filename1)

    filename2 = 'res_{date:%Y%m%d_%H%M%S}_last_legs.csv'.format(date=datetime.now())
    logger.debug('Export results to {}'.format(filename2))
    datastring = 'from_id,trip_id,stop_id\n'
    for i in list(fd.keys()):
        frm = i
        via = fd[i][0]
        to = fd[i][0]
        datastring += (str(frm) + ',' + str(via) + ',' + str(to) + '\n')
    df2 = pd.read_csv(io.StringIO(datastring), sep=",")
    df2.to_csv(filename2)

    return df, df2


def reconstruct_journey(destination, legs_list):
    j = []
    current = destination
    while current != '':
        t = legs_list[current]
        j.append((t[1], t[0], current))
        current = t[1]
    j.reverse()
    return j


def print_journey(j, tt, dep_time):
    """
    Print the given journey to logger info
    :param j: journey
    :param tt: timetable
    :param dep_time: Original requested departure
    :return: -
    """
    logger.info('Journey:')
    arr = dep_time
    for leg in j:
        if leg[1] != 0:
            frm = tt.stops[tt.stops.index == leg[0]].stop_name.values[0]
            frm_p = tt.stops[tt.stops.index == leg[0]].platform_code.values[0]
            to = tt.stops[tt.stops.index == leg[2]].stop_name.values[0]
            to_p = tt.stops[tt.stops.index == leg[2]].platform_code.values[0]
            tr = tt.trips[tt.trips.trip_id == leg[1]].trip_short_name.values[0]
            trid = tt.trips[tt.trips.trip_id == leg[1]].trip_id.values[0]
            dep = tt.stop_times[(tt.stop_times.index == leg[0]) &
                                (tt.stop_times.trip_id == leg[1])].departure_time.values[0]
            arr = tt.stop_times[(tt.stop_times.index == leg[2]) &
                                (tt.stop_times.trip_id == leg[1])].arrival_time.values[0]
            logger.info(str(parse_sec_to_time(dep)) + " " + frm.ljust(20) + '(p. ' + frm_p.rjust(3) + ') TO ' +
                        str(parse_sec_to_time(arr)) + " " + to.ljust(20) + '(p. ' + to_p.rjust(3) + ') WITH ' +
                        str(tr) + ' (' + str(trid) + ')')

    fdt = j[0] if j[0][1] != 0 else j[1]
    fdt = tt.stop_times[(tt.stop_times.index == fdt[0]) &
                        (tt.stop_times.trip_id == fdt[1])].departure_time.values[0]
    logger.info('Duration : {} ({} from request time {})'.format(parse_sec_to_time(fdt - parse_time_to_sec(dep_time)),
                                                                 parse_sec_to_time(arr - parse_time_to_sec(dep_time)),
                                                                 parse_sec_to_time(parse_time_to_sec(dep_time))))


def parse_arguments():
    # --i gtfs-extracted --s "Arnhem Zuid" --e "Oosterbeek" --d "08:30:00" --r 2 --c True
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, help="Input directory")
    parser.add_argument("-s", "--startpoint", type=str, help="Startpoint of the journey")
    parser.add_argument("-e", "--endpoint", type=str, help="Endpoint of the journey")
    parser.add_argument("-d", "--departure", type=str, help="Departure time hh:mm:ss")
    parser.add_argument("-r", "--rounds", type=int, help="Number of rounds to execute the RAPTOR algorithm")
    parser.add_argument("-c", "--cache", type=str2bool, default=False, help="Use cached GTFS")
    arguments = parser.parse_args(sys.argv[1:])
    logger.debug('Parameters     : ' + str(sys.argv[1:]))
    logger.debug('Input directoy : ' + arguments.input)
    logger.debug('Start point    : ' + arguments.startpoint)
    logger.debug('End point      : ' + arguments.endpoint)
    logger.debug('Departure time : ' + arguments.departure)
    logger.debug('Rounds         : ' + str(arguments.rounds))
    logger.debug('Cached GTFS    : ' + str(arguments.cache))
    return arguments


def optimize_timetable(tt):
    # Remove unused data
    tt.agencies = None
    tt.routes = None
    tt.calendar = None
    # stop ID's as integer
    tt.stop_times.stop_id = tt.stop_times.stop_id.astype(int)
    tt.stops.stop_id = tt.stops.stop_id.astype(int)
    # Remove unused columns from trips and stop_times
    tt.trips.drop(['route_id', 'service_id', 'trip_headsign', 'trip_long_name', 'direction_id', 'shape_id'],
                  axis=1, inplace=True)
    tt.stop_times.drop(['shape_dist_traveled'], axis=1, inplace=True)
    # Create dataset for mapping stop_ids to trips
    tt.stop_times_for_trips = tt.stop_times.copy()
    # Clean stops data and add index for stop_id
    tt.stops.drop(['stop_lat', 'stop_lon', 'stop_code', 'zone_id'], axis=1, inplace=True)
    # Lookup table for parent_station to platforms
    tt.station2stops = tt.stops[['parent_station', 'stop_id']].set_index('parent_station')
    # Determine transfer stations (more than two direct destinations reachable)
    tt.transfers = tt.stop_times[['trip_id', 'stop_sequence', 'stop_id']].copy()
    tt.transfers = tt.transfers.sort_values(['trip_id', 'stop_sequence'])
    tt.transfers['prev'] = tt.transfers['trip_id'] == tt.transfers['trip_id'].shift(-1)
    tt.transfers['next_stop_id'] = tt.transfers['stop_id'].shift(-1)
    tt.transfers = tt.transfers[tt.transfers.prev & (tt.transfers.stop_id != tt.transfers.next_stop_id)]
    tt.transfers = tt.transfers[['stop_id', 'next_stop_id']]
    tt.transfers = tt.transfers.merge(tt.stops[['stop_id', 'parent_station']])
    tt.transfers.columns = ['stop_id', 'next_stop_id', 'parent_station']
    tt.transfers = tt.transfers[['parent_station', 'next_stop_id']].drop_duplicates().groupby('parent_station').count()
    tt.transfers['transfer_station'] = tt.transfers['next_stop_id'] > 2
    tt.transfers.drop('next_stop_id', 1, inplace=True)
    # Add transfer info to the stops info
    tt.stops.set_index('stop_id', inplace=True)
    tt.stop_times.set_index('stop_id', inplace=True)
    tt.stop_times_for_trips.set_index('trip_id', inplace=True)
    tt.stops = tt.stops.merge(tt.transfers, left_on='parent_station', right_index=True)


    return tt


if __name__ == "__main__":
    # python -m cProfile -o out.prof lRaptor.py --i gtfs-extracted --s "Arnhem Zuid"
    #                                           --e "Oosterbeek" --d "08:30:00" --r 2 --c True
    # snakeviz out.prof

    args = parse_arguments()

    time_table = read_timetable(args.input, args.cache)
    time_table = optimize_timetable(time_table)

    ts = time.perf_counter()
    traveltimes, final_dest, legs = perform_lraptor(time_table, args.startpoint, args.endpoint,
                                                    args.departure, args.rounds)
    logger.debug('Algorithm executed in {} seconds'.format(time.perf_counter() - ts))

    if SAVE_RESULTS:
        traveltimes, last_legs = export_results(traveltimes, legs, time_table)

    journey = reconstruct_journey(final_dest, legs)
    print_journey(journey, time_table, args.departure)
