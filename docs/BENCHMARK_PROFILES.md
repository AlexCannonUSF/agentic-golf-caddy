# Benchmark Profiles

These benchmark profiles were added so the app can switch between publicly sourced distance models instead of only using the four synthetic defaults.

## Included profiles

- `benchmark_shotscope_0hcp_male.json`
- `benchmark_shotscope_5hcp_male.json`
- `benchmark_shotscope_10hcp_male.json`
- `benchmark_shotscope_15hcp_male.json`
- `benchmark_shotscope_20hcp_male.json`
- `benchmark_shotscope_25hcp_male.json`
- `benchmark_trackman_pga_tour_2024.json`
- `benchmark_trackman_lpga_tour_2024.json`

## Sources

### Shot Scope handicap benchmarks

Source used: Golf Monthly article `How Far Do Average Golfers Actually Hit It?` by Elliott Heath, last updated 2025-03-27.

The article explicitly says the table comes from Shot Scope `Performance Average` data and provides total distances by handicap category for:

- Driver
- 3-wood
- Hybrid
- 4-iron through 9-iron
- PW, GW, SW, LW

Implementation note:

- The source table labels one long club as `Hybrid`.
- Inside the app, that value is stored as `4-hybrid` so it fits the existing club naming scheme.
- No extra `5-wood` value was invented for these Shot Scope profiles.
- A few source rows are not perfectly monotonic, especially in the highest-handicap wedge section. Those values were kept as published so the profiles stay faithful to the public dataset.

### TrackMan tour averages

Primary source: TrackMan `Trackman Tour Averages`, published 2024-05-02, with downloadable PGA and LPGA tour-average assets.

Convenient text table source used for profile entry: Golf Monthly articles built from the 2024 TrackMan data tables.

Included tour profiles use the published carry distances for:

- Driver
- 3-wood
- 5-wood
- Hybrid
- 4-iron through PW for LPGA
- 3-iron through PW for PGA

Implementation note:

- The source table labels one long club as `Hybrid`.
- Inside the app, that value is stored as `4-hybrid`.
- No extra wedges were inferred for the tour profiles beyond what was in the published table.

## Why these are useful

These benchmark profiles let you test the caddie against:

- elite male tour distance windows
- elite female tour distance windows
- six handicap-based amateur distance models

That gives you a more realistic set of selectable player types for demos, screenshots, class checkpoints, and evaluation runs.
