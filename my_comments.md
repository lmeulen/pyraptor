# Deciphering RAPTOR:
(24/05/2022)

<br>

1. Looked at `class McRaptorAlgorithm` ([source code](https://github.com/yunusskeete/pyraptor/blob/42e5303a52e0ce09349fe98fc4968ed38be281b1/pyraptor/model/mcraptor.py#L19))
    1. Looked at implementation of [Bag](https://github.com/yunusskeete/pyraptor/blob/42e5303a52e0ce09349fe98fc4968ed38be281b1/pyraptor/model/mcraptor.py#L32)
    1. Looked at definition of [Bag](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L608)
    1. Looked at [pareto_set](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L631)
    1. Looked at definition of [pareto_set](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L776)
    1. Looked at [Label](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L786)
    1. Looked at definition of [Label](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L561)


[Label source code:](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L561)

```python
@dataclass(frozen=True)
class Label:
    """Label"""

    earliest_arrival_time: int
    fare: int  # total fare
    trip: Trip  # trip to take to obtain travel_time and fare
    from_stop: Stop  # stop to hop-on the trip
    n_trips: int = 0
    infinite: bool = False

    @property
    def criteria(self):
        """Criteria"""
        return [self.earliest_arrival_time, self.fare, self.n_trips]

    def update(self, earliest_arrival_time=None, fare_addition=None, from_stop=None):
        """Update earliest arrival time and add fare_addition to fare"""
        return copy(
            Label(
                earliest_arrival_time=earliest_arrival_time
                if earliest_arrival_time is not None
                else self.earliest_arrival_time,
                fare=self.fare + fare_addition
                if fare_addition is not None
                else self.fare,
                trip=self.trip,
                from_stop=from_stop if from_stop is not None else self.from_stop,
                n_trips=self.n_trips,
                infinite=self.infinite,
            )
        )

    def update_trip(self, trip: Trip, current_stop: Stop):
        """Update trip"""
        return copy(
            Label(
                earliest_arrival_time=self.earliest_arrival_time,
                fare=self.fare,
                trip=trip,
                from_stop=current_stop if self.trip != trip else self.from_stop,
                n_trips=self.n_trips + 1 if self.trip != trip else self.n_trips,
                infinite=self.infinite,
            )
        )
```

- We could add an occupancy attribute to the class [Label](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L561), which contains the (int) occupancy at stop `from_stop` (`p`) <br> (see commented implementation - 25/05/2022)
- We could add an occupancy attribute to the class [Trip](https://github.com/yunusskeete/pyraptor/blob/42e5303a52e0ce09349fe98fc4968ed38be281b1/pyraptor/model/structures.py#L246), which contains the (int) occupancy on trip, `trip` (`t(l)`)
- In the `criteria` attribute of the class [Label](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L561), we can either return a weighted combination of stop and trip occupancy (weighted by time spent?) or return both as separate criteria.


To Do:
1. (26/05/2022) Read through and understand all of the structures in [structures](/pyraptor/model/structures.py)
1. (26/05/2022) Run a few raptor queries and display these structures as debug outputs
1. (26/05/2022) Understand the FULL code workflow to go from query to route

Then:
1. Begin by creating a new branch in the [GitHub repository](https://github.com/yunusskeete/pyraptor) and implementing these new class attributes (assign all to `int: 0`)
1. Ensure that these are handled correctly by [McRaptorAlgorithm](https://github.com/yunusskeete/pyraptor/blob/42e5303a52e0ce09349fe98fc4968ed38be281b1/pyraptor/model/mcraptor.py#L19), [Bag](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L608), [pareto_set](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L776) and [Label](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L561).
1. Get accurate values for occupancy (stop) and occupancy (trip) from database ()Extend the [Timetable](https://github.com/yunusskeete/pyraptor/blob/42e5303a52e0ce09349fe98fc4968ed38be281b1/pyraptor/model/structures.py#L24) class.

<br>

<br>

<br>

<br>

<br>

---

<br>

<br>

<br>

<br>

<br>

# Occupancy
(25/05/2022)


To add occupancy to the rMcRaptor, we will need to update the `Timetable` class which is inherited into all Raptor instances.

```python
@dataclass
class Timetable:
    """Timetable data"""

    stations: Stations = None
    stops: Stops = None
    trips: Trips = None
    trip_stop_times: TripStopTimes = None
    routes: Routes = None
    transfers: Transfers = None

    def counts(self) -> None:
        """Print timetable counts"""
        logger.debug("Counts:")
        logger.debug("Stations   : {}", len(self.stations))
        logger.debug("Routes     : {}", len(self.routes))
        logger.debug("Trips      : {}", len(self.trips))
        logger.debug("Stops      : {}", len(self.stops))
        logger.debug("Stop Times : {}", len(self.trip_stop_times))
        logger.debug("Transfers  : {}", len(self.transfers))
```

(See [pyraptor/model/structures.py](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L24) for `Timetable` class implementation).

We will need to implement a `occupancy_stations` class and an `occupancy_trips` class.

These classes will need to be live updating or previously specified and from which, you should be able to search for the 'real-time' occupancy corresponding to a platform, or trip (could also include interchange, station etc.).

Using the `get_fare()` class ([definition](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/structures.py#L294), [implementation](https://github.com/yunusskeete/pyraptor/blob/bb43ab268ea08930e829c3c88c92871f951312c3/pyraptor/model/mcraptor.py#L138)), we should be able to implement occupancy depreferencing by adding a fare.

