# SetFlow

SetFlow is an end-to-end data pipeline that combines open music metadata and acoustic features to generate explainable, occasion-specific DJ-style set plans.

A user can request a set for an occasion such as a party, chill setting or warm-up, together with a target duration. SetFlow selects suitable tracks from its catalogue and orders them using transparent rules based on characteristics such as tempo, musical key and danceability.

The aim of the project is not to claim that there is one objectively perfect playlist or transition. Instead, SetFlow demonstrates how music data from multiple sources can be extracted, cleaned, validated, joined and used to make explainable recommendations.

## What I built and who for

I built SetFlow for an amateur DJ or party host who wants help creating a coherent set without manually comparing the musical characteristics of every available track.

The user provides:

- an occasion: `party`, `chill` or `warmup`
- a target set duration in minutes

For example:

```bash
py src/generate_set.py party 30