# lRaptor
Work in progress.

Project to implement a Raptor implementation in Python. Source data is GTFS.

Two applications:

- ExtractOperators.py - Extract the time table information for one operator from a GTFS dataset
- iRaptor.py - Perform the RAPTOR analysis

Example usage:

python lRaptor.py --i gtfs-extracted --s "Arnhem Zuid" --e "Oosterbeek" --d "08:30:00" --r 1 --c True
