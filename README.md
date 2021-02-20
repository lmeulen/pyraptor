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
| only add transfers on transfer stations | 316 | 9948 |

Due to the filtering om trips checked in a previous round, the following scenario is no longer possible:

- Sprinter A - B
- Intercity B - C
- Sprinter B - D

when the sprinter lin from A to B also extends to D. E.g. Nijmegen Lent to Gilze-Rijen in the Netherlands.
At this moment, these  journey advices are not given in practice so this filtering is kept.
