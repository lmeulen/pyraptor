# lRaptor
Work in progress.

Project to implement a Raptor implementation in Python. Source data is GTFS.

Two applications:

- ExtractOperators.py - Extract the time table information for one operator from a GTFS dataset
- lRaptor.py - Perform the RAPTOR analysis

Example usage: 

`python ExtractOperators.py NS`

`python lRaptor.py --i gtfs-extracted --s "Arnhem Zuid" --e "Oosterbeek" --d "08:30:00" --r 1 --c True`


The original implementation is naive and expensive. To measure the results op optimalisations the number of 
times a possible new arrival time is checked (k=2), is counted.

| Version | Loops k=1 | Loops k=2|
|---|---|---|
|1.0| 3.855 | 174.521|
|filter trips checked before | 3.855|108.818 |
|limit journey duration to 6h |1.811 | 41.457 |
|limit journey to 1h from transfer time | 316 | 10.974 |
| only add transfers on transfer stations | 316 | 9.948 |
| filter trips in traverse trips | 316 | 4.279

Together with the other performance optimalisations (numerical indexes on dataframes, replace dataframes with
numpy arrays, loop optimalisations, ...) the execution time of the algorithm is reduced from
~90 seconds to ~1.5 seconds (intel i5, 8GB RAM).

Due to the filtering on trips checked in a previous round, the following scenario is no longer possible:

- Sprinter A - B
- Intercity B - C
- Sprinter B - D

when the sprinter lin from A to B also extends to D. E.g. Nijmegen Lent to Gilze-Rijen in the Netherlands.
At this moment, these  journey advices are not given in practice so this filtering is kept.


# Code structure

The core of the application is the `perform_lRaptor(..)` method. Before it is called, the GTFS data is read and parerd. 
```
if __name__ == "__main__":
    args = parse_arguments()
    read_timetable(...)
    optimize_timetable()
    traveltimes, final_dest, legs = perform_lraptor(...)
    journey = reconstruct_journey(final_dest, legs)
    print_journey(journey, time_table, args.departure)
```
After performing the analysis, the journey is reconstructed and printed. The journey needs reconstruciton 
since it is not build during analysis. For performance reasons, only the last
leg to each reached destination is kept and by traversing these backwards the route can be
reconstructed.
The `perform_lRaptor(..)` method consists of the following steps:
```
def perform_lraptor(departure_name, arrival_name, departure_time, iterations):

    (from_stops, to_stops, dep_secs) = determine_parameters(...)

    # initialize lookup with start node taking 0 seconds to reach
    k_results = {}
    numberstops = max(timetable.stops.index)+1
    travel_times = np.full(shape=numberstops, fill_value=T24H, dtype=np.dtype(np.int32))
    last_leg = np.full(shape=(numberstops, 2), fill_value=(-1, 0), dtype=np.dtype(np.int32, np.int32))
    new_stops = tripfilter = []
    # Filter timetable stop times, keep only coming 6 hours
    mask = timetable.stop_times.departure_time.between(dep_secs, dep_secs + T6H)
    timetable.stop_times_filtered = timetable.stop_times[mask].copy()

    for from_stop in from_stops:
        travel_times[from_stop] = 0
        last_leg[from_stop] = (0, 0)
        new_stops.append(from_stop)

    for k in [1,2,..]:

        new_stops_travel = traverse_trips(new_stops, travel_times, last_leg, dep_secs, tripfilter)

        new_stops_transfer = add_transfer_time(new_stops_travel, travel_times, last_leg)

        new_stops = new_stops_travel + new_stops_transfer
        k_results[k] = reached_stops
        # filter trips from stop times, will not be evaluated again
        mask = ~timetable.stop_times_filtered.trip_id.isin(filter_trips)
        timetable.stop_times_filtered = timetable.stop_times_filtered[mask]

    dest_id = final_destination(to_stops, reached_stops)
```
One calcalation round consists of a `traverse_trips(...)` and a `add_transfer_time(..)` combination. The first 
calculates all reachable stops by train, given the already reached stops (starts with departure station). The
latter adds transfer time to all other platforms of the reached stations. After this, handled trips are removed
from the trips that can be evaluated since it cannot impse an improvement anymore.

The algorithm starts by finding all platforms for the departure station and adding these to the reached
stops. This enables departure in alle directions from a station and we do not want walking time between
platform at the origin.

### Add transfer time between platforms
For a given set of stops (`stops`) the station is determined for this stop and transfer time is added
for all other platforms at this station. This is only done for stations where a transfer to another route is
possible. 
```
def add_transfer_time(stops, time_to_stops, last_leg):
    new_stops = []

    # add in transfers to other platforms
    for stop in ids:
        stopdata = timetable.stops[timetable.stops.index == stop].iloc[0]
        stoparea = stopdata['parent_station']

        if stopdata['transfer_station']:
            # only update if currently inaccessible or faster than currrent option
            # for arrive_stop_id in timetable.stops[timetable.stops.parent_station == stoparea]['stop_id'].values:
            for arrive_stop_id in timetable.station2stops[timetable.station2stops.index == stoparea]['stop_id'].values:
                # time to reach new nearby stops is the transfer cost plus arrival at last stop
                time_sofar = traveltime_stops[stop]
                arrive_time_adjusted = time_sofar + get_transfer_time(stop, arrive_stop_id, time_sofar, 0)
                old_value = traveltime_stops[arrive_stop_id]
                if arrive_time_adjusted < old_value:
                    last_leg[arrive_stop_id] = (0, stop)
                    traveltime_stops[arrive_stop_id] = arrive_time_adjusted
                    new_stops.append(arrive_stop_id)

    return new_stops

```
### Final destination
The algorithm ends with a call to `final_destination(..)` whch ensures the stop with the shortest traveltime for
the departure station is returned. This is to prevent adding walk time at the end of the journey which is
unncessary. It returns the smallest distance for ID's that are in to_ids.

```
def final_destination(to_ids, reached_ids):
    final_id = 0
    distance = 999999
    for to_id in to_ids:
        if to_id in reached_ids:
            if reached_ids[to_id] < distance:
                distance = reached_ids[to_id]
                final_id = to_id
    return final_id

```

Remember that the number of stop_ids is determined by the number of platforms at the destination station. 

# Data structure

For the calculations a GTFS file is read. Some additional preparation is performed so it can be used optimal.

```
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
  ```

## agencies
Not used.
## routes
Not used

## trips
Overview of all trips in the network

| field | type | description |
| --- | --- | --- |
|trip_id          |   int64 | ID of tthe trip
|trip_short_name  |   int32 | Shortname (e.g. 8178).

## stop_times
All stop times in the network. REfers to the assicated stoplocation and trip.

| field | type | description |
| --- | --- | --- |
|index                |    int32 | Stop location ID (stop_id)
|trip_id              |    int64 | ID of the associated trip
|stop_sequence        |    int64 | Stop sequence along the line (NB not consecutive  numbers for intercity lines
|arrival_time         |    int64 | Arrival time at the stop location
|departure_time       |    int64 | Departure time from the stop location

## stops
Overview of all stoplocations in the network. A stoplocaiton is a platform at a station.

| field | type | description |
| --- | --- | --- |
| index           |     int32 | ID of the stoplocation (platform at a station) (stop_id)
| stop_name       |    object | Name of the station where the stop location is located 
| parent_station  |    object | Parent station, ID
| platform_code   |    object | Name of the platform of the stop location
| transfer_Station  |  bool   | True, if it is a transferstation 

## calendar
Not used

## stop_times_filtered
A subset of the original stop_times. Filtered to contain only the coming 6 hours starting at the departure time of the trave lrequest. Implemented to speed up retrieval of possible trips.  

| field | type | description |
| --- | --- | --- |
|index                |    int32 | Stop location ID (stop_id)
|trip_id              |    int64 | ID of the associated trip
|stop_sequence        |    int64 | Stop sequence along the line (NB not consecutive  numbers for intercity lines
|arrival_time         |    int64 | Arrival time at the stop location
|departure_time       |    int64 | Departure time from the stop location

## station2stops
A lookup table containg all stations and their asociated stops

| field | type | description |
| --- | --- | --- |
| index   | int32 | ID of the station
| stop_id | int32 | ID of a platform located at this station. One row per platform

## stop_times_for_trips

Faster lookup of arrival and dperature times for a stop of a trip

| field | type | description |
| --- | --- | --- |
| index           |  int64 | Trip ID (trip_id)
| stop_sequence   |  int64 | Stop sequency for the trip
| stop_id         |  int32 | STop ID for the stop location
| arrival_time    |  int64 | Arrival time
| departure_time  |  int64 | Departure time

## transfers

Lookup tabel showing if a station is a transfer station.
A station with more than two next stops is a transfer station

| field | type | description |
| --- | --- | --- |
| index             |  int32 | Station ID
| transfer_Station  |   bool  | True, if it is a transferstation 
