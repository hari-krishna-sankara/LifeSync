
import streamlit as st
from database import get_connection
from gamification import award_xp
from datetime import date, timedelta


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def is_overdue(due_date, completed):

    if not due_date or completed:
        return False

    try:
        return date.fromisoformat(str(due_date)) < date.today()
    except (ValueError, TypeError):
        return False


def get_priority_order(priority):

    order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    return order.get(priority, 4)


def get_reminder_category(due_date, completed):

    if not due_date or completed:
        return None

    try:
        task_date = date.fromisoformat(str(due_date))
    except (ValueError, TypeError):
        return None

    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)

    if task_date < today:
        return "Overdue"

    elif task_date == today:
        return "Due Today"

    elif task_date == tomorrow:
        return "Due Tomorrow"

    elif today < task_date <= next_week:
        return "Upcoming"

    return None


# ==================================================
# SMART TASK REMINDERS
# ==================================================

def show_task_reminders(tasks):

    reminders = {
        "Overdue": [],
        "Due Today": [],
        "Due Tomorrow": [],
        "Upcoming": []
    }

    for task in tasks:

        task_id, title, due_date, priority, completed, created_at = task

        category = get_reminder_category(
            due_date,
            completed
        )

        if category:
            reminders[category].append(task)

    total_reminders = sum(
        len(items) for items in reminders.values()
    )

    st.subheader("🔔 Smart Reminders")

    if total_reminders == 0:

        st.success("🎉 You're all caught up! No upcoming task reminders.")

        return

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Overdue", len(reminders["Overdue"]))
    col2.metric("Due Today", len(reminders["Due Today"]))
    col3.metric("Tomorrow", len(reminders["Due Tomorrow"]))
    col4.metric("Next 7 Days", len(reminders["Upcoming"]))

    # Overdue reminders
    if reminders["Overdue"]:

        st.error("🔴 Overdue Tasks")

        for task in reminders["Overdue"]:

            st.markdown(
                f"- **{task[1]}** — Due: {task[2]} — Priority: {task[3]}"
            )

    # Today's reminders
    if reminders["Due Today"]:

        st.warning("🟠 Tasks Due Today")

        for task in reminders["Due Today"]:

            st.markdown(
                f"- **{task[1]}** — Priority: {task[3]}"
            )

    # Tomorrow's reminders
    if reminders["Due Tomorrow"]:

        st.info("🟡 Tasks Due Tomorrow")

        for task in reminders["Due Tomorrow"]:

            st.markdown(
                f"- **{task[1]}** — Priority: {task[3]}"
            )

    # Upcoming reminders
    if reminders["Upcoming"]:

        st.info("🔵 Upcoming Tasks (Next 7 Days)")

        for task in reminders["Upcoming"]:

            st.markdown(
                f"- **{task[1]}** — Due: {task[2]} — Priority: {task[3]}"
            )


# ==================================================
# TASK MANAGEMENT
# ==================================================

def show_tasks():

    user_id = st.session_state.user["id"]

    st.title("📝 Task Management")
    st.caption("Organize your work and get things done.")

    # ==================================================
    # XP SUCCESS MESSAGE
    # ==================================================

    if "task_xp_message" in st.session_state:

        st.success(st.session_state["task_xp_message"])

        st.session_state.pop("task_xp_message", None)

    # ==================================================
    # ADD NEW TASK
    # ==================================================

    with st.expander("➕ Add New Task", expanded=True):

        with st.form("task_form"):

            title = st.text_input("Task Name")

            due_date = st.date_input(
                "Due Date",
                value=date.today()
            )

            priority = st.selectbox(
                "Priority",
                ["High", "Medium", "Low"]
            )

            submitted = st.form_submit_button(
                "Add Task",
                use_container_width=True
            )

            if submitted:

                if not title.strip():

                    st.warning("Please enter a task name.")

                else:

                    conn = get_connection()

                    try:
                        conn.execute("""
                            INSERT INTO tasks (
                                title,
                                due_date,
                                priority,
                                completed,
                                user_id
                            )
                            VALUES (?, ?, ?, 0, ?)
                        """, (
                            title.strip(),
                            due_date.isoformat(),
                            priority,
                            user_id
                        ))

                        conn.commit()

                    finally:
                        conn.close()

                    st.success("Task added successfully!")
                    st.rerun()

    # ==================================================
    # FETCH TASKS
    # ==================================================

    conn = get_connection()

    try:

        tasks = conn.execute("""
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
        """, (user_id,)).fetchall()

    finally:
        conn.close()

    # ==================================================
    # TASK STATISTICS
    # ==================================================

    total_tasks = len(tasks)

    completed_tasks = sum(
        1 for task in tasks if task[4]
    )

    pending_tasks = total_tasks - completed_tasks

    overdue_tasks = sum(
        1 for task in tasks
        if is_overdue(task[2], task[4])
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Tasks", total_tasks)
    col2.metric("Completed", completed_tasks)
    col3.metric("Pending", pending_tasks)
    col4.metric("Overdue", overdue_tasks)

    st.divider()

    # ==================================================
    # SMART REMINDERS
    # ==================================================

    show_task_reminders(tasks)

    st.divider()

    # ==================================================
    # SEARCH AND FILTERS
    # ==================================================

    st.subheader("📋 Your Tasks")

    search = st.text_input(
        "🔍 Search Tasks",
        placeholder="Search by task name..."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        status_filter = st.selectbox(
            "Status",
            ["All", "Pending", "Completed"]
        )

    with col2:

        priority_filter = st.selectbox(
            "Priority",
            ["All", "High", "Medium", "Low"]
        )

    with col3:

        sort_by = st.selectbox(
            "Sort By",
            [
                "Newest First",
                "Oldest First",
                "Priority",
                "Due Date"
            ]
        )

    # ==================================================
    # APPLY FILTERS
    # ==================================================

    filtered_tasks = list(tasks)

    if search:

        filtered_tasks = [
            task for task in filtered_tasks
            if search.lower() in task[1].lower()
        ]

    if status_filter == "Pending":

        filtered_tasks = [
            task for task in filtered_tasks
            if not task[4]
        ]

    elif status_filter == "Completed":

        filtered_tasks = [
            task for task in filtered_tasks
            if task[4]
        ]

    if priority_filter != "All":

        filtered_tasks = [
            task for task in filtered_tasks
            if task[3] == priority_filter
        ]

    # ==================================================
    # SORT TASKS
    # ==================================================

    if sort_by == "Newest First":

        filtered_tasks.sort(
            key=lambda task: task[0],
            reverse=True
        )

    elif sort_by == "Oldest First":

        filtered_tasks.sort(
            key=lambda task: task[0]
        )

    elif sort_by == "Priority":

        filtered_tasks.sort(
            key=lambda task: get_priority_order(task[3])
        )

    elif sort_by == "Due Date":

        filtered_tasks.sort(
            key=lambda task: task[2] or "9999-12-31"
        )

    # ==================================================
    # DISPLAY TASKS
    # ==================================================

    if not filtered_tasks:

        st.info("No tasks found.")

    for task in filtered_tasks:

        (
            task_id,
            task_title,
            task_due_date,
            task_priority,
            completed,
            created_at
        ) = task

        overdue = is_overdue(
            task_due_date,
            completed
        )

        with st.container(border=True):

            col1, col2 = st.columns([4, 1])

            with col1:

                if completed:

                    st.markdown(
                        f"~~**{task_title}**~~"
                    )

                    st.caption("✅ Completed")

                else:

                    st.markdown(
                        f"**{task_title}**"
                    )

                    if overdue:

                        st.error("⚠️ Overdue")

                    else:

                        st.caption("⏳ Pending")

                st.caption(
                    f"📅 Due: {task_due_date or 'Not set'}"
                )

                st.caption(
                    f"Priority: {task_priority}"
                )

            with col2:

                if task_priority == "High":

                    st.error("High")

                elif task_priority == "Medium":

                    st.warning("Medium")

                else:

                    st.success("Low")

            # ==================================================
            # COMPLETE / UNDO
            # ==================================================

            col1, col2, col3 = st.columns(3)

            with col1:

                if not completed:

                    if st.button(
                        "✅ Complete",
                        key=f"complete_{task_id}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        try:

                            cursor = conn.execute("""
                                UPDATE tasks
                                SET completed = 1
                                WHERE id = ?
                                AND user_id = ?
                                AND completed = 0
                            """, (task_id, user_id))

                            conn.commit()

                            task_updated = cursor.rowcount > 0

                        finally:
                            conn.close()

                        if task_updated:

                            awarded, xp = award_xp(
                                user_id,
                                "task",
                                task_id
                            )

                            if awarded:

                                st.session_state["task_xp_message"] = (
                                    f"🎉 Task completed! You earned {xp} XP!"
                                )

                            else:

                                st.session_state["task_xp_message"] = (
                                    "🎉 Task completed! XP was already earned."
                                )

                        st.rerun()

                else:

                    if st.button(
                        "↩️ Undo",
                        key=f"undo_{task_id}",
                        use_container_width=True
                    ):

                        conn = get_connection()

                        try:

                            conn.execute("""
                                UPDATE tasks
                                SET completed = 0
                                WHERE id = ?
                                AND user_id = ?
                            """, (task_id, user_id))

                            conn.commit()

                        finally:
                            conn.close()

                        st.session_state["task_xp_message"] = (
                            "Task moved back to Pending. Previously earned XP is retained."
                        )

                        st.rerun()

            # ==================================================
            # EDIT TASK
            # ==================================================

            with col2:

                with st.popover(
                    "✏️ Edit",
                    use_container_width=True
                ):

                    with st.form(
                        f"edit_form_{task_id}"
                    ):

                        updated_title = st.text_input(
                            "Task Name",
                            value=task_title
                        )

                        try:
                            current_due_date = (
                                date.fromisoformat(task_due_date)
                                if task_due_date
                                else date.today()
                            )
                        except (ValueError, TypeError):
                            current_due_date = date.today()

                        updated_due_date = st.date_input(
                            "Due Date",
                            value=current_due_date
                        )

                        priority_options = [
                            "High",
                            "Medium",
                            "Low"
                        ]

                        updated_priority = st.selectbox(
                            "Priority",
                            priority_options,
                            index=priority_options.index(task_priority)
                            if task_priority in priority_options
                            else 1
                        )

                        update_button = st.form_submit_button(
                            "Save Changes",
                            use_container_width=True
                        )

                        if update_button:

                            if not updated_title.strip():

                                st.warning("Task name cannot be empty.")

                            else:

                                conn = get_connection()

                                try:

                                    conn.execute("""
                                        UPDATE tasks
                                        SET title = ?,
                                            due_date = ?,
                                            priority = ?
                                        WHERE id = ?
                                        AND user_id = ?
                                    """, (
                                        updated_title.strip(),
                                        updated_due_date.isoformat(),
                                        updated_priority,
                                        task_id,
                                        user_id
                                    ))

                                    conn.commit()

                                finally:
                                    conn.close()

                                st.success("Task updated successfully!")
                                st.rerun()

            # ==================================================
            # DELETE TASK
            # ==================================================

            with col3:

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{task_id}",
                    use_container_width=True
                ):

                    conn = get_connection()

                    try:

                        conn.execute("""
                            DELETE FROM tasks
                            WHERE id = ?
                            AND user_id = ?
                        """, (task_id, user_id))

                        conn.commit()

                    finally:
                        conn.close()

                    st.success("Task deleted successfully!")
                    st.rerun()
