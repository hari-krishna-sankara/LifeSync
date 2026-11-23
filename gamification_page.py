
import streamlit as st

from gamification import (
    BADGES,
    get_user_progress,
    get_user_achievements,
    get_xp_history
)


def show_gamification_page():

    user_id = st.session_state.user["id"]

    st.title("🏆 Gamification Center")
    st.caption("Earn XP, level up, and celebrate your achievements!")

    # ==================================================
    # LOAD USER PROGRESS
    # ==================================================

    progress_data = get_user_progress(user_id)

    total_xp = progress_data["total_xp"]
    level = progress_data["level"]
    current_xp = progress_data["current_level_xp"]
    next_level_xp = progress_data["next_level_xp"]
    progress = progress_data["progress"]

    achievements = get_user_achievements(user_id)
    xp_history = get_xp_history(user_id, limit=10)

    unlocked_codes = {
        badge["code"] for badge in achievements
    }

    # ==================================================
    # XP OVERVIEW
    # ==================================================

    st.subheader("⭐ Your XP Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("⭐ Total XP", total_xp)

    with col2:
        st.metric("🏆 Current Level", level)

    with col3:
        st.metric(
            "🎖️ Badges Unlocked",
            f"{len(achievements)} / {len(BADGES)}"
        )

    st.divider()

    # ==================================================
    # LEVEL PROGRESS
    # ==================================================

    st.subheader("🚀 Level Progress")

    st.markdown(f"### Level {level}")

    st.progress(progress)

    st.write(
        f"**{current_xp} / {next_level_xp} XP** "
        "toward your next level."
    )

    remaining_xp = next_level_xp - current_xp

    st.info(
        f"🎯 You need {remaining_xp} more XP to reach Level {level + 1}!"
    )

    st.caption(
        "Earn XP by completing tasks, checking in to habits, "
        "and completing goals."
    )

    st.divider()

    # ==================================================
    # ACHIEVEMENTS
    # ==================================================

    st.subheader("🎖️ Achievement Badges")

    st.write(
        f"You have unlocked {len(achievements)} "
        f"out of {len(BADGES)} achievements."
    )

    badge_col1, badge_col2 = st.columns(2)

    for index, (badge_code, badge_info) in enumerate(BADGES.items()):

        unlocked = badge_code in unlocked_codes

        with (badge_col1 if index % 2 == 0 else badge_col2):

            with st.container(border=True):

                if unlocked:

                    st.markdown(
                        f"### {badge_info['icon']} "
                        f"{badge_info['title']}"
                    )

                    st.success("Unlocked!")

                else:

                    st.markdown(
                        f"### 🔒 {badge_info['title']}"
                    )

                    st.caption("Not unlocked yet")

                st.write(badge_info["description"])

    st.divider()

    # ==================================================
    # XP HISTORY
    # ==================================================

    st.subheader("📜 Recent XP History")

    if xp_history:

        for item in xp_history:

            activity = item["activity"]
            xp = item["xp"]
            activity_date = item["date"]

            with st.container(border=True):

                col1, col2 = st.columns([3, 1])

                with col1:

                    if activity == "Task":
                        st.write(f"📝 {activity} completed")

                    elif activity == "Habit":
                        st.write(f"🔥 {activity} check-in")

                    elif activity == "Goal":
                        st.write(f"🎯 {activity} completed")

                    else:
                        st.write(activity)

                    st.caption(str(activity_date))

                with col2:

                    st.markdown(
                        f"### +{xp} XP"
                    )

    else:

        st.info(
            "No XP history yet. Complete a task, habit, or goal "
            "to start earning XP!"
        )
