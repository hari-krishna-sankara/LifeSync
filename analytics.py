
import streamlit as st
import pandas as pd
import plotly.express as px

from database import get_connection
from datetime import date, timedelta


def show_analytics():

    user_id = st.session_state.user["id"]

    st.title("📊 Analytics Dashboard")
    st.caption("Understand your progress and improve your consistency.")

    today = date.today()

    conn = get_connection()

    try:

        # -------------------------------
        # GOAL STATISTICS
        # -------------------------------

        goals = conn.execute(
            """
            SELECT status, COUNT(*)
            FROM goals
            WHERE user_id = ?
            GROUP BY status
            """,
            (user_id,)
        ).fetchall()

        total_goals = sum(row[1] for row in goals)

        completed_goals = sum(
            row[1] for row in goals
            if row[0] and row[0].lower() == "completed"
        )

        pending_goals = total_goals - completed_goals

        # -------------------------------
        # TASK STATISTICS
        # -------------------------------

        tasks = conn.execute(
            """
            SELECT completed, COUNT(*)
            FROM tasks
            WHERE user_id = ?
            GROUP BY completed
            """,
            (user_id,)
        ).fetchall()

        total_tasks = sum(row[1] for row in tasks)

        completed_tasks = sum(
            row[1] for row in tasks
            if row[0] == 1
        )

        pending_tasks = total_tasks - completed_tasks

        # -------------------------------
        # HABIT STATISTICS
        # -------------------------------

        total_habits = conn.execute(
            """
            SELECT COUNT(*)
            FROM habits
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()[0]

        completed_today = conn.execute(
            """
            SELECT COUNT(DISTINCT hl.habit_id)
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date = ?
            """,
            (user_id, str(today))
        ).fetchone()[0]

        # -------------------------------
        # WEEKLY HABIT ACTIVITY
        # -------------------------------

        weekly_data = conn.execute(
            """
            SELECT hl.log_date, COUNT(DISTINCT hl.habit_id)
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date >= ?
              AND hl.log_date <= ?
            GROUP BY hl.log_date
            ORDER BY hl.log_date
            """,
            (
                user_id,
                str(today - timedelta(days=6)),
                str(today)
            )
        ).fetchall()

    finally:
        conn.close()

    # -------------------------------
    # TOP METRICS
    # -------------------------------

    st.subheader("📈 Your Overall Performance")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🎯 Total Goals", total_goals)
    col2.metric("🏆 Goals Completed", completed_goals)
    col3.metric("📝 Tasks Completed", completed_tasks)
    col4.metric("🔥 Active Habits", total_habits)

    st.divider()

    # -------------------------------
    # GOAL AND TASK PROGRESS
    # -------------------------------

    st.subheader("📊 Goals & Tasks Progress")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### 🎯 Goal Progress")

        if total_goals > 0:

            goal_df = pd.DataFrame({
                "Status": ["Completed", "Pending"],
                "Count": [completed_goals, pending_goals]
            })

            fig = px.pie(
                goal_df,
                names="Status",
                values="Count",
                hole=0.5,
                title="Goal Completion"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("Create goals to see your goal analytics.")

    with col2:

        st.markdown("### 📝 Task Progress")

        if total_tasks > 0:

            task_df = pd.DataFrame({
                "Status": ["Completed", "Pending"],
                "Count": [completed_tasks, pending_tasks]
            })

            fig = px.pie(
                task_df,
                names="Status",
                values="Count",
                hole=0.5,
                title="Task Completion"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("Add tasks to see your task analytics.")

    st.divider()

    # -------------------------------
    # WEEKLY HABIT ACTIVITY
    # -------------------------------

    st.subheader("🔥 Weekly Habit Activity")

    weekly_dates = [
        today - timedelta(days=i)
        for i in range(6, -1, -1)
    ]

    weekly_counts = dict(weekly_data)

    weekly_df = pd.DataFrame({
        "Date": weekly_dates,
        "Completed Habits": [
            weekly_counts.get(str(day), 0)
            for day in weekly_dates
        ]
    })

    weekly_df["Date"] = pd.to_datetime(
        weekly_df["Date"]
    )

    fig = px.bar(
        weekly_df,
        x="Date",
        y="Completed Habits",
        title="Daily Habit Completions - Last 7 Days",
        text="Completed Habits"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Completed Habits",
        xaxis=dict(tickformat="%d %b")
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.divider()

    # -------------------------------
    # TODAY'S HABIT CONSISTENCY
    # -------------------------------

    st.subheader("📅 Today's Habit Consistency")

    if total_habits > 0:

        habit_progress = completed_today / total_habits

        st.progress(habit_progress)

        st.write(
            f"{completed_today} out of {total_habits} habits completed."
        )

        st.write(
            f"Consistency: {habit_progress * 100:.1f}%"
        )

    else:
        st.info("Create habits to measure your consistency.")

    st.divider()

    # -------------------------------
    # OVERALL COMPLETION
    # -------------------------------

    st.subheader("🏆 Overall Completion")

    total_items = total_goals + total_tasks

    completed_items = completed_goals + completed_tasks

    if total_items > 0:

        overall_progress = completed_items / total_items

        st.progress(overall_progress)

        st.write(
            f"{completed_items} out of {total_items} goals and tasks completed."
        )

        st.write(
            f"Overall completion: {overall_progress * 100:.1f}%"
        )

    else:
        st.info(
            "Start adding goals and tasks to see your overall progress."
        )
