"""Data access object for timetable"""
import os
from pathlib import Path
from dataclasses import dataclass

from loguru import logger
import joblib

from pyraptor.util import mkdir_if_not_exists


@dataclass
class Timetable:
    """Timetable data"""

    stations = None
    stops = None
    trips = None
    trip_stop_times = None


def read_timetable(input_folder: str) -> Timetable:
    """
    Read the timetable data from the cache directory
    """

    if not os.path.exists(input_folder):
        raise IOError(
            "Optimized timetable not found. Run `pyraptor/gtfs/timetable.py` first to create timetable."
        )

    logger.debug("Using cached optimized datastructures")

    def load_joblib(name):
        logger.debug(f"Loading '{name}'")
        with open(Path(input_folder, f"{name}.pcl"), "rb") as handle:
            return joblib.load(handle)

    timetable = Timetable()

    timetable.stations = load_joblib("stations")
    timetable.stops = load_joblib("stops")
    timetable.trips = load_joblib("trips")
    timetable.trip_stop_times = load_joblib("trip_stop_times")

    return timetable


def write_timetable(output_folder: str, timetable: Timetable) -> None:
    """
    Write the timetable to output directory
    """

    def write_joblib(state, name):
        with open(Path(output_folder, f"{name}.pcl"), "wb") as handle:
            joblib.dump(state, handle)

    logger.info("Write PyRaptor timetable to output directory")

    mkdir_if_not_exists(output_folder)

    write_joblib(timetable.stations, "stations")
    write_joblib(timetable.stops, "stops")
    write_joblib(timetable.trips, "trips")
    write_joblib(timetable.trip_stop_times, "trip_stop_times")
