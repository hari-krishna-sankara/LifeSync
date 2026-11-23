
import streamlit as st
import pandas as pd
import plotly.express as px

from html import escape
from datetime import date, timedelta

from database import initialize_database, get_connection

from auth import (
    show_auth_page,
    initialize_auth,
    logout_user,
    show_profile_settings
)

from goals import show_goals
from task import show_tasks
from habbits import show_habits
from analytics import show_analytics

from gamification import (
    initialize_user_progress,
    get_user_progress
)

from gamification_page import show_gamification_page
from calendar_page import show_calendar
from weekly_review import show_weekly_review
from focus_timer import show_focus_timer


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Trackly",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================================
# DATABASE INITIALIZATION
# ==========================================================

initialize_database()


# ==========================================================
# CUSTOM CSS
# ==========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0F172A;
        color: #FFFFFF;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #273449;
    }

    [data-testid="stSidebar"] p {
        color: #D1D5DB;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        border: 1px solid #374151;
        background-color: #1E293B;
        color: #FFFFFF;
        padding: 10px 15px;
        font-weight: 600;
        transition: 0.2s;
    }

    div.stButton > button:hover {
        background-color: #6D28D9;
        color: #FFFFFF;
        border-color: #8B5CF6;
    }

    [data-testid="stMetric"] {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #334155;
    }

    [data-testid="stMetricLabel"] {
        color: #CBD5E1;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    hr {
        border-color: #334155;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# SESSION STATE
# ==========================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Dashboard"


# ==========================================================
# AUTHENTICATION
# ==========================================================

cookies = initialize_auth()

if not st.session_state.authenticated or not st.session_state.user:
    show_auth_page(cookies)
    st.stop()


user_id = st.session_state.user["id"]

user_name = escape(str(st.session_state.user["name"]))
user_email = escape(str(st.session_state.user["email"]))


# ==========================================================
# DASHBOARD DATA
# ==========================================================

def get_dashboard_data(user_id):

    today = date.today()

    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    conn = get_connection()

    try:

        # GOALS

        total_goals = conn.execute(
            """
            SELECT COUNT(*)
            FROM goals
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()[0]

        completed_goals = conn.execute(
            """
            SELECT COUNT(*)
            FROM goals
            WHERE user_id = ?
              AND LOWER(status) = 'completed'
            """,
            (user_id,)
        ).fetchone()[0]

        # TASKS

        total_tasks = conn.execute(
            """
            SELECT COUNT(*)
            FROM tasks
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()[0]

        completed_tasks = conn.execute(
            """
            SELECT COUNT(*)
            FROM tasks
            WHERE user_id = ?
              AND completed = 1
            """,
            (user_id,)
        ).fetchone()[0]

        overdue_tasks = conn.execute(
            """
            SELECT COUNT(*)
            FROM tasks
            WHERE user_id = ?
              AND completed = 0
              AND due_date < ?
            """,
            (user_id, str(today))
        ).fetchone()[0]

        # HABITS

        total_habits = conn.execute(
            """
            SELECT COUNT(*)
            FROM habits
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()[0]

        completed_habits = conn.execute(
            """
            SELECT COUNT(DISTINCT hl.habit_id)
            FROM habit_logs hl
            INNER JOIN habits h
                ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date = ?
            """,
            (user_id, str(today))
        ).fetchone()[0]

        # WEEKLY HABIT ACTIVITY

        weekly_activity = conn.execute(
            """
            SELECT
                hl.log_date,
                COUNT(DISTINCT hl.habit_id)
            FROM habit_logs hl
            INNER JOIN habits h
                ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date BETWEEN ? AND ?
            GROUP BY hl.log_date
            ORDER BY hl.log_date
            """,
            (
                user_id,
                str(week_start),
                str(today)
            )
        ).fetchall()

        # MONTHLY HABIT ACTIVITY

        monthly_activity = conn.execute(
            """
            SELECT
                hl.log_date,
                COUNT(DISTINCT hl.habit_id)
            FROM habit_logs hl
            INNER JOIN habits h
                ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date BETWEEN ? AND ?
            GROUP BY hl.log_date
            ORDER BY hl.log_date
            """,
            (
                user_id,
                str(month_start),
                str(today)
            )
        ).fetchall()

        # RECENT TASKS

        recent_tasks = conn.execute(
            """
            SELECT
                id,
                title,
                due_date,
                priority,
                completed,
                created_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (user_id,)
        ).fetchall()

        # RECENT GOALS

        recent_goals = conn.execute(
            """
            SELECT
                id,
                title,
                description,
                target_date,
                status,
                created_at
            FROM goals
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (user_id,)
        ).fetchall()

        return {
            "total_goals": total_goals,
            "completed_goals": completed_goals,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_habits": total_habits,
            "completed_habits": completed_habits,
            "weekly_activity": weekly_activity,
            "monthly_activity": monthly_activity,
            "recent_tasks": recent_tasks,
            "recent_goals": recent_goals
        }

    finally:
        conn.close()


# ==========================================================
# SMART DASHBOARD REMINDERS
# ==========================================================

def get_dashboard_reminders(user_id):

    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)

    reminders = {
        "Overdue Tasks": [],
        "Tasks Due Today": [],
        "Tasks Due Tomorrow": [],
        "Upcoming Tasks": [],
        "Overdue Goals": [],
        "Goals Due Today": [],
        "Upcoming Goals": [],
        "Pending Habits": []
    }

    conn = get_connection()

    try:

        # TASK REMINDERS

        tasks = conn.execute(
            """
            SELECT title, due_date
            FROM tasks
            WHERE user_id = ?
              AND completed = 0
              AND due_date IS NOT NULL
              AND due_date != ''
            """,
            (user_id,)
        ).fetchall()

        for title, due_date in tasks:

            try:
                due = date.fromisoformat(due_date)
            except (ValueError, TypeError):
                continue

            item = {
                "title": title,
                "date": due_date
            }

            if due < today:
                reminders["Overdue Tasks"].append(item)

            elif due == today:
                reminders["Tasks Due Today"].append(item)

            elif due == tomorrow:
                reminders["Tasks Due Tomorrow"].append(item)

            elif today < due <= next_week:
                reminders["Upcoming Tasks"].append(item)

        # GOAL REMINDERS

        goals = conn.execute(
            """
            SELECT title, target_date
            FROM goals
            WHERE user_id = ?
              AND LOWER(status) != 'completed'
              AND target_date IS NOT NULL
              AND target_date != ''
            """,
            (user_id,)
        ).fetchall()

        for title, target_date in goals:

            try:
                target = date.fromisoformat(target_date)
            except (ValueError, TypeError):
                continue

            item = {
                "title": title,
                "date": target_date
            }

            if target < today:
                reminders["Overdue Goals"].append(item)

            elif target == today:
                reminders["Goals Due Today"].append(item)

            elif today < target <= next_week:
                reminders["Upcoming Goals"].append(item)

        # HABIT REMINDERS

        habits = conn.execute(
            """
            SELECT h.id, h.name
            FROM habits h
            LEFT JOIN habit_logs hl
                ON h.id = hl.habit_id
                AND hl.log_date = ?
            WHERE h.user_id = ?
              AND hl.id IS NULL
            ORDER BY h.id DESC
            """,
            (str(today), user_id)
        ).fetchall()

        for habit_id, name in habits:

            reminders["Pending Habits"].append({
                "title": name,
                "date": "Not completed today"
            })

        return reminders

    finally:
        conn.close()


# ==========================================================
# DISPLAY SMART REMINDERS
# ==========================================================

def show_dashboard_reminders(reminders):

    st.markdown("## 🔔 Smart Reminders")

    total_reminders = sum(
        len(items) for items in reminders.values()
    )

    if total_reminders == 0:

        st.success(
            "🎉 You're all caught up! No pending reminders."
        )
        return

    overdue_count = (
        len(reminders["Overdue Tasks"])
        + len(reminders["Overdue Goals"])
    )

    due_today_count = (
        len(reminders["Tasks Due Today"])
        + len(reminders["Goals Due Today"])
    )

    pending_habits_count = len(
        reminders["Pending Habits"]
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🔔 Total Reminders", total_reminders)

    with col2:
        st.metric("⚠️ Overdue", overdue_count)

    with col3:
        st.metric("📅 Due Today", due_today_count)

    with col4:
        st.metric("🔥 Pending Habits", pending_habits_count)

    st.divider()

    reminder_groups = [
        ("⚠️ Overdue Tasks", "Overdue Tasks"),
        ("📝 Tasks Due Today", "Tasks Due Today"),
        ("⏰ Tasks Due Tomorrow", "Tasks Due Tomorrow"),
        ("📌 Upcoming Tasks", "Upcoming Tasks"),
        ("🎯 Overdue Goals", "Overdue Goals"),
        ("🏁 Goals Due Today", "Goals Due Today"),
        ("🎯 Upcoming Goals", "Upcoming Goals"),
        ("🔥 Habits To Complete Today", "Pending Habits")
    ]

    for heading, key in reminder_groups:

        items = reminders[key]

        if not items:
            continue

        with st.expander(
            f"{heading} ({len(items)})",
            expanded=key in [
                "Overdue Tasks",
                "Tasks Due Today",
                "Overdue Goals",
                "Goals Due Today",
                "Pending Habits"
            ]
        ):

            for item in items:

                st.write(
                    f"• **{escape(str(item['title']))}** "
                    f"— {escape(str(item['date']))}"
                )


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.html(
        """
        <div style="text-align:center; padding:15px 0 25px 0;">
            <h1 style="color:#A78BFA; font-size:32px; margin:0;">
                🎯 Trackly
            </h1>
            <p style="color:#9CA3AF; margin-top:5px; font-size:13px;">
                Your Personal Productivity Tracker
            </p>
        </div>
        """
    )

    st.divider()

    # PROFILE

    profile_html = f"""
    <div style="
        background-color:#1E293B;
        padding:16px;
        border-radius:12px;
        border:1px solid #374151;
        margin-bottom:20px;
    ">
        <div style="font-size:28px; margin-bottom:8px;">
            👤
        </div>
        <div style="
            color:#FFFFFF;
            font-size:16px;
            font-weight:bold;
            margin-bottom:5px;
        ">
            {user_name}
        </div>
        <div style="
            color:#A78BFA;
            font-size:12px;
            overflow-wrap:anywhere;
        ">
            {user_email}
        </div>
    </div>
    """

    st.html(profile_html)

    st.html(
        """
        <p style="
            color:#9CA3AF;
            font-size:12px;
            font-weight:bold;
            letter-spacing:1px;
            margin-bottom:10px;
        ">
            MAIN MENU
        </p>
        """
    )

    # NAVIGATION

    pages = {
        "🏠 Dashboard": "Dashboard",
        "🎯 Goals": "Goals",
        "📝 Tasks": "Tasks",
        "🔥 Habits": "Habits",
        "📅 Calendar": "Calendar",
        "📊 Weekly Review": "Weekly Review",
        "⏱️ Focus Timer": "Focus Timer",
        "🏆 Gamification": "Gamification",
        "📊 Analytics": "Analytics",
        "⚙️ Profile & Settings": "Profile"
    }

    for label, page in pages.items():

        if st.button(
            label,
            key=f"nav_{page}",
            use_container_width=True
        ):

            st.session_state.selected_page = page
            st.rerun()

    st.divider()

    # LOGOUT

    if st.button("🚪 Logout", use_container_width=True):
        logout_user(cookies)

    st.html(
        """
        <div style="
            text-align:center;
            color:#64748B;
            font-size:11px;
            margin-top:25px;
        ">
            Trackly © 2026
            <br>
            Stay consistent. Keep growing.
        </div>
        """
    )


# ==========================================================
# PAGE ROUTING
# ==========================================================

selected_page = st.session_state.selected_page


# ==========================================================
# ADVANCED DASHBOARD
# ==========================================================

if selected_page == "Dashboard":

    welcome_html = f"""
    <div style="
        background:linear-gradient(
            135deg,
            #312E81,
            #581C87,
            #4C1D95
        );
        padding:30px;
        border-radius:18px;
        margin-bottom:25px;
        border:1px solid #6D28D9;
    ">
        <h1 style="
            margin:0;
            color:#FFFFFF;
            font-size:32px;
        ">
            Welcome, {user_name} 👋
        </h1>

        <p style="
            color:#C4B5FD;
            margin-top:10px;
            margin-bottom:0;
            font-size:16px;
        ">
            Track your progress. Stay consistent.
            Keep moving forward. 🚀
        </p>
    </div>
    """

    st.html(welcome_html)

    # XP AND LEVEL SUMMARY

    initialize_user_progress(user_id)

    xp_data = get_user_progress(user_id)

    total_xp = xp_data["total_xp"]
    current_level = xp_data["level"]
    current_xp = xp_data["current_level_xp"]
    required_xp = xp_data["next_level_xp"]
    xp_progress = xp_data["progress"]

    st.markdown("## 🏆 Your Gamification Progress")

    xp_col1, xp_col2, xp_col3 = st.columns(3)

    with xp_col1:
        st.metric("⭐ Total XP", f"{total_xp} XP")

    with xp_col2:
        st.metric("🏆 Current Level", current_level)

    with xp_col3:
        st.metric(
            "🚀 XP to Next Level",
            f"{required_xp - current_xp} XP"
        )

    st.progress(xp_progress)

    st.caption(
        f"Level {current_level} Progress: "
        f"{current_xp} / {required_xp} XP"
    )

    st.divider()

    data = get_dashboard_data(user_id)

    # SMART REMINDERS

    dashboard_reminders = get_dashboard_reminders(user_id)

    show_dashboard_reminders(dashboard_reminders)

    st.divider()

    total_goals = data["total_goals"]
    completed_goals = data["completed_goals"]

    total_tasks = data["total_tasks"]
    completed_tasks = data["completed_tasks"]

    overdue_tasks = data["overdue_tasks"]

    total_habits = data["total_habits"]
    completed_habits = data["completed_habits"]

    # OVERALL PERFORMANCE

    st.markdown("## 📈 Your Performance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🎯 Total Goals",
            total_goals,
            delta=f"{completed_goals} completed"
        )

    with col2:
        st.metric(
            "📝 Total Tasks",
            total_tasks,
            delta=f"{completed_tasks} completed"
        )

    with col3:
        st.metric(
            "🔥 Active Habits",
            total_habits,
            delta=f"{completed_habits} completed today"
        )

    with col4:
        st.metric("⚠️ Overdue Tasks", overdue_tasks)

    st.divider()

    # COMPLETION SCORE

    st.markdown("## 🏆 Overall Completion Score")

    total_items = total_goals + total_tasks
    completed_items = completed_goals + completed_tasks

    completion_score = (
        completed_items / total_items
        if total_items > 0 else 0
    )

    score_col1, score_col2 = st.columns([2, 1])

    with score_col1:

        st.progress(completion_score)

        st.write(
            f"**{completed_items} of {total_items}** "
            "goals and tasks completed."
        )

    with score_col2:

        st.metric(
            "Completion Score",
            f"{completion_score * 100:.1f}%"
        )

    st.divider()

    # GOAL, TASK AND HABIT PROGRESS

    st.markdown("## 🚀 Your Progress")

    progress_col1, progress_col2, progress_col3 = st.columns(3)

    goal_progress = (
        completed_goals / total_goals
        if total_goals > 0 else 0
    )

    task_progress = (
        completed_tasks / total_tasks
        if total_tasks > 0 else 0
    )

    habit_progress = (
        completed_habits / total_habits
        if total_habits > 0 else 0
    )

    with progress_col1:

        st.markdown("### 🎯 Goals")
        st.progress(goal_progress)

        st.write(f"{completed_goals} / {total_goals} completed")

    with progress_col2:

        st.markdown("### 📝 Tasks")
        st.progress(task_progress)

        st.write(f"{completed_tasks} / {total_tasks} completed")

    with progress_col3:

        st.markdown("### 🔥 Habits")
        st.progress(habit_progress)

        st.write(
            f"{completed_habits} / {total_habits} completed today"
        )

    st.divider()

    # WEEKLY AND MONTHLY ACTIVITY

    st.markdown("## 📅 Activity Overview")

    activity_tab1, activity_tab2 = st.tabs(
        ["📆 Last 7 Days", "🗓️ Last 30 Days"]
    )

    today = date.today()

    with activity_tab1:

        weekly_dates = [
            today - timedelta(days=i)
            for i in range(6, -1, -1)
        ]

        weekly_counts = dict(data["weekly_activity"])

        weekly_df = pd.DataFrame({
            "Date": weekly_dates,
            "Completed Habits": [
                weekly_counts.get(str(day), 0)
                for day in weekly_dates
            ]
        })

        weekly_df["Date"] = pd.to_datetime(weekly_df["Date"])

        fig = px.bar(
            weekly_df,
            x="Date",
            y="Completed Habits",
            title="Your Weekly Habit Activity",
            text="Completed Habits"
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Completed Habits",
            xaxis=dict(tickformat="%d %b"),
            plot_bgcolor="#1E293B",
            paper_bgcolor="#1E293B",
            font_color="white"
        )

        st.plotly_chart(fig, use_container_width=True)

    with activity_tab2:

        monthly_dates = [
            today - timedelta(days=i)
            for i in range(29, -1, -1)
        ]

        monthly_counts = dict(data["monthly_activity"])

        monthly_df = pd.DataFrame({
            "Date": monthly_dates,
            "Completed Habits": [
                monthly_counts.get(str(day), 0)
                for day in monthly_dates
            ]
        })

        monthly_df["Date"] = pd.to_datetime(monthly_df["Date"])

        fig = px.line(
            monthly_df,
            x="Date",
            y="Completed Habits",
            title="Your Monthly Habit Activity",
            markers=True
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Completed Habits",
            xaxis=dict(tickformat="%d %b"),
            plot_bgcolor="#1E293B",
            paper_bgcolor="#1E293B",
            font_color="white"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # RECENT ACTIVITY

    st.markdown("## 📌 Recent Activity")

    recent_col1, recent_col2 = st.columns(2)

    with recent_col1:

        st.markdown("### 📝 Recent Tasks")

        if data["recent_tasks"]:

            for task in data["recent_tasks"]:

                (
                    task_id,
                    title,
                    due_date,
                    priority,
                    completed,
                    created_at
                ) = task

                status = (
                    "✅ Completed"
                    if completed
                    else "⏳ Pending"
                )

                task_html = f"""
                <div style="
                    background-color:#1E293B;
                    padding:14px;
                    border-radius:10px;
                    border:1px solid #334155;
                    margin-bottom:10px;
                ">
                    <div style="color:#FFFFFF;font-weight:bold;">
                        {escape(str(title))}
                    </div>
                    <div style="
                        color:#A78BFA;
                        font-size:12px;
                        margin-top:5px;
                    ">
                        Priority: {escape(str(priority))}
                        &nbsp; | &nbsp;
                        {status}
                    </div>
                    <div style="
                        color:#9CA3AF;
                        font-size:12px;
                        margin-top:5px;
                    ">
                        Due: {escape(str(due_date))}
                    </div>
                </div>
                """

                st.html(task_html)

        else:
            st.info("No tasks yet. Create your first task!")

    with recent_col2:

        st.markdown("### 🎯 Recent Goals")

        if data["recent_goals"]:

            for goal in data["recent_goals"]:

                (
                    goal_id,
                    title,
                    description,
                    target_date,
                    status,
                    created_at
                ) = goal

                goal_html = f"""
                <div style="
                    background-color:#1E293B;
                    padding:14px;
                    border-radius:10px;
                    border:1px solid #334155;
                    margin-bottom:10px;
                ">
                    <div style="color:#FFFFFF;font-weight:bold;">
                        {escape(str(title))}
                    </div>
                    <div style="
                        color:#A78BFA;
                        font-size:12px;
                        margin-top:5px;
                    ">
                        Status: {escape(str(status))}
                    </div>
                    <div style="
                        color:#9CA3AF;
                        font-size:12px;
                        margin-top:5px;
                    ">
                        Target: {escape(str(target_date))}
                    </div>
                </div>
                """

                st.html(goal_html)

        else:
            st.info("No goals yet. Create your first goal!")

    st.divider()

    # QUICK ACTIONS

    st.markdown("## ⚡ Quick Actions")

    quick_col1, quick_col2, quick_col3 = st.columns(3)
    quick_col4, quick_col5, quick_col6 = st.columns(3)

    with quick_col1:

        if st.button("🎯 View Goals"):
            st.session_state.selected_page = "Goals"
            st.rerun()

    with quick_col2:

        if st.button("📝 View Tasks"):
            st.session_state.selected_page = "Tasks"
            st.rerun()

    with quick_col3:

        if st.button("🔥 View Habits"):
            st.session_state.selected_page = "Habits"
            st.rerun()

    with quick_col4:

        if st.button("📅 View Calendar"):
            st.session_state.selected_page = "Calendar"
            st.rerun()

    with quick_col5:

        if st.button("🏆 Gamification"):
            st.session_state.selected_page = "Gamification"
            st.rerun()

    with quick_col6:

        if st.button("⏱️ Focus Timer"):
            st.session_state.selected_page = "Focus Timer"
            st.rerun()


# ==========================================================
# GOALS
# ==========================================================

elif selected_page == "Goals":

    show_goals()


# ==========================================================
# TASKS
# ==========================================================

elif selected_page == "Tasks":

    show_tasks()


# ==========================================================
# HABITS
# ==========================================================

elif selected_page == "Habits":

    show_habits()


# ==========================================================
# UNIFIED CALENDAR
# ==========================================================

elif selected_page == "Calendar":

    show_calendar()


# ==========================================================
# WEEKLY REVIEW
# ==========================================================

elif selected_page == "Weekly Review":

    show_weekly_review()


# ==========================================================
# FOCUS TIMER
# ==========================================================

elif selected_page == "Focus Timer":

    show_focus_timer()


# ==========================================================
# GAMIFICATION
# ==========================================================

elif selected_page == "Gamification":

    show_gamification_page()


# ==========================================================
# ANALYTICS
# ==========================================================

elif selected_page == "Analytics":

    show_analytics()


# ==========================================================
# PROFILE & SETTINGS
# ==========================================================

elif selected_page == "Profile":

    show_profile_settings()
