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

`python pyraptor/gtfs/timetable.py -d "20210223" -a NS`

### 2. Run queries on timetable

`python pyraptor/query.py -i output/optimized_timetable -or "Arnhem Zuid" -d "Oosterbeek" -t "08:30:00"`

`python pyraptor/range_query.py -i output/optimized_timetable -or "Arnhem Zuid" -d "Oosterbeek" -st "08:00:00" -et "08:30:00"`

# References

[Round-Based Public Transit Routing](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf), Microsoft.com, Daniel Delling et al

[Raptor, another journey planning algorithm](https://ljn.io/posts/raptor-journey-planning-algorithm), Linus Norton

[Dutch GTFS feed](http://transitfeeds.com/p/ov/814), Transit Feeds
