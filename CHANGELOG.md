# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased]


## [0.0.6] - 2020-05-05
### Changed
- Updated Garmin [activity
  type](https://github.com/garmin-data/garmdown/issues/3) mapping thanks to
  `nantasquad`.  "Garmin has added extra types, most of them are not
  mapped. When using my edge130 for tracking it creates an activity with
  'road_biking' as type and the import doesn't know about this. To fix this I
  have to edit my activity type to change it to 'cycling' so the import works"


## [0.0.5] - 2020-04-24
### Changed
- Upgrade to ``zensols.util``.


## [0.0.4] - 2020-03-02
### Changed
- Robo browser dependency is locked down to the specific version that keeps the
  `chached_property` object to fix [install
  issue](https://github.com/garmin-data/garmdown/issues/1).


## [0.0.3] - 2020-01-21
### Changed
- Stationary sports use `duration` rather than `moving duration`.


## [0.0.2] - 2018-11-02
### Added
- Initial version


[Unreleased]: https://github.com/garmin-data/garmdown/compare/v0.0.6...HEAD
[0.0.6]: https://github.com/garmin-data/garmdown/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/garmin-data/garmdown/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/garmin-data/garmdown/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/garmin-data/garmdown/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/garmin-data/garmdown/compare/v0.0.1...v0.0.2
