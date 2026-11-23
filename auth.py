
import os
import re
import streamlit as st
import bcrypt

from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
from database import get_connection


# ==================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()


# ==================================================
# 2. EMAIL VALIDATION
# ==================================================

def is_valid_email(email):

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(re.match(pattern, email))


# ==================================================
# 3. INITIALIZE AUTHENTICATION
# ==================================================

def initialize_auth():

    cookie_password = os.getenv("COOKIE_PASSWORD")

    if not cookie_password:
        st.error(
            "COOKIE_PASSWORD is missing from your .env file."
        )
        st.stop()

    cookies = EncryptedCookieManager(
        prefix="trackly/",
        password=cookie_password
    )

    if not cookies.ready():
        st.stop()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    # Restore login after browser refresh
    if not st.session_state.authenticated:

        user_id = cookies.get("user_id")

        if user_id:

            conn = get_connection()

            try:
                user = conn.execute(
                    """
                    SELECT id, name, email
                    FROM users
                    WHERE id = ?
                    """,
                    (user_id,)
                ).fetchone()

            finally:
                conn.close()

            if user:

                st.session_state.user = {
                    "id": user[0],
                    "name": user[1],
                    "email": user[2]
                }

                st.session_state.authenticated = True

            else:

                cookies["user_id"] = ""
                cookies.save()

    return cookies


# ==================================================
# 4. REGISTER USER
# ==================================================

def register_user(name, email, password):

    name = name.strip()
    email = email.strip().lower()

    if not name:
        return False, "Please enter your name."

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    conn = get_connection()

    try:

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:
            return False, "Email already registered."

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash)
        )

        conn.commit()

        return True, "Account created successfully!"

    except Exception as e:

        return False, f"Registration failed: {e}"

    finally:
        conn.close()


# ==================================================
# 5. LOGIN USER
# ==================================================

def login_user(email, password):

    email = email.strip().lower()

    conn = get_connection()

    try:

        user = conn.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if user is None:
            return False, "Invalid email or password.", None

        stored_hash = user[3].encode("utf-8")

        if bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash
        ):

            user_data = {
                "id": user[0],
                "name": user[1],
                "email": user[2]
            }

            return True, "Login successful!", user_data

        return False, "Invalid email or password.", None

    finally:
        conn.close()


# ==================================================
# 6. UPDATE PROFILE
# ==================================================

def update_profile(user_id, name, email):

    name = name.strip()
    email = email.strip().lower()

    if not name:
        return False, "Please enter your name."

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    conn = get_connection()

    try:

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
              AND id != ?
            """,
            (email, user_id)
        ).fetchone()

        if existing_user:
            return False, "This email is already registered."

        conn.execute(
            """
            UPDATE users
            SET name = ?, email = ?
            WHERE id = ?
            """,
            (name, email, user_id)
        )

        conn.commit()

        # Update current session
        st.session_state.user["name"] = name
        st.session_state.user["email"] = email

        return True, "Profile updated successfully!"

    except Exception as e:

        return False, f"Profile update failed: {e}"

    finally:
        conn.close()


# ==================================================
# 7. CHANGE PASSWORD
# ==================================================

def change_password(user_id, current_password, new_password):

    if not current_password or not new_password:
        return False, "Please fill in all password fields."

    if len(new_password) < 8:
        return False, "New password must contain at least 8 characters."

    if current_password == new_password:
        return False, "New password must be different from your current password."

    conn = get_connection()

    try:

        user = conn.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if not user:
            return False, "User account not found."

        stored_hash = user[0].encode("utf-8")

        if not bcrypt.checkpw(
            current_password.encode("utf-8"),
            stored_hash
        ):
            return False, "Current password is incorrect."

        new_password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (new_password_hash, user_id)
        )

        conn.commit()

        return True, "Password changed successfully!"

    except Exception as e:

        return False, f"Password change failed: {e}"

    finally:
        conn.close()


# ==================================================
# 8. PROFILE & SETTINGS PAGE
# ==================================================

def show_profile_settings():

    if not st.session_state.get("user"):
        st.warning("Please log in to access your profile.")
        return

    user = st.session_state.user
    user_id = user["id"]

    st.title("⚙️ Profile & Settings")
    st.caption("Manage your personal information and account security.")

    # ==================================================
    # PROFILE INFORMATION
    # ==================================================

    st.subheader("👤 Profile Information")

    st.info(
        "Update your name and email address below."
    )

    with st.form("profile_update_form"):

        name = st.text_input(
            "Full Name",
            value=user["name"]
        )

        email = st.text_input(
            "Email Address",
            value=user["email"]
        )

        profile_submit = st.form_submit_button(
            "Save Profile Changes",
            use_container_width=True
        )

        if profile_submit:

            success, message = update_profile(
                user_id,
                name,
                email
            )

            if success:
                st.success(message)
                st.rerun()

            else:
                st.error(message)

    st.divider()

    # ==================================================
    # CHANGE PASSWORD
    # ==================================================

    st.subheader("🔐 Change Password")

    st.caption(
        "For security, enter your current password before choosing a new one."
    )

    with st.form("change_password_form"):

        current_password = st.text_input(
            "Current Password",
            type="password"
        )

        new_password = st.text_input(
            "New Password",
            type="password"
        )

        confirm_password = st.text_input(
            "Confirm New Password",
            type="password"
        )

        password_submit = st.form_submit_button(
            "Change Password",
            use_container_width=True
        )

        if password_submit:

            if not current_password or not new_password or not confirm_password:

                st.warning("Please fill in all password fields.")

            elif new_password != confirm_password:

                st.error("New passwords do not match.")

            else:

                success, message = change_password(
                    user_id,
                    current_password,
                    new_password
                )

                if success:
                    st.success(message)
                    st.rerun()

                else:
                    st.error(message)

    st.divider()

    # ==================================================
    # ACCOUNT INFORMATION
    # ==================================================

    st.subheader("📋 Account Information")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Account ID", user_id)

    with col2:
        st.metric("Account Status", "Active")


# ==================================================
# 9. LOGOUT USER
# ==================================================

def logout_user(cookies):

    cookies["user_id"] = ""
    cookies.save()

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.selected_page = "Dashboard"

    st.rerun()


# ==================================================
# 10. LOGIN AND REGISTRATION PAGE
# ==================================================

def show_auth_page(cookies):

    st.title("🎯 Welcome to Trackly")
    st.caption("Track your progress. Stay consistent.")

    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )

    # ==================================================
    # LOGIN TAB
    # ==================================================

    with login_tab:

        st.subheader("Login to your account")

        with st.form("login_form"):

            email = st.text_input(
                "Email Address"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

            if submitted:

                if not email.strip() or not password:

                    st.warning(
                        "Please enter your email and password."
                    )

                else:

                    success, message, user = login_user(
                        email,
                        password
                    )

                    if success:

                        st.session_state.user = user
                        st.session_state.authenticated = True

                        cookies["user_id"] = str(user["id"])
                        cookies.save()

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)

    # ==================================================
    # REGISTRATION TAB
    # ==================================================

    with register_tab:

        st.subheader("Create a new account")

        with st.form("register_form"):

            name = st.text_input(
                "Full Name"
            )

            email = st.text_input(
                "Email Address"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

            if submitted:

                if not name.strip() or not email.strip():

                    st.warning(
                        "Please fill in all required fields."
                    )

                elif len(password) < 8:

                    st.warning(
                        "Password must contain at least 8 characters."
                    )

                elif password != confirm_password:

                    st.error(
                        "Passwords do not match."
                    )

                else:

                    success, message = register_user(
                        name,
                        email,
                        password
                    )

                    if success:

                        st.success(message)

                        st.info(
                            "Your account has been created. "
                            "You can now log in."
                        )

                    else:

                        st.error(message)
