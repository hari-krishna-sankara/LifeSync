
import streamlit as st
from database import get_connection
from datetime import date, timedelta


def get_weekly_data(user_id):

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    start_date = week_start.isoformat()
    end_date = today.isoformat()

    days_elapsed = (today - week_start).days + 1

    conn = get_connection()

    try:
        # Tasks completed this week
        completed_tasks = conn.execute("""
            SELECT COUNT(DISTINCT activity_id)
            FROM xp_history
            WHERE user_id = ?
              AND activity_type = 'task'
              AND date(created_at, '+5 hours', '+30 minutes')
                  BETWEEN ? AND ?
        """, (user_id, start_date, end_date)).fetchone()[0]

        # Goals completed this week
        completed_goals = conn.execute("""
            SELECT COUNT(DISTINCT activity_id)
            FROM xp_history
            WHERE user_id = ?
              AND activity_type = 'goal'
              AND date(created_at, '+5 hours', '+30 minutes')
                  BETWEEN ? AND ?
        """, (user_id, start_date, end_date)).fetchone()[0]

        # Habit check-ins this week
        habit_checkins = conn.execute("""
            SELECT COUNT(*)
            FROM habit_logs hl
            JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date BETWEEN ? AND ?
        """, (user_id, start_date, end_date)).fetchone()[0]

        # Total habits
        total_habits = conn.execute("""
            SELECT COUNT(*)
            FROM habits
            WHERE user_id = ?
        """, (user_id,)).fetchone()[0]

        # Expected habit check-ins so far this week
        expected_checkins = total_habits * days_elapsed

        habit_rate = (
            round((habit_checkins / expected_checkins) * 100)
            if expected_checkins > 0 else 0
        )

        # XP earned this week
        weekly_xp = conn.execute("""
            SELECT COALESCE(SUM(xp_earned), 0)
            FROM xp_history
            WHERE user_id = ?
              AND date(created_at, '+5 hours', '+30 minutes')
                  BETWEEN ? AND ?
        """, (user_id, start_date, end_date)).fetchone()[0]

        # Weekly productivity score:
        # Based on progress towards a 100 XP weekly target
        productivity_score = min(weekly_xp, 100)

        return {
            "week_start": week_start,
            "today": today,
            "completed_tasks": completed_tasks,
            "completed_goals": completed_goals,
            "habit_checkins": habit_checkins,
            "habit_rate": habit_rate,
            "weekly_xp": weekly_xp,
            "productivity_score": productivity_score
        }

    finally:
        conn.close()


def show_weekly_review():

    user_id = st.session_state.user["id"]

    st.title("📊 Weekly Review")
    st.caption("Review your progress and celebrate your achievements.")

    data = get_weekly_data(user_id)

    st.write(
        f"**Week:** {data['week_start'].strftime('%d %b %Y')} "
        f"– {data['today'].strftime('%d %b %Y')}"
    )

    st.divider()

    # Weekly statistics
    st.subheader("📈 Your Weekly Progress")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Tasks Completed",
            data["completed_tasks"]
        )

    with col2:
        st.metric(
            "Goals Completed",
            data["completed_goals"]
        )

    with col3:
        st.metric(
            "Habit Check-ins",
            data["habit_checkins"]
        )

    st.divider()

    # Productivity score and XP
    st.subheader("🏆 Weekly Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Productivity Score",
            f"{data['productivity_score']} / 100"
        )

        st.progress(data["productivity_score"] / 100)

        st.caption("Based on progress towards a 100 XP weekly target.")

    with col2:
        st.metric(
            "XP Earned This Week",
            f"+{data['weekly_xp']} XP"
        )

    st.divider()

    # Habit completion rate
    st.subheader("🔥 Habit Consistency")

    st.metric(
        "Habit Completion Rate",
        f"{data['habit_rate']}%"
    )

    st.progress(data["habit_rate"] / 100)

    st.divider()

    # Weekly feedback
    st.subheader("💡 Suggestions for Next Week")

    suggestions = []

    if data["completed_tasks"] == 0:
        suggestions.append(
            "Try completing at least one task next week."
        )

    if data["completed_goals"] == 0:
        suggestions.append(
            "Make progress towards one of your goals."
        )

    if data["habit_rate"] < 70:
        suggestions.append(
            "Improve your habit consistency by checking in daily."
        )
    elif data["habit_rate"] >= 90:
        suggestions.append(
            "Excellent habit consistency! Keep it going."
        )

    if data["weekly_xp"] < 100:
        suggestions.append(
            "Aim to earn 100 XP next week."
        )
    else:
        suggestions.append(
            "Great work reaching your weekly XP target!"
        )

    for suggestion in suggestions:
        st.info(suggestion)
