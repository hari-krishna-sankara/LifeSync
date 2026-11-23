
import streamlit as st
import time


def initialize_timer():

    defaults = {
        "timer_mode": "Focus",
        "timer_running": False,
        "timer_end_time": None,
        "timer_remaining": 25 * 60,
        "focus_sessions": 0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def format_time(seconds):

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


def show_focus_timer():

    initialize_timer()

    st.title("⏱️ Focus Timer")
    st.caption("Stay focused, manage your time, and take regular breaks.")

    durations = {
        "Focus": 25,
        "Short Break": 5,
        "Long Break": 15
    }

    st.subheader("Choose Your Session")

    selected_mode = st.selectbox(
        "Timer Mode",
        ["Focus", "Short Break", "Long Break"],
        index=["Focus", "Short Break", "Long Break"].index(
            st.session_state.timer_mode
        ),
        disabled=st.session_state.timer_running
    )

    if selected_mode != st.session_state.timer_mode:

        st.session_state.timer_mode = selected_mode
        st.session_state.timer_remaining = durations[selected_mode] * 60
        st.session_state.timer_end_time = None
        st.rerun()

    # Timer display
    @st.fragment(run_every="1s")
    def timer_display():

        if st.session_state.timer_running:

            remaining = max(
                0,
                int(st.session_state.timer_end_time - time.time())
            )

            st.session_state.timer_remaining = remaining

            if remaining == 0:

                st.session_state.timer_running = False
                st.session_state.timer_end_time = None

                if st.session_state.timer_mode == "Focus":

                    st.session_state.focus_sessions += 1
                    st.success("🎉 Focus session completed! Time for a break.")

                else:
                    st.success("Break completed! Ready to focus again?")

        remaining = st.session_state.timer_remaining

        st.divider()

        st.subheader(f"{st.session_state.timer_mode} Session")

        st.title(format_time(remaining))

        total_seconds = durations[st.session_state.timer_mode] * 60

        progress = 1 - (remaining / total_seconds)

        st.progress(min(max(progress, 0.0), 1.0))

        col1, col2, col3 = st.columns(3)

        with col1:

            if not st.session_state.timer_running:

                if st.button("▶️ Start", use_container_width=True):

                    st.session_state.timer_end_time = (
                        time.time() + st.session_state.timer_remaining
                    )

                    st.session_state.timer_running = True
                    st.rerun()

        with col2:

            if st.session_state.timer_running:

                if st.button("⏸️ Pause", use_container_width=True):

                    st.session_state.timer_remaining = max(
                        0,
                        int(st.session_state.timer_end_time - time.time())
                    )

                    st.session_state.timer_running = False
                    st.session_state.timer_end_time = None
                    st.rerun()

        with col3:

            if st.button("🔄 Reset", use_container_width=True):

                st.session_state.timer_running = False
                st.session_state.timer_end_time = None
                st.session_state.timer_remaining = (
                    durations[st.session_state.timer_mode] * 60
                )

                st.rerun()

    timer_display()

    st.divider()

    st.subheader("🏆 Your Focus Progress")

    st.metric(
        "Completed Focus Sessions",
        st.session_state.focus_sessions
    )

    st.info(
        "💡 Tip: Avoid distractions during focus sessions "
        "and use breaks to refresh your mind."
    )
