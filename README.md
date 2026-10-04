# SetFlow

**Try SetFlow:** [Open the interactive SetFlow app](https://setflow-music.streamlit.app)

SetFlow is an end-to-end music data pipeline that creates DJ-style set plans based on a user's music preferences, occasion and requested duration.

For example, a user could request a 60-minute party set using pop, RnB and hip-hop. SetFlow filters its catalogue, selects suitable tracks and orders them using acoustic characteristics such as BPM, musical key and danceability.

The output is a suggested set plan rather than an audio mix, and the recommendation rules are designed to be transparent rather than represent an objectively perfect playlist or transition.

## About me

I have a Master's degree in Integrated Engineering, covering mechanical, electrical and electronic engineering. This multidisciplinary background developed my interest in solving technical problems using structured and analytical approaches, as well as programming and working with data.

I am interested in data engineering because it combines technical problem-solving with the challenge of transforming raw data into reliable and useful outputs. I am applying to The Information Lab because I want to develop these skills further through practical projects, continuous learning and exposure to varied real-world data problems.

I built SetFlow to explore this interest through an end-to-end data engineering project, from extracting and cleaning raw API data to data modelling, storage and creating a useful output.

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

A Streamlit interface also allows the user to choose the occasion, target duration and music pools without using command-line arguments. The interface displays the generated set and transition information and includes an option to include or exclude seasonal / Christmas music.

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
Data licence: https://musicbrainz.org/doc/About/Data_License

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

Documentation: https://acousticbrainz.org/data  
Data licence: CC0 – https://acousticbrainz.org/

AcousticBrainz stopped collecting new data in 2022, so the available dataset is historical and does not contain acoustic features for every MusicBrainz recording. This limits coverage, particularly for newer music.

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
Automated validation
      ↓
DuckDB
      ↓
Music-pool + occasion filtering
      ↓
Track selection and ordering
      ↓
SetFlow set plan / interface
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

`join_music_data.py` joins the cleaned datasets using MBID and checks for issues including missing acoustic features and differences between the two sources.

`validate_data.py` performs automated checks on the final joined data, including checks for missing and duplicate MBIDs, required fields, track durations, BPM values, scale values and music-pool assignments. The current validation script performs 17 checks and stops with a failure status if a check does not pass.

### 4. Store

The data is loaded into DuckDB using:

- `tracks` – one row per recording
- `track_music_pools` – the relationship between recordings and music pools

The music-pool relationship is stored separately because a recording can be associated with more than one pool.

The database is recreated from the processed data on each run so repeated runs produce a predictable state.

### 5. Generate the set

Tracks are filtered to the requested music pool(s). Each occasion has a target BPM range and danceability level, and tracks closer to these targets are prioritised.

Enough tracks are selected to approximately meet the requested duration. They are then ordered to favour smaller BPM changes, more compatible musical keys and smaller changes in danceability between consecutive songs.

The requested duration is treated as a target rather than an exact cutoff, allowing track suitability to remain the priority.

The interface also applies some additional user-facing rules. By default, obvious seasonal / Christmas tracks are filtered using title keywords unless the user chooses to include them. It also prevents the same apparent artist and song title from appearing twice in one generated set, while retaining the original MusicBrainz records in the underlying data.

The command-line result is saved as a text set plan in `outputs/`, while the Streamlit interface displays the generated set and transition information interactively.

## How to run it

### Requirements

- Python 3
- `requests`
- `duckdb`
- `streamlit`

Install the dependencies:

```bash
py -m pip install -r requirements.txt
```

No API key is required.

The committed raw responses can be processed from a clean clone using:

```bash
py src/run_pipeline.py
```

This runs the transformation, join, validation and DuckDB loading stages in sequence.

Generate a set from the command line with:

```bash
py src/generate_set.py <occasion> <minutes> <music_pool...>
```

Examples:

```bash
py src/generate_set.py party 30 pop rnb hip_hop_rap
py src/generate_set.py chill 30 indie_alternative rock
py src/generate_set.py party 30 country
py src/generate_set.py party 30 all
```

Generated command-line set plans are saved in `outputs/`.

To use the interactive interface:

```bash
py -m streamlit run src/app.py
```

## What I would do next

With more time I would:

- explore additional openly licensed audio-feature sources to improve coverage beyond the historical AcousticBrainz dataset, particularly for newer releases
- expand the catalogue beyond the current seed artists and add more music categories and niche styles
- improve how individual songs are categorised, rather than basing music pools mainly on the artist
- improve detection of remixes, edits, live recordings and other alternative versions, as well as recordings that represent the same underlying song despite having different MusicBrainz IDs
- improve contextual filtering beyond the current title-based seasonal / Christmas filter, so tracks can be matched more accurately to particular occasions and contexts
- investigate openly licensed data or audio-analysis methods for identifying song structure, such as intros, outros, choruses and drops, so SetFlow could suggest where within each track to start and end a transition
- use listening data, where available, to identify which parts of a song listeners engage with or commonly skip, and use this to improve transition suggestions
- explore listening patterns across different age groups to better tailor sets to different audiences
- explore an optional stricter duration mode so the final set can more closely match the requested duration while retaining the current suitability-first approach
- add more occasions and continue developing the user interface

## Where AI helped

I used AI as a development tool to help understand unfamiliar API structures, troubleshoot code and discuss approaches to data cleaning and modelling. I tested suggestions against the data and adapted them rather than using them unchanged. For example:

- I changed the cleaning logic after finding unrelated MusicBrainz search results, adding artist-credit validation.
- I changed the database design to separate `tracks` and `track_music_pools` rather than storing multiple pools in one field.
- I improved the alternative-version filter after testing showed that checking only the disambiguation field missed some remixes, while leaving more complex mix/edit filtering as a documented future improvement.