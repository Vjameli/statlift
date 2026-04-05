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
   - Fills NaN values, converts weight from kg to lbs if needed
   - Generates `workout_uid`, `volume` columns
   - Converts duration to minutes
5. Cleaned data is stored in `st.session_state` for use across sections.

### App Sections

1. **Overall Metrics** — Aggregated stats across all workouts (count, volume, sets, reps, duration).
2. **Weekly View** — Calendar-style 7-column (Mon-Sun) layout showing workout cards per day with full exercise details (sets, weight, reps, RPE, notes, volume) or "Rest" for off days. Users select a week from a dropdown.
3. **Individual Exercise Metrics** — Per-exercise stats and trend charts with optional linear regression.
4. **Workout Routine Metrics** — Per-routine (e.g., "Push Day") aggregated stats and trend charts.

## Weekly View (`weekly_view.py`)

### Public API

- `show_weekly_view(data: pd.DataFrame, columns: Dict) -> None` — Renders the weekly calendar view section.

### Internal Helpers

- `_get_week_label(monday: dt.date) -> str` — Formats a week label like "Mar 2 - Mar 8, 2026".
- `_get_weeks(data, date_col) -> list` — Returns `(monday, label)` tuples for all weeks in data, most recent first.
- `_format_set_line(row, columns) -> str` — Formats a single set: `1) 135.0 lbs x 8 @ RPE 8 (vol: 1080)`.
- `_render_day_card(col, day, day_data, columns) -> None` — Renders a single day's card with workout details or "Rest".

### Day Card Contents

- Day label (e.g., "Mon Mar 30")
- Workout name + time
- Workout-level notes (if present)
- Each exercise: name (bold), then each set showing set#, weight x reps, RPE, and volume
- Exercise-level notes (if present)
- Footer: duration (minutes) and total volume (lbs)

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
