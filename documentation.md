# StatLift Documentation

## Overview

StatLift is a Streamlit-based web app for analyzing workout data exported from the Strong app. Users upload a CSV file and get visual analytics including overall metrics, per-exercise breakdowns, workout routine trends, and a weekly calendar view.

## Architecture

### Modules

| File | Purpose |
|------|---------|
| `statlift.py` | Main Streamlit app entry point. Orchestrates page layout and sections. |
| `sepump.py` | `SePump` class for loading, cleaning, and wrangling workout data. |
| `weekly_view.py` | Weekly calendar view rendering with workout cards for each day. |
| `session_state_handler.py` | Streamlit session state initialization and callback functions. |
| `streamlit_utils.py` | Small Streamlit utility helpers (e.g., vertical spacing). |
| `columns.json` | Column name definitions for different languages and platforms (EN/DE, iOS/Android). |

### Data Flow

1. User uploads a CSV exported from the Strong app.
2. `SePump.load_data()` reads the CSV into a pandas DataFrame.
3. `SePump.load_column_names()` auto-detects the CSV's language/platform variant via `columns.json`.
4. `SePump.clean_data()` performs data cleaning:
   - Deduplicates rows
   - Selects core columns (Date, Workout Name, Exercise Name, Weight, Reps, Duration, Notes)
   - Preserves optional columns if available (RPE, Set Order, Workout Notes)
   - Creates a `datetime` column (full timestamp) before converting Date to date-only
   - Propagates exercise notes from header rows (NaN weight/reps) to set rows before dropping them
   - Fills NaN values, converts weight from kg to lbs if needed
   - Generates `workout_uid`, `volume` columns
   - Converts duration to minutes
5. Cleaned data is stored in `st.session_state` for use across sections.

### App Sections

1. **Overall Metrics** — Aggregated stats across all workouts (count, volume, sets, reps, duration).
2. **Weekly View** — Calendar-style 7-column (Mon-Sun) layout showing workout cards per day with full exercise details (sets, weight, reps, RPE, notes, volume) or "Rest" for off days. Users select a week from a dropdown.
3. **Individual Exercise Metrics** — Per-exercise stats, exercise history grid (dark-themed cards showing each workout instance with a slider for how many to display), and trend charts with optional linear regression.
4. **Workout Routine Metrics** — Per-routine (e.g., "Push Day") aggregated stats and trend charts.

## Weekly View (`weekly_view.py`)

### Public API

- `show_weekly_view(data, columns, full_data=None)` — Renders the weekly calendar view section. Accepts optional `full_data` (unfiltered dataset) for computing PRs against all-time history.
- `show_exercise_history(exercise, data, columns, full_data=None, cards_per_row=6)` — Renders a grid of exercise instance cards showing each time the selected exercise was performed across different workouts, most recent first. Includes a slider to control how many instances to display.

### Internal Helpers

- `_get_week_label(monday: dt.date) -> str` — Formats a week label like "Mar 2 – Mar 8, 2026".
- `_get_weeks(data, date_col) -> list` — Returns `(monday, label)` tuples for all weeks in data, most recent first.
- `_compute_prs(full_data, columns) -> Dict[int, Set[str]]` — Computes personal records per set by iterating chronologically per exercise. Tracks weight, single-set volume, and estimated 1RM (Epley formula). Returns a dict mapping DataFrame index to a set of PR types (`'1RM'`, `'Vol.'`, `'Weight'`).
- `_find_sticky_notes(full_data, columns) -> Set[tuple]` — Identifies sticky/template exercise notes by finding `(exercise, note)` pairs appearing on more than one date.
- `_build_day_html(day, day_data, columns, pr_map, sticky_notes) -> str` — Builds the HTML string for a single day's dark-themed card.
- `_build_exercise_card_html(workout_name, exercise_name, exercise_rows, columns, pr_map, sticky_notes) -> str` — Builds the HTML string for a single exercise instance card within the exercise history grid.
- `_esc(text) -> str` — HTML-escapes a value for safe rendering.
- `_fmt_weight(weight) -> str` — Formats weight, dropping `.0` for whole numbers.

### Day Card Design

Cards use a dark theme (`#1a2332` background) rendered via `st.markdown` with custom HTML/CSS:

- **Header**: Workout name (bold white) + date/time (gray caption)
- **Workout notes**: Italic gray text below the date (one-time workout-level comments)
- **Exercise sections**: Name (bold, truncated with ellipsis) + "1RM" label (teal) when any set achieved a 1RM PR
- **Exercise notes**: Italic gray text below exercise name. Only one-time notes are shown; sticky/template notes (same text appearing on 2+ dates for the same exercise) are filtered out via `_find_sticky_notes()`
- **Set lines**: `set# weight lb × reps @ RPE` (left) with estimated 1RM (right, gray)
- **PR badges**: Teal rounded pills (`1RM`, `Vol.`, `Weight`) below sets that achieved personal records
- **Footer**: Duration (e.g. "1h 6m"), total volume, PR count (exercises with at least one PR)
- **Rest days**: Centered italic "Rest" label
- **Bodyweight exercises**: Shown as "BW × reps" when weight is 0

## Data Columns

### Core (always present after cleaning)

| Column Key | Description |
|-----------|-------------|
| `DATE` | Workout date (date-only after cleaning) |
| `WORKOUT_NAME` | Name of the workout routine |
| `EXERCISE_NAME` | Name of the exercise |
| `WEIGHT` | Weight used (converted to lbs) |
| `REPS` | Number of repetitions |
| `WORKOUT_DURATION` | Duration in minutes (converted from various formats) |
| `NOTES` | Exercise-level notes |

### Optional (preserved if available in CSV)

| Column Key | Description |
|-----------|-------------|
| `RPE` | Rate of Perceived Exertion |
| `SET_ORDER` | Order of the set within the exercise |
| `WORKOUT_NOTES` | Workout-level notes |

### Derived

| Column | Description |
|--------|-------------|
| `datetime` | Full datetime timestamp (preserved before date-only conversion) |
| `workout_uid` | Unique workout identifier (name + date + duration) |
| `volume` | Weight x Reps for each set |

## Running the App

```bash
cd statlift
uv run streamlit run statlift.py
```

Then upload a CSV file exported from the Strong app.
