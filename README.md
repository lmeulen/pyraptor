# PyRaptor

Python implementation of RAPTOR using GTFS data.

Three applications:

- `pyraptor/gtfs/timetable.py` - Extract the time table information for one operator from a GTFS dataset and write it to an optimized format for querying with RAPTOR.
- `pyraptor/query.py` - Get the best journey for a given origin, destination and desired departure time using RAPTOR
- `pyraptor/range_query.py` - Get a list of the best journeys to all destinations for a given origin and desired departure time window using RAPTOR

## Installation

Install from PyPi using `pip install pyraptor` or clone this repository and install from source using pip.

## Example usage

### 1. Create timetable from GTFS

`python pyraptor/gtfs/timetable.py -d "20211201" -a NS`

### 2. Run (range) queries on timetable

`python pyraptor/query.py -i output/timetable -or "Arnhem Zuid" -d "Oosterbeek" -t "08:30:00"`

`python pyraptor/range_query.py -i output/timetable -or "Arnhem Zuid" -d "Oosterbeek" -st "08:00:00" -et "08:30:00"`

`python pyraptor/query_mcraptor.py -i output/timetable -or "Breda" -d "Amsterdam Centraal" -t "08:30:00" -r 2`

`python pyraptor/query_mcraptor.py -i output/timetable -or "Arnhem Zuid" -d "Oosterbeek" -t "08:30:00" -r 2`

# Notes

- The current version doesn't implement target pruning as we are interested in querying all targets at once and performance is sufficient already.

# References

[Round-Based Public Transit Routing](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf), Microsoft.com, Daniel Delling et al

[Raptor, another journey planning algorithm](https://ljn.io/posts/raptor-journey-planning-algorithm), Linus Norton

[Dutch GTFS feed](http://transitfeeds.com/p/ov/814), Transit Feeds
