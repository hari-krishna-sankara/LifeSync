
import streamlit as st
import streamlit.components.v1 as components
import calendar
from datetime import date
from html import escape

from database import get_connection


# ==================================================
# FETCH CALENDAR EVENTS
# ==================================================

def get_calendar_events(user_id, year, month):

    first_day = date(year, month, 1)

    last_day = date(
        year,
        month,
        calendar.monthrange(year, month)[1]
    )

    start = str(first_day)
    end = str(last_day)

    events = {}

    conn = get_connection()

    try:

        # ------------------------------------------
        # TASK EVENTS
        # ------------------------------------------

        tasks = conn.execute(
            """
            SELECT title, due_date, completed, priority
            FROM tasks
            WHERE user_id = ?
              AND due_date >= ?
              AND due_date <= ?
            """,
            (user_id, start, end)
        ).fetchall()

        for task in tasks:

            event_date = date.fromisoformat(task[1])

            events.setdefault(event_date, []).append({
                "type": "Task",
                "title": task[0],
                "status": (
                    "Completed" if task[2] else "Pending"
                ),
                "priority": task[3]
            })

        # ------------------------------------------
        # GOAL EVENTS
        # ------------------------------------------

        goals = conn.execute(
            """
            SELECT title, target_date, status
            FROM goals
            WHERE user_id = ?
              AND target_date >= ?
              AND target_date <= ?
            """,
            (user_id, start, end)
        ).fetchall()

        for goal in goals:

            event_date = date.fromisoformat(goal[1])

            events.setdefault(event_date, []).append({
                "type": "Goal",
                "title": goal[0],
                "status": goal[2]
            })

        # ------------------------------------------
        # HABIT EVENTS
        # ------------------------------------------

        habits = conn.execute(
            """
            SELECT h.name, hl.log_date
            FROM habit_logs hl
            INNER JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
              AND hl.log_date >= ?
              AND hl.log_date <= ?
            """,
            (user_id, start, end)
        ).fetchall()

        for habit in habits:

            event_date = date.fromisoformat(habit[1])

            events.setdefault(event_date, []).append({
                "type": "Habit",
                "title": habit[0],
                "status": "Completed"
            })

    finally:
        conn.close()

    return events


# ==================================================
# CALENDAR PAGE
# ==================================================

def show_calendar():

    user_id = st.session_state.user["id"]

    st.title("📅 Unified Calendar")

    st.caption(
        "View your tasks, goals and habit check-ins in one place."
    )

    st.divider()

    # ------------------------------------------
    # MONTH SELECTION
    # ------------------------------------------

    selected_date = st.date_input(
        "Select a date to view its month",
        value=date.today(),
        key="unified_calendar_date"
    )

    year = selected_date.year
    month = selected_date.month

    events = get_calendar_events(
        user_id,
        year,
        month
    )

    # ------------------------------------------
    # MONTHLY SUMMARY
    # ------------------------------------------

    task_count = sum(
        len([e for e in day_events if e["type"] == "Task"])
        for day_events in events.values()
    )

    goal_count = sum(
        len([e for e in day_events if e["type"] == "Goal"])
        for day_events in events.values()
    )

    habit_count = sum(
        len([e for e in day_events if e["type"] == "Habit"])
        for day_events in events.values()
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📝 Tasks", task_count)

    with col2:
        st.metric("🎯 Goals", goal_count)

    with col3:
        st.metric("🔥 Habit Check-ins", habit_count)

    st.divider()

    # ------------------------------------------
    # CALENDAR LEGEND
    # ------------------------------------------

    st.markdown(
        """
        🟦 Tasks &nbsp;&nbsp;
        🟩 Goals &nbsp;&nbsp;
        🟪 Habits
        """
    )

    st.subheader(
        f"{calendar.month_name[month]} {year}"
    )

    # ------------------------------------------
    # BUILD CALENDAR HTML
    # ------------------------------------------

    weeks = calendar.monthcalendar(year, month)

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
            color: #FFFFFF;
        }

        .calendar {
            width: 100%;
            table-layout: fixed;
            border-collapse: separate;
            border-spacing: 4px;
        }

        .calendar th {
            padding: 10px 2px;
            color: #9CA3AF;
            font-size: 12px;
        }

        .calendar td {
            height: 75px;
            padding: 5px;
            vertical-align: top;
            border: 1px solid #374151;
            border-radius: 8px;
            background: #111827;
            overflow-wrap: anywhere;
        }

        .day-number {
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .today {
            border: 2px solid #60A5FA !important;
        }

        .event {
            font-size: 10px;
            padding: 3px;
            border-radius: 4px;
            margin-top: 3px;
            color: white;
        }

        .task {
            background: #1D4ED8;
        }

        .goal {
            background: #15803D;
        }

        .habit {
            background: #7E22CE;
        }

        .empty {
            background: transparent !important;
            border: none !important;
        }

        @media (max-width: 600px) {
            .calendar {
                border-spacing: 2px;
            }

            .calendar td {
                height: 65px;
                padding: 2px;
            }

            .event {
                font-size: 8px;
                padding: 2px;
            }

            .calendar th {
                font-size: 10px;
            }
        }

    </style>
    </head>

    <body>

    <table class="calendar">

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

    for week in weeks:

        calendar_html += "<tr>"

        for day in week:

            if day == 0:

                calendar_html += '<td class="empty"></td>'
                continue

            current_date = date(year, month, day)

            css_class = "today" if current_date == date.today() else ""

            calendar_html += f"""
            <td class="{css_class}">
                <div class="day-number">{day}</div>
            """

            day_events = events.get(current_date, [])

            for event in day_events:

                event_type = event["type"].lower()

                title = escape(str(event["title"]))

                if event_type == "task":
                    icon = "📝"
                elif event_type == "goal":
                    icon = "🎯"
                else:
                    icon = "🔥"

                calendar_html += f"""
                <div class="event {event_type}">
                    {icon} {title}
                </div>
                """

            calendar_html += "</td>"

        calendar_html += "</tr>"

    calendar_html += """
    </tbody>
    </table>

    </body>
    </html>
    """

    component_height = 100 + len(weeks) * 85

    components.html(
        calendar_html,
        height=component_height,
        scrolling=False
    )

    st.divider()

    # ------------------------------------------
    # SELECTED DATE ACTIVITIES
    # ------------------------------------------

    st.subheader("📌 Activities for Selected Date")

    selected_events = events.get(selected_date, [])

    if not selected_events:

        st.info("No activities scheduled or completed on this date.")

    else:

        for event in selected_events:

            if event["type"] == "Task":

                with st.container(border=True):

                    st.markdown(
                        f"📝 **{event['title']}**"
                    )

                    st.caption(
                        f"Task | {event['priority']} Priority"
                    )

                    if event["status"] == "Completed":
                        st.success("Completed")
                    else:
                        st.warning("Pending")

            elif event["type"] == "Goal":

                with st.container(border=True):

                    st.markdown(
                        f"🎯 **{event['title']}**"
                    )

                    st.caption("Goal target date")

                    st.write(
                        f"Status: {event['status']}"
                    )

            else:

                with st.container(border=True):

                    st.markdown(
                        f"🔥 **{event['title']}**"
                    )

                    st.success("Habit completed")
