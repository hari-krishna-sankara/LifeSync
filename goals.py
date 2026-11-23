
import streamlit as st
from database import get_connection
from gamification import award_xp
from datetime import date, timedelta


# ==================================================
# GOAL DEADLINE REMINDERS
# ==================================================

def get_goal_reminder_category(target_date, status):

    if status == "Completed" or not target_date:
        return None

    try:
        target = date.fromisoformat(str(target_date))
    except (ValueError, TypeError):
        return None

    today = date.today()
    next_week = today + timedelta(days=7)

    if target < today:
        return "Overdue"

    elif target == today:
        return "Due Today"

    elif today < target <= next_week:
        return "Upcoming"

    return None


def show_goal_reminders(goals):

    reminders = {
        "Overdue": [],
        "Due Today": [],
        "Upcoming": []
    }

    for goal in goals:

        goal_id, title, description, target, status = goal

        category = get_goal_reminder_category(
            target,
            status
        )

        if category:
            reminders[category].append(goal)

    total_reminders = sum(
        len(items) for items in reminders.values()
    )

    st.subheader("🔔 Goal Deadline Reminders")

    if total_reminders == 0:

        st.success(
            "🎉 No urgent goal deadlines. Keep moving forward!"
        )

        return

    col1, col2, col3 = st.columns(3)

    col1.metric("Overdue", len(reminders["Overdue"]))
    col2.metric("Due Today", len(reminders["Due Today"]))
    col3.metric("Next 7 Days", len(reminders["Upcoming"]))

    if reminders["Overdue"]:

        st.error("🔴 Overdue Goals")

        for goal in reminders["Overdue"]:

            st.markdown(
                f"- **{goal[1]}** — Target: {goal[3]}"
            )

    if reminders["Due Today"]:

        st.warning("🟠 Goals Due Today")

        for goal in reminders["Due Today"]:

            st.markdown(
                f"- **{goal[1]}** — Complete this goal today!"
            )

    if reminders["Upcoming"]:

        st.info("🟡 Upcoming Goal Deadlines")

        for goal in reminders["Upcoming"]:

            try:
                target = date.fromisoformat(str(goal[3]))
                remaining = (target - date.today()).days
            except (ValueError, TypeError):
                remaining = None

            if remaining is not None:

                st.markdown(
                    f"- **{goal[1]}** — Due in {remaining} day(s) ({goal[3]})"
                )


# ==================================================
# GOAL MANAGEMENT
# ==================================================

def show_goals():

    user_id = st.session_state.user["id"]

    st.title("🎯 Goal Management")
    st.caption("Set your goals and turn your plans into achievements.")

    # ==================================================
    # XP SUCCESS MESSAGE
    # ==================================================

    if "goal_xp_message" in st.session_state:

        st.success(st.session_state["goal_xp_message"])

        st.session_state.pop("goal_xp_message", None)

    # ==================================================
    # ADD NEW GOAL
    # ==================================================

    with st.expander("➕ Create a New Goal", expanded=True):

        with st.form("goal_form"):

            title = st.text_input("Goal Title")

            description = st.text_area("Description")

            target_date = st.date_input(
                "Target Date",
                min_value=date.today()
            )

            submitted = st.form_submit_button("Create Goal")

            if submitted:

                if title.strip():

                    conn = get_connection()

                    try:
                        conn.execute(
                            """
                            INSERT INTO goals
                            (title, description, target_date, user_id)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                title.strip(),
                                description,
                                str(target_date),
                                user_id
                            )
                        )

                        conn.commit()

                    finally:
                        conn.close()

                    st.success("Goal created successfully! 🎉")
                    st.rerun()

                else:
                    st.warning("Please enter a goal title.")

    st.divider()

    # ==================================================
    # FETCH USER GOALS
    # ==================================================

    st.subheader("Your Goals")

    conn = get_connection()

    try:
        goals = conn.execute(
            """
            SELECT id, title, description, target_date, status
            FROM goals
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

    finally:
        conn.close()

    # ==================================================
    # SMART GOAL REMINDERS
    # ==================================================

    show_goal_reminders(goals)

    st.divider()

    if not goals:
        st.info("No goals yet. Create your first goal!")

    # ==================================================
    # DISPLAY EACH GOAL
    # ==================================================

    for goal in goals:

        goal_id = goal[0]
        title = goal[1]
        description = goal[2]
        target = goal[3]
        status = goal[4]

        with st.container(border=True):

            col1, col2 = st.columns([4, 1])

            with col1:

                st.subheader(title)

                if description:
                    st.write(description)

                st.caption(f"🎯 Target date: {target}")
                st.caption(f"Status: {status}")

            with col2:

                if status == "Completed":

                    st.success("Completed")

                else:

                    if st.button(
                        "Mark Complete",
                        key=f"complete_goal_{goal_id}"
                    ):

                        conn = get_connection()

                        try:
                            cursor = conn.execute(
                                """
                                UPDATE goals
                                SET status = ?
                                WHERE id = ?
                                  AND user_id = ?
                                  AND status != 'Completed'
                                """,
                                ("Completed", goal_id, user_id)
                            )

                            conn.commit()

                            goal_updated = cursor.rowcount > 0

                        finally:
                            conn.close()

                        if goal_updated:

                            awarded, xp = award_xp(
                                user_id,
                                "goal",
                                goal_id
                            )

                            if awarded:

                                st.session_state["goal_xp_message"] = (
                                    f"🏆 Goal completed! You earned {xp} XP!"
                                )

                            else:

                                st.session_state["goal_xp_message"] = (
                                    "🏆 Goal completed! XP was already earned."
                                )

                        st.rerun()

            # ==================================================
            # EDIT GOAL
            # ==================================================

            with st.expander("Edit / Delete"):

                with st.form(f"edit_goal_{goal_id}"):

                    new_title = st.text_input(
                        "Goal Title",
                        value=title
                    )

                    new_description = st.text_area(
                        "Description",
                        value=description or ""
                    )

                    try:
                        current_target = date.fromisoformat(target)
                    except (ValueError, TypeError):
                        current_target = date.today()

                    new_target = st.date_input(
                        "Target Date",
                        value=current_target,
                        key=f"date_{goal_id}"
                    )

                    update = st.form_submit_button("Update Goal")

                    if update:

                        if new_title.strip():

                            conn = get_connection()

                            try:
                                conn.execute(
                                    """
                                    UPDATE goals
                                    SET title = ?,
                                        description = ?,
                                        target_date = ?
                                    WHERE id = ? AND user_id = ?
                                    """,
                                    (
                                        new_title.strip(),
                                        new_description,
                                        str(new_target),
                                        goal_id,
                                        user_id
                                    )
                                )

                                conn.commit()

                            finally:
                                conn.close()

                            st.success("Goal updated!")
                            st.rerun()

                        else:
                            st.warning("Goal title cannot be empty.")

                # ==================================================
                # DELETE GOAL
                # ==================================================

                if st.button(
                    "🗑️ Delete Goal",
                    key=f"delete_{goal_id}"
                ):

                    conn = get_connection()

                    try:
                        conn.execute(
                            """
                            DELETE FROM goals
                            WHERE id = ? AND user_id = ?
                            """,
                            (goal_id, user_id)
                        )

                        conn.commit()

                    finally:
                        conn.close()

                    st.success("Goal deleted!")
                    st.rerun()
