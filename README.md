# PyRaptor

Python implementation of RAPTOR and McRAPTOR using GTFS data. Tested on Dutch GTFS data.

This repository contains four applications:

1. `pyraptor/gtfs/timetable.py` - Extract the timetable information for one operator from a GTFS dataset and write it to an optimized format for querying with RAPTOR.
2. `pyraptor/query_raptor.py` - Get the best journey for a given origin, destination and desired departure time using RAPTOR
3. `pyraptor/query_range_raptor.py` - Get a list of the best journeys to all destinations for a given origin and desired departure time window using RAPTOR
4. `pyraptor/query_mcraptor.py` - Get a list of the Pareto-optimal journeys to all destinations for a given origin and a departure time using McRAPTOR
5. `pyraptor/query_range_mcraptor.py` - Get a list of Pareto-optimal journeys to all destinations for a given origin and a departure time window using McRAPTOR

## Installation

Install from PyPi using `pip install pyraptor` or clone this repository and install from source using pip.

## Example usage

### 1. Create timetable from GTFS

> `python pyraptor/gtfs/timetable.py -d "20211201" -a NS --icd`

### 2. Run (range) queries on timetable

Quering on the timetable to get the best journeys can be done using several implementations.

#### RAPTOR query

RAPTOR returns a single journey with the earliest arrival time given the query time.

**Examples**

> `python pyraptor/query_raptor.py -or "Arnhem Zuid" -d "Oosterbeek" -t "08:30:00"`

> `python pyraptor/query_raptor.py -or "Breda" -d "Amsterdam Centraal" -t "08:30:00"`

#### rRAPTOR query

rRAPTOR returns a set of best journeys with a given query time range.
Journeys that are dominated by other journeys in the time range are removed.

**Examples**
 
> `python pyraptor/query_range_raptor.py -or "Arnhem Zuid" -d "Oosterbeek" -st "08:00:00" -et "08:30:00"`

> `python pyraptor/query_range_raptor.py -or "Breda" -d "Amsterdam Centraal" -st "08:00:00" -et "08:30:00"`

#### McRaptor query

McRaptor returns a set of Pareto-optimal journeys given multiple criterions, i.e. earliest 
arrival time, fare and number of trips.

**Examples**

> `python pyraptor/query_mcraptor.py -or "Breda" -d "Amsterdam Centraal" -t "08:30:00"`

> `python pyraptor/query_mcraptor.py -or "Vlissingen" -d "Akkrum" -t "08:30:00"`

> `python pyraptor/query_mcraptor.py -or "Obdam" -d "Akkrum" -t "08:30:00" -r 7`

#### rMcRaptor query

Range version of McRaptor, i.e. it returns a set of Pareto-optimal journeys within a departure time window.

**Examples**

> `python pyraptor/query_range_mcraptor.py -or "Breda" -d "Amsterdam Centraal" -st "08:15:00" -et "08:30:00"`

> `python pyraptor/query_range_mcraptor.py -or "Vlissingen" -d "Akkrum" -st "08:15:00" -et "08:30:00"`

> `python pyraptor/query_range_mcraptor.py -or "Obdam" -d "Akkrum" -st "08:00:00" -et "09:00:00"`

# Notes

- The current version doesn't implement target pruning as we are interested in efficiently querying all targets/destinations after running RAPTOR algorithm.

# References

[Round-Based Public Transit Routing](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/01/raptor_alenex.pdf), Microsoft.com, Daniel Delling et al

[Raptor, another journey planning algorithm](https://ljn.io/posts/raptor-journey-planning-algorithm), Linus Norton

[Dutch GTFS feed](http://transitfeeds.com/p/ov/814), Transit Feeds
