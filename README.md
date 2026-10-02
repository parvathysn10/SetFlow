# SetFlow

SetFlow is an end-to-end music data pipeline that creates DJ-style set plans based on a user's music preferences, occasion and requested duration.

For example, a user could request a 60-minute party set using pop, R&B and hip-hop. SetFlow filters its catalogue, selects suitable tracks and orders them using acoustic characteristics such as BPM, musical key and danceability.

The output is a suggested set plan rather than an audio mix, and the recommendation rules are designed to be transparent rather than represent an objectively perfect playlist or transition.

## What I built and who for

I built SetFlow for an amateur DJ or party host who wants to create a coherent set without manually comparing the musical characteristics of a large number of tracks.

The user chooses:

- an occasion: `party`, `chill` or `warmup`
- a target duration in minutes
- one or more music pools, or `all`

The current prototype supports 12 music pools:

`pop`, `rnb`, `hip_hop_rap`, `dance_electronic`, `indie_alternative`, `rock`, `country`, `latin`, `funk_disco`, `reggae`, `metal` and `jazz`.

For example:

```bash
py src/generate_set.py party 60 pop rnb hip_hop_rap
```

SetFlow returns an ordered set with track information and an explanation of the suggested transitions.

## The data

SetFlow uses two open music data sources.

### MusicBrainz

MusicBrainz provides the core recording metadata, including:

- MusicBrainz Recording ID (MBID)
- track title
- artist credits
- recording duration
- disambiguation information

The development catalogue uses 23 seed artists across a range of musical styles. The API responses are paginated and the raw JSON is stored unchanged before transformation.

Documentation: https://musicbrainz.org/doc/MusicBrainz_API

### AcousticBrainz

AcousticBrainz provides previously extracted acoustic features for MusicBrainz recordings. SetFlow uses features including:

- BPM
- key and scale
- danceability
- loudness
- dynamic complexity
- onset rate
- acoustic duration

The two sources are joined using the MusicBrainz Recording ID.

Documentation: https://acousticbrainz.org/

AcousticBrainz does not contain data for every MusicBrainz recording, so incomplete acoustic coverage is a limitation of the current dataset.

## How it works

```text
MusicBrainz API
      ↓
Raw JSON
      ↓
Clean MusicBrainz catalogue
      ↓
AcousticBrainz enrichment
      ↓
Clean acoustic features
      ↓
Join using MBID
      ↓
DuckDB
      ↓
Music-pool + occasion filtering
      ↓
Track selection and ordering
      ↓
SetFlow set plan
```

### 1. Extract

`extract_catalogue.py` retrieves paginated MusicBrainz recording data and stores the raw responses before transformation.

`extract_acousticbrainz.py` then attempts to retrieve acoustic features for the available recording MBIDs. The extraction handles rate limits, retries and unavailable AcousticBrainz data.

### 2. Clean and transform

`transform_catalogue.py` converts the nested MusicBrainz responses into a consistent recording-level dataset.

The cleaning handles:

- duplicate and missing MBIDs
- missing and inconsistent durations
- artist credits
- unintended artist search results
- common alternative recording versions
- music-pool assignment

`transform_acousticbrainz.py` extracts the acoustic features needed by SetFlow into a consistent structure.

The music pools are broad prototype groupings rather than exact genres for every song, as individual artists and songs can span several styles.

### 3. Join and validate

`join_music_data.py` joins the cleaned datasets using MBID and checks for duplicate IDs, missing acoustic features, missing durations, duration differences between sources and missing music-pool assignments.

### 4. Store

The data is loaded into DuckDB using:

- `tracks` – one row per recording
- `track_music_pools` – the relationship between recordings and music pools

The music-pool relationship is stored separately because a recording can be associated with more than one pool.

The database is recreated from the processed data on each run so repeated runs produce a predictable state.

### 5. Generate the set

Tracks are filtered to the requested music pool(s). Each occasion has a target BPM range and danceability level, and tracks closer to these targets are prioritised.

Enough tracks are selected to approximately meet the requested duration. They are then ordered to favour smaller BPM changes, more compatible musical keys and smaller changes in danceability between consecutive songs.

The result is saved as a text set plan in `outputs/`.

## How to run it

### Requirements

- Python 3
- `requests`
- `duckdb`

Install the dependencies:

```bash
py -m pip install requests duckdb
```

No API key is required.

The committed raw responses can be processed from a clean clone using:

```bash
py src/transform_catalogue.py
py src/transform_acousticbrainz.py
py src/join_music_data.py
py src/load_duckdb.py
```

Generate a set with:

```bash
py src/generate_set.py <occasion> <minutes> <music_pool...>
```

Examples:

```bash
py src/generate_set.py party 30 pop rnb hip_hop_rap
py src/generate_set.py chill 30 indie_alternative rock
py src/generate_set.py party 30 country
py src/generate_set.py warmup 60 all
```

Generated set plans are saved in `outputs/`.

## What I would do next

With more time I would:

- expand the catalogue beyond the current seed artists and add more music categories and niche styles
- improve how individual songs are categorised, rather than basing music pools mainly on the artist
- improve detection of remixes, edits and other alternative versions
- use listening data, where available, to identify which parts of a song listeners engage with or commonly skip, and use this to improve transition suggestions
- explore listening patterns across different age groups to better tailor sets to different audiences
- improve track selection so the final set more closely matches the requested duration
- add more occasions and a simple user interface

## Where AI helped

I used AI as a development tool to help understand unfamiliar API structures, troubleshoot code and discuss approaches to data cleaning and modelling. I tested suggestions against the data and adapted them rather than using them unchanged. For example:

- I changed the cleaning logic after finding unrelated MusicBrainz search results, adding artist-credit validation.
- I changed the database design to separate `tracks` and `track_music_pools` rather than storing multiple pools in one field.
- I improved the alternative-version filter after testing showed that checking only the disambiguation field missed some remixes, while leaving more complex mix/edit filtering as a documented future improvement.