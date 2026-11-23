
from database import get_connection


# XP rewards
XP_REWARDS = {
    "task": 10,
    "goal": 50,
    "habit": 5
}


# Level calculation
def calculate_level(total_xp):
    return (total_xp // 100) + 1


def xp_for_next_level(level):
    return level * 100


def xp_progress(total_xp):
    level = calculate_level(total_xp)
    current_level_xp = (level - 1) * 100
    next_level_xp = level * 100

    earned = total_xp - current_level_xp
    required = next_level_xp - current_level_xp

    return earned, required


# Create progress record for a user
def initialize_user_progress(user_id):
    conn = get_connection()

    try:
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (user_id)
            VALUES (?)
        """, (user_id,))

        conn.commit()

    finally:
        conn.close()


# Get user's XP and level
def get_user_progress(user_id):
    initialize_user_progress(user_id)

    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT total_xp, level
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        total_xp = row[0]
        level = calculate_level(total_xp)

        # Keep stored level synchronized
        conn.execute("""
            UPDATE user_progress
            SET level = ?
            WHERE user_id = ?
        """, (level, user_id))

        conn.commit()

        earned, required = xp_progress(total_xp)

        return {
            "total_xp": total_xp,
            "level": level,
            "current_level_xp": earned,
            "next_level_xp": required,
            "progress": earned / required if required else 0
        }

    finally:
        conn.close()


# Award XP for an activity
def award_xp(user_id, activity_type, activity_id):
    if activity_type not in XP_REWARDS:
        return False, 0

    xp = XP_REWARDS[activity_type]

    conn = get_connection()

    try:
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (user_id)
            VALUES (?)
        """, (user_id,))

        cursor = conn.execute("""
            INSERT OR IGNORE INTO xp_history (
                user_id,
                activity_type,
                activity_id,
                xp_earned
            )
            VALUES (?, ?, ?, ?)
        """, (user_id, activity_type, activity_id, xp))

        # No XP if this activity was already rewarded
        if cursor.rowcount == 0:
            return False, 0

        conn.execute("""
            UPDATE user_progress
            SET total_xp = total_xp + ?
            WHERE user_id = ?
        """, (xp, user_id))

        total_xp = conn.execute("""
            SELECT total_xp
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,)).fetchone()[0]

        level = calculate_level(total_xp)

        conn.execute("""
            UPDATE user_progress
            SET level = ?
            WHERE user_id = ?
        """, (level, user_id))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    check_achievements(user_id)

    return True, xp


# Available achievement badges
BADGES = {
    "first_task": {
        "title": "Task Starter",
        "description": "Complete your first task.",
        "icon": "🎯"
    },
    "task_master": {
        "title": "Task Master",
        "description": "Complete 10 tasks.",
        "icon": "🏆"
    },
    "first_habit": {
        "title": "Habit Builder",
        "description": "Complete your first habit check-in.",
        "icon": "🔥"
    },
    "habit_master": {
        "title": "Consistency King",
        "description": "Complete 30 habit check-ins.",
        "icon": "💪"
    },
    "first_goal": {
        "title": "Goal Achiever",
        "description": "Complete your first goal.",
        "icon": "⭐"
    },
    "goal_master": {
        "title": "Goal Crusher",
        "description": "Complete 5 goals.",
        "icon": "🚀"
    },
    "xp_100": {
        "title": "Century Club",
        "description": "Earn 100 XP.",
        "icon": "💎"
    },
    "xp_500": {
        "title": "XP Champion",
        "description": "Earn 500 XP.",
        "icon": "👑"
    }
}


# Check and unlock achievements
def check_achievements(user_id):
    conn = get_connection()

    try:
        completed_tasks = conn.execute("""
            SELECT COUNT(*)
            FROM tasks
            WHERE user_id = ? AND completed = 1
        """, (user_id,)).fetchone()[0]

        completed_goals = conn.execute("""
            SELECT COUNT(*)
            FROM goals
            WHERE user_id = ? AND status = 'Completed'
        """, (user_id,)).fetchone()[0]

        habit_checkins = conn.execute("""
            SELECT COUNT(*)
            FROM habit_logs hl
            JOIN habits h ON h.id = hl.habit_id
            WHERE h.user_id = ?
        """, (user_id,)).fetchone()[0]

        total_xp = conn.execute("""
            SELECT total_xp
            FROM user_progress
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        total_xp = total_xp[0] if total_xp else 0

        earned_badges = []

        if completed_tasks >= 1:
            earned_badges.append("first_task")

        if completed_tasks >= 10:
            earned_badges.append("task_master")

        if habit_checkins >= 1:
            earned_badges.append("first_habit")

        if habit_checkins >= 30:
            earned_badges.append("habit_master")

        if completed_goals >= 1:
            earned_badges.append("first_goal")

        if completed_goals >= 5:
            earned_badges.append("goal_master")

        if total_xp >= 100:
            earned_badges.append("xp_100")

        if total_xp >= 500:
            earned_badges.append("xp_500")

        newly_unlocked = []

        for badge_code in earned_badges:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO achievements (
                    user_id,
                    badge_code
                )
                VALUES (?, ?)
            """, (user_id, badge_code))

            if cursor.rowcount > 0:
                newly_unlocked.append(BADGES[badge_code])

        conn.commit()

        return newly_unlocked

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# Get all unlocked badges
def get_user_achievements(user_id):
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT badge_code, unlocked_at
            FROM achievements
            WHERE user_id = ?
            ORDER BY unlocked_at DESC
        """, (user_id,)).fetchall()

        result = []

        for badge_code, unlocked_at in rows:
            badge = BADGES.get(badge_code)

            if badge:
                result.append({
                    "code": badge_code,
                    "title": badge["title"],
                    "description": badge["description"],
                    "icon": badge["icon"],
                    "unlocked_at": unlocked_at
                })

        return result

    finally:
        conn.close()


# Get XP history
def get_xp_history(user_id, limit=10):
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT activity_type, xp_earned, created_at
            FROM xp_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()

        return [
            {
                "activity": row[0].title(),
                "xp": row[1],
                "date": row[2]
            }
            for row in rows
        ]

    finally:
        conn.close()
