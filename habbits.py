
import streamlit as st
import streamlit.components.v1 as components
import calendar

from database import get_connection
from gamification import award_xp
from datetime import date, timedelta


# ==================================================
# STREAK CALCULATIONS
# ==================================================

def calculate_streak(habit_id, user_id):

    conn = get_connection()

    try:
        logs = conn.execute(
            """
            SELECT hl.log_date
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE hl.habit_id = ?
              AND h.user_id = ?
            ORDER BY hl.log_date ASC
            """,
            (habit_id, user_id)
        ).fetchall()

    finally:
        conn.close()

    completed_dates = sorted({
        date.fromisoformat(row[0])
        for row in logs
    })

    if not completed_dates:
        return 0, 0, 0

    total_checkins = len(completed_dates)

    longest_streak = 1
    current_run = 1

    for i in range(1, len(completed_dates)):

        difference = (
            completed_dates[i] - completed_dates[i - 1]
        ).days

        if difference == 1:
            current_run += 1
        else:
            current_run = 1

        longest_streak = max(longest_streak, current_run)

    today = date.today()
    yesterday = today - timedelta(days=1)

    if completed_dates[-1] not in [today, yesterday]:
        current_streak = 0

    else:
        current_streak = 1
        current_date = completed_dates[-1]

        for previous_date in reversed(completed_dates[:-1]):

            if (current_date - previous_date).days == 1:
                current_streak += 1
                current_date = previous_date
            else:
                break

    return current_streak, longest_streak, total_checkins


# ==================================================
# STREAK MILESTONES
# ==================================================

def get_streak_milestone(streak):

    milestones = [3, 7, 14, 30, 60, 100]

    achieved = [
        milestone
        for milestone in milestones
        if streak >= milestone
    ]

    upcoming = [
        milestone
        for milestone in milestones
        if streak < milestone
    ]

    latest_achievement = max(achieved) if achieved else 0
    next_milestone = min(upcoming) if upcoming else None

    return latest_achievement, next_milestone


# ==================================================
# DAILY HABIT REMINDERS
# ==================================================

def show_habit_reminders(habits, completed_habit_ids):

    pending_habits = [
        habit for habit in habits
        if habit[0] not in completed_habit_ids
    ]

    st.subheader("🔔 Daily Habit Reminders")

    if not pending_habits:

        st.success(
            "🎉 Amazing! You have completed all your habits today."
        )

        return

    st.warning(
        f"You have {len(pending_habits)} habit(s) remaining today."
    )

    for habit in pending_habits:

        habit_id, name, description, created_at = habit

        st.markdown(f"- 🔔 **{name}** — Not completed today")


# ==================================================
# DAILY STREAK CALENDAR
# ==================================================

def show_streak_calendar(habit_id, user_id, created_at):

    st.markdown("#### 📅 Daily Streak Calendar")

    selected_date = st.date_input(
        "Choose a month",
        value=date.today(),
        key=f"calendar_date_{habit_id}"
    )

    year = selected_date.year
    month = selected_date.month

    first_day = date(year, month, 1)

    last_day = date(
        year,
        month,
        calendar.monthrange(year, month)[1]
    )

    today = date.today()

    try:
        habit_start_date = date.fromisoformat(
            str(created_at)[:10]
        )
    except (ValueError, TypeError):
        habit_start_date = first_day

    conn = get_connection()

    try:
        logs = conn.execute(
            """
            SELECT hl.log_date
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE hl.habit_id = ?
              AND h.user_id = ?
              AND hl.log_date >= ?
              AND hl.log_date <= ?
            """,
            (
                habit_id,
                user_id,
                str(first_day),
                str(last_day)
            )
        ).fetchall()

    finally:
        conn.close()

    completed_dates = {
        date.fromisoformat(row[0])
        for row in logs
    }

    expected_days = sum(
        1
        for day in range(1, last_day.day + 1)
        if habit_start_date <= date(year, month, day) <= today
    )

    completed_count = len(completed_dates)

    missed_count = sum(
        1
        for day in range(1, last_day.day + 1)
        if (
            habit_start_date <= date(year, month, day) <= today
            and date(year, month, day) not in completed_dates
        )
    )

    consistency = (
        completed_count / expected_days * 100
        if expected_days > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Completed", completed_count)

    with col2:
        st.metric("Missed", missed_count)

    with col3:
        st.metric("Consistency", f"{consistency:.0f}%")

    st.markdown(
        """
        🟩 Completed &nbsp;&nbsp;
        ⬜ Missed &nbsp;&nbsp;
        🟦 Today &nbsp;&nbsp;
        ⚪ Future / Not started
        """
    )

    st.markdown(
        f"**{calendar.month_name[month]} {year}**"
    )

    month_weeks = calendar.monthcalendar(year, month)

    calendar_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 5px;
            background: transparent;
            font-family: Arial, sans-serif;
        }

        .habit-calendar {
            width: 100%;
            border-collapse: separate;
            border-spacing: 5px;
            table-layout: fixed;
        }

        .habit-calendar th {
            padding: 10px 2px;
            color: #9CA3AF;
            font-size: 13px;
            text-align: center;
        }

        .habit-calendar td {
            height: 48px;
            text-align: center;
            vertical-align: middle;
            border-radius: 9px;
            font-size: 14px;
            font-weight: bold;
        }
    </style>
    </head>

    <body>

    <table class="habit-calendar">

        <thead>
            <tr>
                <th>Mon</th>
                <th>Tue</th>
                <th>Wed</th>
                <th>Thu</th>
                <th>Fri</th>
                <th>Sat</th>
                <th>Sun</th>
            </tr>
        </thead>

        <tbody>
    """

    for week in month_weeks:

        calendar_html += "<tr>"

        for day in week:

            if day == 0:

                calendar_html += """
                <td style="background:transparent;"></td>
                """

                continue

            current_date = date(year, month, day)

            if current_date in completed_dates:

                background = "#166534"
                color = "#FFFFFF"
                border = "1px solid #22C55E"

            elif current_date == today:

                background = "#1E40AF"
                color = "#FFFFFF"
                border = "2px solid #60A5FA"

            elif habit_start_date <= current_date <= today:

                background = "#E5E7EB"
                color = "#374151"
                border = "1px solid #D1D5DB"

            else:

                background = "#374151"
                color = "#D1D5DB"
                border = "1px solid #4B5563"

            calendar_html += f"""
            <td style="
                background:{background};
                color:{color};
                border:{border};
            ">
                {day}
            </td>
            """

        calendar_html += "</tr>"

    calendar_html += """
        </tbody>
    </table>

    </body>
    </html>
    """

    component_height = 75 + (len(month_weeks) * 58)

    components.html(
        calendar_html,
        height=component_height,
        scrolling=False
    )


# ==================================================
# HABIT MANAGEMENT
# ==================================================

def show_habits():

    user_id = st.session_state.user["id"]

    today = str(date.today())

    st.title("🔥 Habit Tracker")
    st.caption("Build good habits. Stay consistent every day.")

    # ==================================================
    # XP SUCCESS MESSAGE
    # ==================================================

    if "habit_xp_message" in st.session_state:

        st.success(st.session_state["habit_xp_message"])

        st.session_state.pop("habit_xp_message", None)

    # ==================================================
    # ADD NEW HABIT
    # ==================================================

    with st.expander("➕ Add New Habit", expanded=True):

        with st.form("habit_form"):

            habit_name = st.text_input("Habit Name")

            description = st.text_area(
                "Description (Optional)"
            )

            submitted = st.form_submit_button("Add Habit")

            if submitted:

                if habit_name.strip():

                    conn = get_connection()

                    try:
                        conn.execute(
                            """
                            INSERT INTO habits
                            (name, description, user_id)
                            VALUES (?, ?, ?)
                            """,
                            (
                                habit_name.strip(),
                                description.strip(),
                                user_id
                            )
                        )

                        conn.commit()

                    finally:
                        conn.close()

                    st.success("Habit added successfully!")
                    st.rerun()

                else:
                    st.warning("Please enter a habit name.")

    st.divider()

    # ==================================================
    # FETCH USER HABITS
    # ==================================================

    conn = get_connection()

    try:
        habits = conn.execute(
            """
            SELECT id, name, description, created_at
            FROM habits
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

    finally:
        conn.close()

    st.subheader("Your Habits")

    if not habits:
        st.info("You haven't added any habits yet.")
        return

    # ==================================================
    # DAILY PROGRESS AND COMPLETED HABITS
    # ==================================================

    conn = get_connection()

    try:
        completed_habits = conn.execute(
            """
            SELECT DISTINCT hl.habit_id
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date = ?
            """,
            (user_id, today)
        ).fetchall()

    finally:
        conn.close()

    completed_habit_ids = {
        row[0] for row in completed_habits
    }

    total_habits = len(habits)
    completed_count = len(completed_habit_ids)

    progress = completed_count / total_habits

    # ==================================================
    # DAILY HABIT REMINDERS
    # ==================================================

    show_habit_reminders(
        habits,
        completed_habit_ids
    )

    st.divider()

    # ==================================================
    # DAILY PROGRESS
    # ==================================================

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Habits", total_habits)

    with col2:
        st.metric("Completed Today", completed_count)

    with col3:
        st.metric(
            "Remaining",
            total_habits - completed_count
        )

    st.progress(progress)

    st.caption(
        f"You completed {completed_count} out of "
        f"{total_habits} habits today."
    )

    st.divider()

    # ==================================================
    # STREAK OVERVIEW
    # ==================================================

    st.subheader("🏆 Your Streak Achievements")

    all_streaks = []

    for habit in habits:

        habit_id = habit[0]

        current, longest, total = calculate_streak(
            habit_id,
            user_id
        )

        all_streaks.append({
            "current": current,
            "longest": longest,
            "total": total
        })

    best_current = max(
        (item["current"] for item in all_streaks),
        default=0
    )

    best_longest = max(
        (item["longest"] for item in all_streaks),
        default=0
    )

    total_checkins = sum(
        item["total"] for item in all_streaks
    )

    streak_col1, streak_col2, streak_col3 = st.columns(3)

    with streak_col1:
        st.metric("🔥 Best Current Streak", f"{best_current} days")

    with streak_col2:
        st.metric("🏆 Longest Streak Record", f"{best_longest} days")

    with streak_col3:
        st.metric("✅ Total Check-ins", total_checkins)

    st.divider()

    # ==================================================
    # DISPLAY EACH HABIT
    # ==================================================

    for habit in habits:

        habit_id, name, description, created_at = habit

        today_log = habit_id in completed_habit_ids

        current_streak, longest_streak, total = calculate_streak(
            habit_id,
            user_id
        )

        latest_achievement, next_milestone = get_streak_milestone(
            current_streak
        )

        with st.container(border=True):

            col1, col2 = st.columns([4, 1])

            with col1:

                st.markdown(f"### 🔥 {name}")

                if description:
                    st.caption(description)

                st.write(
                    f"🔥 Current Streak: **{current_streak} days**"
                )

                st.write(
                    f"🏆 Longest Streak: **{longest_streak} days**"
                )

                st.write(
                    f"✅ Total Check-ins: **{total}**"
                )

                if today_log:
                    st.success("Completed today!")

                else:
                    st.warning("Not completed today")

                if latest_achievement:
                    st.success(
                        f"🏅 {latest_achievement}-Day Milestone Achieved!"
                    )

                if next_milestone:

                    remaining = next_milestone - current_streak

                    st.info(
                        f"🎯 Next milestone: {next_milestone} days "
                        f"({remaining} more consecutive days)"
                    )

                    st.progress(
                        min(current_streak / next_milestone, 1.0)
                    )

                else:
                    st.success("🌟 All streak milestones achieved!")

            with col2:

                # ==================================================
                # CHECK IN AND AWARD XP
                # ==================================================

                if not today_log:

                    if st.button(
                        "Check In",
                        key=f"checkin_{habit_id}"
                    ):

                        conn = get_connection()

                        try:
                            cursor = conn.execute(
                                """
                                INSERT INTO habit_logs
                                (habit_id, log_date)
                                SELECT id, ?
                                FROM habits
                                WHERE id = ?
                                  AND user_id = ?
                                  AND NOT EXISTS (
                                      SELECT 1
                                      FROM habit_logs
                                      WHERE habit_id = ?
                                        AND log_date = ?
                                  )
                                """,
                                (
                                    today,
                                    habit_id,
                                    user_id,
                                    habit_id,
                                    today
                                )
                            )

                            conn.commit()

                            log_added = cursor.rowcount > 0
                            habit_log_id = cursor.lastrowid

                        finally:
                            conn.close()

                        if log_added:

                            awarded, xp = award_xp(
                                user_id,
                                "habit",
                                habit_log_id
                            )

                            if awarded:

                                st.session_state["habit_xp_message"] = (
                                    f"🔥 Habit completed! You earned {xp} XP!"
                                )

                            else:

                                st.session_state["habit_xp_message"] = (
                                    "🔥 Habit completed! XP was already earned for this check-in."
                                )

                        st.rerun()

                # ==================================================
                # UNDO CHECK-IN
                # ==================================================

                else:

                    if st.button(
                        "Undo",
                        key=f"undo_{habit_id}"
                    ):

                        conn = get_connection()

                        try:
                            conn.execute(
                                """
                                DELETE FROM habit_logs
                                WHERE habit_id = ?
                                  AND log_date = ?
                                  AND EXISTS (
                                      SELECT 1
                                      FROM habits
                                      WHERE habits.id = habit_logs.habit_id
                                        AND habits.user_id = ?
                                  )
                                """,
                                (habit_id, today, user_id)
                            )

                            conn.commit()

                        finally:
                            conn.close()

                        st.session_state["habit_xp_message"] = (
                            "Check-in undone. Previously earned XP is retained."
                        )

                        st.rerun()

            # ==================================================
            # DAILY STREAK CALENDAR
            # ==================================================

            with st.expander("🔥 View Daily Streak Calendar"):

                show_streak_calendar(
                    habit_id,
                    user_id,
                    created_at
                )

            # ==================================================
            # HABIT HISTORY
            # ==================================================

            with st.expander("📅 View Habit History"):

                conn = get_connection()

                try:
                    history = conn.execute(
                        """
                        SELECT hl.log_date
                        FROM habit_logs hl
                        INNER JOIN habits h ON h.id = hl.habit_id
                        WHERE hl.habit_id = ?
                          AND h.user_id = ?
                        ORDER BY hl.log_date DESC
                        """,
                        (habit_id, user_id)
                    ).fetchall()

                finally:
                    conn.close()

                if history:

                    st.write("**Completed Dates:**")

                    for log in history:
                        st.write(f"✅ {log[0]}")

                else:
                    st.info("No history available yet.")

            # ==================================================
            # DELETE HABIT
            # ==================================================

            if st.button(
                "🗑️ Delete Habit",
                key=f"delete_habit_{habit_id}"
            ):

                conn = get_connection()

                try:
                    conn.execute(
                        """
                        DELETE FROM habits
                        WHERE id = ? AND user_id = ?
                        """,
                        (habit_id, user_id)
                    )

                    conn.commit()

                finally:
                    conn.close()

                st.success("Habit deleted successfully!")
                st.rerun()
