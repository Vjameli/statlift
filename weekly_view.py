import datetime as dt
from typing import Dict

import pandas as pd
import streamlit as st


def _get_week_label(monday: dt.date) -> str:
    """Returns a human-readable label for a week starting on the given Monday."""
    sunday = monday + dt.timedelta(days=6)
    if monday.month == sunday.month:
        return f"{monday.strftime('%b %d')} - {sunday.strftime('%d, %Y')}"
    if monday.year == sunday.year:
        return f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}"
    return f"{monday.strftime('%b %d, %Y')} - {sunday.strftime('%b %d, %Y')}"


def _get_weeks(data: pd.DataFrame, date_col: str) -> list:
    """Returns a list of (monday_date, label) tuples for all weeks in the data,
    most recent first."""
    dates = data[date_col].unique()
    mondays = set()
    for d in dates:
        if isinstance(d, dt.datetime):
            d = d.date()
        monday = d - dt.timedelta(days=d.weekday())
        mondays.add(monday)
    mondays = sorted(mondays, reverse=True)
    return [(m, _get_week_label(m)) for m in mondays]


def _format_set_line(row: pd.Series, columns: Dict) -> str:
    """Formats a single set line like: 1) 135.0 lbs x 8 @ RPE 8"""
    set_order = row.get(columns.get("SET_ORDER", ""), "")
    weight = row[columns["WEIGHT"]]
    reps = row[columns["REPS"]]

    parts = []
    if set_order and str(set_order).strip():
        parts.append(f"**{int(float(set_order))})**")
    weight_str = f"{weight:.1f}" if weight else "0"
    parts.append(f"{weight_str} lbs x {int(reps)}")

    rpe_col = columns.get("RPE", "")
    if rpe_col and rpe_col in row.index:
        rpe_val = row[rpe_col]
        if rpe_val and str(rpe_val).strip():
            try:
                rpe_num = float(rpe_val)
                rpe_str = str(int(rpe_num)) if rpe_num == int(rpe_num) else str(rpe_num)
            except (ValueError, TypeError):
                rpe_str = str(rpe_val)
            parts.append(f"@ RPE {rpe_str}")

    volume = row.get("volume", 0)
    if volume:
        parts.append(f"(vol: {int(volume)})")

    return " ".join(parts)


def _render_day_card(
    col: st.delta_generator.DeltaGenerator,
    day: dt.date,
    day_data: pd.DataFrame,
    columns: Dict,
) -> None:
    """Renders a single day card in the given Streamlit column."""
    day_label = day.strftime("%a %b %d")

    with col:
        with st.container(border=True):
            if day_data.empty:
                st.markdown(f"**{day_label}**")
                st.markdown("*Rest*")
                return

            # Get workout info from first row
            workout_name = day_data.iloc[0][columns["WORKOUT_NAME"]]
            duration = day_data.iloc[0][columns["WORKOUT_DURATION"]]

            # Get workout time if datetime column exists
            time_str = ""
            if "datetime" in day_data.columns:
                workout_dt = day_data.iloc[0]["datetime"]
                if pd.notna(workout_dt):
                    time_str = f" ({workout_dt.strftime('%H:%M')})"

            st.markdown(f"**{day_label}**")
            st.markdown(f"**{workout_name}**{time_str}")

            # Workout notes (shown once at top)
            wn_col = columns.get("WORKOUT_NOTES", "")
            if wn_col and wn_col in day_data.columns:
                wn = day_data.iloc[0][wn_col]
                if wn and str(wn).strip():
                    st.caption(f"Note: {wn}")

            # Group by exercise
            exercises = day_data.groupby(
                columns["EXERCISE_NAME"], sort=False
            )

            for exercise_name, exercise_sets in exercises:
                st.markdown(f"**{exercise_name}**")
                for _, row in exercise_sets.iterrows():
                    st.markdown(
                        _format_set_line(row, columns),
                        help=None,
                    )
                # Exercise-level notes
                notes = exercise_sets[columns["NOTES"]].iloc[0]
                if notes and str(notes).strip():
                    st.caption(f"*{notes}*")

            # Footer with duration and total volume
            total_volume = int(day_data["volume"].sum())
            st.divider()
            st.caption(f"Duration: {duration} min | Volume: {total_volume:,} lbs")


def show_weekly_view(data: pd.DataFrame, columns: Dict) -> None:
    """Displays a weekly calendar view of workouts.

    Args:
        data: Cleaned workout dataframe from SePump.
        columns: Column name mapping dictionary.
    """
    if data.empty:
        st.info("No data available for weekly view.")
        return

    weeks = _get_weeks(data, columns["DATE"])
    if not weeks:
        st.info("No weeks found in the data.")
        return

    week_labels = [label for _, label in weeks]
    selected_label = st.selectbox(
        "**Select week**", week_labels, key="weekly_view_selector"
    )

    # Find the selected monday
    selected_monday = None
    for monday, label in weeks:
        if label == selected_label:
            selected_monday = monday
            break

    if selected_monday is None:
        return

    # Build 7 days Mon-Sun
    week_days = [selected_monday + dt.timedelta(days=i) for i in range(7)]
    day_columns = st.columns(7)

    for i, day in enumerate(week_days):
        day_data = data[data[columns["DATE"]] == day]
        _render_day_card(day_columns[i], day, day_data, columns)
