import os
import pandas as pd
import sys

GTFSDIR = 'gtfs-nl'
OUTPUTDIR = 'gtfs-extracted'

agencies_names = ['NS']

trip_list = []

if __name__ == "__main__":

    agencies_names = []
    if len(sys.argv) == 1:
        agencies_names.append('NS')
    else:
        for i, arg in enumerate(sys.argv):
            if i > 0:
                agencies_names.append(arg)
    print('Extracting agencies :' + str(agencies_names))

    # Extract agencies
    print('Extracting Agencies')
    agencies = pd.read_csv(os.path.join(GTFSDIR, 'agency.txt'))
    agency_ids = agencies[agencies.agency_name.isin(agencies_names)]['agency_id'].values
    agencies = agencies[agencies.agency_name.isin(agencies_names)][['agency_id', 'agency_name']]
    agencies.to_csv(os.path.join(OUTPUTDIR, 'agency.txt'), index=False)

    # Extract routes
    print('Extracting Routes')
    routes = pd.read_csv(os.path.join(GTFSDIR, 'routes.txt'))
    routes = routes[routes.agency_id.isin(agency_ids)]
    route_ids = routes.route_id.values
    routes = routes[['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type']]
    routes.to_csv(os.path.join(OUTPUTDIR, 'routes.txt'), index=False)

    # Extract trips
    print('Extracting Trips')
    trips = pd.read_csv(os.path.join(GTFSDIR, 'trips.txt'))
    trips = trips[trips.route_id.isin(route_ids)]
    if trip_list:
        trips = trips[trips.trip_short_name.isin(trip_list)]
    trip_ids = trips.trip_id.values
    service_ids = trips.service_id.values
    trips = trips[['route_id', 'service_id', 'trip_id', 'trip_headsign', 'trip_short_name',
                   'trip_long_name', 'direction_id', 'shape_id']]
    trips.trip_short_name = trips.trip_short_name.astype(int)
    trips.shape_id = trips.shape_id.astype('Int64')
    trips.to_csv(os.path.join(OUTPUTDIR, 'trips.txt'), index=False)

    # Extract calendar
    print('Extracting Calendar')
    calendar = pd.read_csv(os.path.join(GTFSDIR, 'calendar_dates.txt'))
    calendar = calendar[calendar.service_id.isin(service_ids)]
    calendar.date = calendar.date.astype(str)
    # calendar['date'] = calendar.date.str[:4] + '-' + calendar.date.str[4:6] + '-' + calendar.date.str[6:8]
    calendar.to_csv(os.path.join(OUTPUTDIR, 'calendar_dates.txt'), index=False)

    # Add date to trips for extended version
    trips = trips.merge(calendar[['service_id', 'date']], on='service_id')
    trips.to_csv(os.path.join(OUTPUTDIR, 'trips_dated.txt'), index=False)

    # Extractstop times
    print('Extracting Stop times')
    stoptimes = pd.read_csv(os.path.join(GTFSDIR, 'stop_times.txt'))
    stoptimes = stoptimes[stoptimes.trip_id.isin(trip_ids)]
    stoptimes.stop_id = stoptimes.stop_id.astype(str)
    stop_ids = stoptimes.stop_id.unique()
    stoptimes = stoptimes[['trip_id', 'stop_sequence', 'stop_id', 'arrival_time',
                           'departure_time', 'shape_dist_traveled']]
    stoptimes.to_csv(os.path.join(OUTPUTDIR, 'stop_times.txt'), index=False)

    # Extract the stops
    # First get the stops (platforms)
    print('Extracting Stops')
    stops_full = pd.read_csv(os.path.join(GTFSDIR, 'stops.txt'))
    stops_full.stop_id = stops_full.stop_id.astype(str)
    stops = stops_full[stops_full.stop_id.isin(stop_ids)].copy()

    # Now add the stopareas (stations)
    stopareas = stops.parent_station.unique()
    stops = stops.append(stops_full[stops_full.stop_id.isin(stopareas)].copy())

    stops.zone_id = stops.zone_id.str.replace('IFF:', '').str.upper()
    stops.stop_code = stops.stop_code.str.upper()
    stops = stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'parent_station',
                   'platform_code', 'stop_code', 'zone_id']]

    stops.loc[stops['zone_id'].isnull(), 'zone_id'] = stops['stop_code']
    stops.loc[stops['stop_code'].isnull(), 'stop_code'] = stops['zone_id']

    stops.to_csv(os.path.join(OUTPUTDIR, 'stops.txt'), index=False)

    print('Done!')
