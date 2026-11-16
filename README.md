# TerraTwin

Team Astrallis · NASA Space Apps Challenge · Santiago 2026
Challenge: *Identify Earth Locations That Analog the Permanent Moon Base Locations and Mars.*

TerraTwin compares regions of Mars and the Moon with Earth sites documented as possible
analogs, using sourced characteristics, and searches Earth for new zones with similar topography.

## What it does
- **Explorer:** profile of a reference region (Jezero, Gale, Gusev, Marius Hills) and a
  ranking of 10 documented Earth analogs.
- **Map:** location of the analogs on Earth.
- **Analysis:** criterion-by-criterion comparison, measured topography (NASADEM) and
  estimated climate (NASA POWER).
- **Discovery:** compares slope and relief measured on Mars (MOLA) or the Moon (LOLA) with
  Earth terrain (NASADEM) at the same scale (~470 m per pixel) and lists new candidate zones.
- **Reports:** downloadable summaries with parameters, limitations and sources.

## Data sources
- NASADEM Merged DEM Global 1 arc second V001 (NASA LP DAAC, via Earthdata)
- MOLA global DEM mosaic, 463 m (Mars Global Surveyor; USGS Astrogeology)
- LOLA global DEM mosaic, 118 m (Lunar Reconnaissance Orbiter; USGS Astrogeology)
- NASA POWER climatology (MERRA-2 reanalysis)
- Team database of regions and analogs (`data/TerraTwin_limpio.xlsx`), built from the
  literature listed in its sheets

## Install and run
```
pip install -r requirements.txt
streamlit run app.py
```
Discovery reads MOLA and LOLA over the internet, so it needs a connection.

## NASADEM tiles (not included in the repository)
Download each tile from https://search.earthdata.nasa.gov (search "NASADEM Merged DEM
Global 1 arc second V001", Spatial → Point, one granule), save the `.zip` in
`data/downloaded/`, then run `python procesar_tesela.py n18w072` (change the tile name).
Tiles used: S25W070, N18W072, N18W071, N19E076, N19W156, N29W014.

## Limitations
- The similarity index is a measure defined by our algorithm (criteria met out of the
  comparable ones). It is not a probability or proof of a validated analog.
- "No data" means not documented in our database, not absent.
- The ranking covers 10 documented analogs; it is not a global search.
- Discovery compares only slope and relief, not composition, minerals or water. With flat
  references almost any plain matches.
- Tolerances and thresholds are team parameters, not scientific values.
- Part of the validation is circular: analogs were chosen for their relationship to Mars
  and the Moon.
- NASADEM covers 60° N to 56° S: McMurdo, Haughton, Fagradalsfjall and Holuhraun have no
  topographic data.
- Climate is an estimate from a coarse reanalysis (tens of km).
- Marius Hills coordinates are approximate.