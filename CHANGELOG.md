# Changelog

<!--next-version-placeholder-->

## v1.3.9 (2022-07-22)
### Fix
* Raptor break for loop if improvements = 0 ([#43](https://github.com/lmeulen/pyraptor/issues/43)) ([`de68e03`](https://github.com/lmeulen/pyraptor/commit/de68e034aefd643d8086e62d9ddea1ffafa958c1))

## v1.3.8 (2022-05-19)
### Fix
* Remove duplicates in range_mcrapter ([`88ed285`](https://github.com/lmeulen/pyraptor/commit/88ed285bf01796f2cd81bb79fb5e14ca6cbd565f))

## v1.3.7 (2022-03-26)
### Fix
* Some performance tweaks ([#38](https://github.com/lmeulen/pyraptor/issues/38)) ([`0b08bad`](https://github.com/lmeulen/pyraptor/commit/0b08bad6066c7be6d27e9774d57d09b0dca49f62))

## v1.3.6 (2022-03-24)
### Fix
* Repr from TripStoptimes ([`221b605`](https://github.com/lmeulen/pyraptor/commit/221b60505df339c833392d844dff4dae917b4532))
* Fare as float ([`52a6942`](https://github.com/lmeulen/pyraptor/commit/52a6942875e7306542dc415d9ced280c58a36c94))

## v1.3.5 (2022-03-23)
### Fix
* Assert in add trip stoptimes only if finite arrival or departure time ([`7363c7f`](https://github.com/lmeulen/pyraptor/commit/7363c7f9f3bfe3ad3334d08368dc3db09c2c2cbe))

## v1.3.4 (2022-03-14)
### Fix
* Performance update rMcRaptor ([#34](https://github.com/lmeulen/pyraptor/issues/34)) ([`c881f45`](https://github.com/lmeulen/pyraptor/commit/c881f4586d6c782ad803f8a93590f788001809c9))

## v1.3.3 (2022-03-11)
### Fix
* Updated earliest trip to look at depature time ([#33](https://github.com/lmeulen/pyraptor/issues/33)) ([`788dd8c`](https://github.com/lmeulen/pyraptor/commit/788dd8c04e73046519728ddee0d6cf31c38048c8))

## v1.3.2 (2022-02-22)
### Fix
* Do not use very slow deepcopy in journey reconstruction ([#30](https://github.com/lmeulen/pyraptor/issues/30)) ([`a836886`](https://github.com/lmeulen/pyraptor/commit/a8368864a8022adcaae56d627cb68f0973a44608))

## v1.3.1 (2022-02-22)
### Fix
* Domination bug in rRaptor and too low LARGE_NUMBER when working with unix seconds ([#29](https://github.com/lmeulen/pyraptor/issues/29)) ([`ec23552`](https://github.com/lmeulen/pyraptor/commit/ec23552653eb7faa5d5e7f986068f72489c8afe4))

## v1.3.0 (2022-02-17)
### Feature
* Improve formatting and trigger minor release ([#26](https://github.com/lmeulen/pyraptor/issues/26)) ([`b8d64cd`](https://github.com/lmeulen/pyraptor/commit/b8d64cdd8d9f0c6b0bd2b141dc4f2e2ce2e7d8cd))

## v1.2.0 (2022-02-15)
### Feature
* Add Transfers to timetable ([#23](https://github.com/lmeulen/pyraptor/issues/23)) ([`67dfa53`](https://github.com/lmeulen/pyraptor/commit/67dfa5373ccb2801fe22ba0429d1557f71b10d8d))

## v1.1.0 (2022-02-14)
### Feature
* Add range query for McRaptor ([#22](https://github.com/lmeulen/pyraptor/issues/22)) ([`d9ca1de`](https://github.com/lmeulen/pyraptor/commit/d9ca1de8533780abeaede2c300031284626d1084))

## v1.0.2 (2022-02-13)
### Fix
* Remove invalid journeys ([`c40659e`](https://github.com/lmeulen/pyraptor/commit/c40659e932edd901ae9a9684012578d1d6052de3))

## v1.0.1 (2022-02-13)
### Fix
* Set Label and Bag to frozen to prevent pointer errors ([#21](https://github.com/lmeulen/pyraptor/issues/21)) ([`44a34a8`](https://github.com/lmeulen/pyraptor/commit/44a34a886cefc0b00fa6cf9168ee89ae3ae68589))

## v1.0.0 (2022-02-11)
### Feature
* Add McRAPTOR and align RAPTOR with paper ([#20](https://github.com/lmeulen/pyraptor/issues/20)) ([`591d91d`](https://github.com/lmeulen/pyraptor/commit/591d91d778574ee155dda8945a8473e69a1ffe77))

### Breaking
* Add McRAPTOR and align RAPTOR with paper ([#20](https://github.com/lmeulen/pyraptor/issues/20)) ([`591d91d`](https://github.com/lmeulen/pyraptor/commit/591d91d778574ee155dda8945a8473e69a1ffe77))

## v0.3.0 (2022-01-25)
### Feature
* Trigger release ([#18](https://github.com/lmeulen/pyraptor/issues/18)) ([`7f06d32`](https://github.com/lmeulen/pyraptor/commit/7f06d326b6a1903792742356a52bed9150a14ba5))

## v0.2.2 (2022-01-14)
### Fix
* Lock dependencies ([#15](https://github.com/lmeulen/pyraptor/issues/15)) ([`24c7a76`](https://github.com/lmeulen/pyraptor/commit/24c7a760cfef381234273619305992287f6bba29))

## v0.2.1 (2021-10-18)
### Fix
* Add extra attributes to pyproject.toml for publishing on PyPi ([#13](https://github.com/lmeulen/pyraptor/issues/13)) ([`112c487`](https://github.com/lmeulen/pyraptor/commit/112c487da984f5eff57dacb0231a6eb654989da3))

## v0.2.0 (2021-10-13)
### Feature
* Release to PyPi ([#12](https://github.com/lmeulen/pyraptor/issues/12)) ([`d6b1911`](https://github.com/lmeulen/pyraptor/commit/d6b1911f39d32386dfdf3ef471ec888ef7f1b512))

## v0.1.0 (2021-10-12)
### Feature
* Publish release to Github via CI ([#8](https://github.com/lmeulen/pyraptor/issues/8)) ([`de38b04`](https://github.com/lmeulen/pyraptor/commit/de38b04614e8836088400da7005a23ed41b90cd5))
