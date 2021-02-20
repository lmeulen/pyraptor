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

Due to the filtering om trips checked in a previous round, the following scenario is no longer possible:

- Sprinter A - B
- Intercity B - C
- Sprinter B - D

when the sprinter lin from A to B also extends to D. E.g. Nijmegen Lent to Gilze-Rijen in the Netherlands.
At this moment, these  journey advices are not given in practice so this filtering is kept.


# Data structure

For the calculations a GTFS file is read. Some additional preparation is performed so it an be used optimal.

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
|index                |    int32 | Stop location ID 
|trip_id              |    int64 | ID of the associated trip
|stop_sequence        |    int64 | Stop sequence along the line (NB not consecutive  numbers for intercity lines
|stop_id              |    int32 | Stop location ID 
|arrival_time         |    int64 | Arrival time at the stop location
|departure_time       |    int64 | Departure time from the stop location

## stops
Overview of all stoplocations in the network. A stoplocaiton is a platform at a station.

| field | type | description |
| --- | --- | --- |
| index           |     int32 | ID of the stoplocaiton (platform at a station)
| stop_id         |     int32 | ID of the stoplocaiton (platform at a station)
| stop_name       |    object | Name of the station where the stop location is located 
| parent_station  |    object | Parent station, station
| platform_code   |    object | Name of the platform of the stop location
| transfer_Station  |  bool  | True, if it is a transferstation 

## calendar
Not used

## stop_times_filtered
A subset of the original stop_times. Filtered to contain only the coming 6 hours starting at the departure time of the trave lrequest. Implemented to speed up retrieval of possible trips.  

| field | type | description |
| --- | --- | --- |
|index                |    int32 | Stop location ID
|trip_id              |    int64 | ID of the associated trip
|stop_sequence        |    int64 | Stop sequence along the line (NB not consecutive  numbers for intercity lines
|stop_id              |    int32 | Stop location ID 
|arrival_time         |    int64 | Arrival time at the stop location
|departure_time       |    int64 | Departure time from the stop location

## station2stops
A lookup table containg all stations (stoparea's) and their asociated stops

| field | type | description |
| --- | --- | --- |
| index | str | ID of the station (stoparea:XXXXX)
| stop_id | int32 | ID of a platform located at this station. One row per platform

## stop_times_for_trips

Faster lookup of arrival and dperature times for a stop of a trip

| field | type | description |
| --- | --- | --- |
| index           |  int64 | Trip ID
| trip_id         |  int64 | Trip ID 
| stop_sequence   |  int64 | Stop sequency for the trip
| stop_id         |  int32 | STop ID for the stop location
| arrival_time    |  int64 | Arrival time
| departure_time  |  int64 | Departure time

## transfers

Lookup tabel showing if a station is a transfer station.
A station with more than two next stops is a transfer station

| field | type | description |
| --- | --- | --- |
| index             |  int64 | STation ID
| transfer_Station  |  bool  | True, if it is a transferstation 
