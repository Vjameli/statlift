import datetime as dt
import html as html_mod
from typing import Dict, Optional, Set

import pandas as pd
import streamlit as st

CARD_CSS = """<style>
.wv-card {
    background: #1a2332;
    border-radius: 12px;
    padding: 14px 12px;
    color: #c8d0d8;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
    line-height: 1.5;
}
.wv-card .wv-title { font-weight: 700; color: #ffffff; font-size: 15px; margin-bottom: 2px; }
.wv-card .wv-date { color: #6b7b8b; font-size: 11px; margin-bottom: 4px; }
.wv-card .ex-section { border-top: 1px solid #283848; padding-top: 8px; margin-top: 8px; }
.wv-card .ex-hdr {
    display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;
}
.wv-card .ex-name {
    font-weight: 700; color: #ffffff; font-size: 13px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 78%;
}
.wv-card .ex-pr { color: #2ec4a5; font-weight: 600; font-size: 12px; white-space: nowrap; }
.wv-card .set-row {
    display: flex; justify-content: space-between; align-items: center;
    margin: 1px 0; font-size: 12px; color: #a0aab4;
}
.wv-card .set-1rm { font-size: 12px; color: #707a84; }
.wv-card .badges { margin: 3px 0 2px 0; line-height: 2; }
.wv-card .badge {
    background: #2a9d8f; color: #fff; border-radius: 10px;
    padding: 2px 8px; font-size: 10px; font-weight: 600;
    display: inline-block; margin-right: 3px;
}
.wv-card .wv-footer {
    border-top: 1px solid #283848; padding-top: 6px; margin-top: 10px;
    color: #6b7b8b; font-size: 11px; display: flex; gap: 14px;
}
.wv-card .rest-label {
    color: #6b7b8b; font-style: italic; text-align: center; padding: 20px 0; font-size: 14px;
}
.wv-day-hdr {
    text-align: center; font-weight: 700; font-size: 16px; margin-bottom: 8px;
}
</style>"""


def _get_week_label(monday: dt.date) -> str:
    """Returns a human-readable label for a week starting on the given Monday."""
    sunday = monday + dt.timedelta(days=6)
    if monday.month == sunday.month:
        return f"{monday.strftime('%b %d')} – {sunday.strftime('%d, %Y')}"
    if monday.year == sunday.year:
        return f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}"
    return f"{monday.strftime('%b %d, %Y')} – {sunday.strftime('%b %d, %Y')}"


def _get_weeks(data: pd.DataFrame, date_col: str) -> list:
    """Returns (monday_date, label) tuples for all weeks in the data, most recent first."""
    dates = data[date_col].unique()
    mondays = set()
    for d in dates:
        if isinstance(d, dt.datetime):
            d = d.date()
        monday = d - dt.timedelta(days=d.weekday())
        mondays.add(monday)
    mondays = sorted(mondays, reverse=True)
    return [(m, _get_week_label(m)) for m in mondays]


def _compute_prs(
    full_data: pd.DataFrame, columns: Dict
) -> Dict[int, Set[str]]:
    """Compute personal records for each set.

    Iterates chronologically per exercise. A set is a PR if it exceeds all
    previous values for that exercise in weight, single-set volume, or
    estimated 1RM (Epley formula).

    Returns:
        Dict mapping DataFrame index -> set of PR type strings
        ('1RM', 'Vol.', 'Weight').
    """
    data = full_data.sort_values("datetime")
    weight_col = columns["WEIGHT"]
    reps_col = columns["REPS"]

    pr_map: Dict[int, Set[str]] = {}

    for _, group in data.groupby(columns["EXERCISE_NAME"]):
        max_weight = 0.0
        max_volume = 0.0
        max_1rm = 0.0

        for idx, row in group.iterrows():
            weight = float(row[weight_col])
            reps = float(row[reps_col])
            volume = weight * reps
            est_1rm = weight * (1 + reps / 30) if reps > 0 else weight
            prs: Set[str] = set()

            if weight > 0:
                if weight > max_weight:
                    prs.add("Weight")
                if volume > max_volume:
                    prs.add("Vol.")
                if est_1rm > max_1rm:
                    prs.add("1RM")

                max_weight = max(max_weight, weight)
                max_volume = max(max_volume, volume)
                max_1rm = max(max_1rm, est_1rm)

            if prs:
                pr_map[idx] = prs

    return pr_map


def _esc(text) -> str:
    """HTML-escape a value."""
    return html_mod.escape(str(text))


def _fmt_weight(weight: float) -> str:
    """Format weight, dropping '.0' for whole numbers."""
    return str(int(weight)) if weight == int(weight) else f"{weight:.1f}"


def _build_day_html(
    day: dt.date,
    day_data: pd.DataFrame,
    columns: Dict,
    pr_map: Dict[int, Set[str]],
) -> str:
    """Build the HTML string for a single day card."""

    if day_data.empty:
        return '<div class="wv-card"><div class="rest-label">Rest</div></div>'

    # --- header ---
    workout_name = _esc(day_data.iloc[0][columns["WORKOUT_NAME"]])
    duration = int(day_data.iloc[0][columns["WORKOUT_DURATION"]])

    time_str = day.strftime("%a, %b ") + str(day.day) + day.strftime(", %Y")
    if "datetime" in day_data.columns:
        workout_dt = day_data.iloc[0]["datetime"]
        if pd.notna(workout_dt):
            time_str += f" at {workout_dt.strftime('%H:%M')}"

    html = [
        '<div class="wv-card">',
        f'<div class="wv-title">{workout_name}</div>',
        f'<div class="wv-date">{_esc(time_str)}</div>',
    ]

    # --- exercises ---
    pr_exercise_count = 0
    exercises = day_data.groupby(columns["EXERCISE_NAME"], sort=False)

    for exercise_name, exercise_sets in exercises:
        has_1rm_pr = any(
            "1RM" in pr_map.get(idx, set()) for idx in exercise_sets.index
        )
        if has_1rm_pr:
            pr_exercise_count += 1

        html.append('<div class="ex-section">')
        html.append('<div class="ex-hdr">')
        html.append(f'<span class="ex-name">{_esc(exercise_name)}</span>')
        if has_1rm_pr:
            html.append('<span class="ex-pr">1RM</span>')
        html.append("</div>")

        for idx, row in exercise_sets.iterrows():
            weight = float(row[columns["WEIGHT"]])
            reps = int(float(row[columns["REPS"]]))

            # set order
            so_col = columns.get("SET_ORDER", "")
            set_num = ""
            if so_col and so_col in row.index:
                so = row[so_col]
                if so and str(so).strip():
                    try:
                        set_num = str(int(float(so)))
                    except (ValueError, TypeError):
                        pass

            # RPE
            rpe_str = ""
            rpe_col = columns.get("RPE", "")
            if rpe_col and rpe_col in row.index:
                rpe_val = row[rpe_col]
                if rpe_val and str(rpe_val).strip():
                    try:
                        rpe_num = float(rpe_val)
                        rpe_fmt = (
                            str(int(rpe_num))
                            if rpe_num == int(rpe_num)
                            else str(rpe_num)
                        )
                        rpe_str = f" @ {rpe_fmt}"
                    except (ValueError, TypeError):
                        pass

            # set text (left side)
            if weight > 0:
                left = f"{set_num}&nbsp;&nbsp;{_fmt_weight(weight)} lb × {reps}{rpe_str}"
            else:
                left = f"{set_num}&nbsp;&nbsp;BW × {reps}{rpe_str}"

            # estimated 1RM (right side)
            right = ""
            if weight > 0 and reps > 0:
                right = str(int(round(weight * (1 + reps / 30))))

            html.append(
                f'<div class="set-row">'
                f"<span>{left}</span>"
                f'<span class="set-1rm">{right}</span>'
                f"</div>"
            )

            # PR badges
            set_prs = pr_map.get(idx, set())
            if set_prs:
                badges = "".join(
                    f'<span class="badge">{_esc(pr)}</span>'
                    for pr in ("1RM", "Vol.", "Weight")
                    if pr in set_prs
                )
                html.append(f'<div class="badges">{badges}</div>')

        html.append("</div>")  # ex-section

    # --- footer ---
    total_volume = int(day_data["volume"].sum())
    parts = [f"{duration}m", f"{total_volume:,} lb"]
    if pr_exercise_count > 0:
        suffix = "s" if pr_exercise_count != 1 else ""
        parts.append(f"{pr_exercise_count} PR{suffix}")

    html.append(
        '<div class="wv-footer">'
        + "&emsp;".join(parts)
        + "</div>"
    )
    html.append("</div>")  # wv-card
    return "\n".join(html)


def show_weekly_view(
    data: pd.DataFrame,
    columns: Dict,
    full_data: Optional[pd.DataFrame] = None,
) -> None:
    """Displays a weekly calendar view of workouts with PR badges.

    Args:
        data: Filtered workout dataframe.
        columns: Column name mapping dictionary.
        full_data: Full unfiltered dataset for PR computation. Uses data if None.
    """
    if data.empty:
        st.info("No data available for weekly view.")
        return

    st.markdown(CARD_CSS, unsafe_allow_html=True)

    weeks = _get_weeks(data, columns["DATE"])
    if not weeks:
        st.info("No weeks found in the data.")
        return

    week_labels = [label for _, label in weeks]
    selected_label = st.selectbox(
        "**Select week**", week_labels, key="weekly_view_selector"
    )

    selected_monday = None
    for monday, label in weeks:
        if label == selected_label:
            selected_monday = monday
            break
    if selected_monday is None:
        return

    # Compute PRs against full history
    pr_map = _compute_prs(full_data if full_data is not None else data, columns)

    # Render 7 day columns
    week_days = [selected_monday + dt.timedelta(days=i) for i in range(7)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_columns = st.columns(7)

    for i, day in enumerate(week_days):
        with day_columns[i]:
            st.markdown(
                f'<div class="wv-day-hdr">{day_labels[i]}</div>',
                unsafe_allow_html=True,
            )
            day_data = data[data[columns["DATE"]] == day]
            st.markdown(
                _build_day_html(day, day_data, columns, pr_map),
                unsafe_allow_html=True,
            )
