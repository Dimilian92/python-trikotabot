from __future__ import annotations

from dataclasses import dataclass


BOT_TIMEZONE = "Europe/Berlin"

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri")


@dataclass(frozen=True, slots=True)
class NotificationRule:
    name: str
    mentions: tuple[str, ...]
    messages: tuple[str, ...]
    days: tuple[str, ...]
    times: tuple[str, ...]


NOTIFICATION_RULES: tuple[NotificationRule, ...] = (
    NotificationRule(
        name="lyda_check_in",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Check-in reminder: time to clock in and start strong.",
            "Good morning, check-in time.",
            "Please clock in now before diving into tasks.",
            "Quick reminder: check in for work.",
            "New day, fresh start, please check in.",
            "Check-in time. Let us get the day moving.",
            "Friendly nudge: clock in now.",
        ),
        days=WEEKDAYS,
        times=("09:10",),
    ),
    NotificationRule(
        name="lyda_lunch_in",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Lunch time. Please check out for your break.",
            "Lunch reminder: clock out now and enjoy your meal.",
            "Time for lunch. Please check out.",
            "Break time is here. Check out and recharge.",
            "Midday reminder: check out for lunch.",
            "Please clock out now for lunch.",
            "Lunch starts now. Quick check-out reminder.",
        ),
        days=WEEKDAYS,
        times=("12:00",),
    ),
    NotificationRule(
        name="lyda_lunch_out",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Lunch break is over. Please check back in.",
            "Welcome back. Time to clock in after lunch.",
            "Break complete. Please check in now.",
            "Post-lunch reminder: check in and continue.",
            "Time to return from lunch and clock in.",
            "Friendly reminder: check in after your break.",
            "Lunch is done. Please check in now.",
        ),
        days=WEEKDAYS,
        times=("13:00",),
    ),
    NotificationRule(
        name="lyda_check_out",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Check-out reminder: great work today, please clock out.",
            "End of day reminder: check out and relax.",
            "Time to wrap up. Please clock out now.",
            "Workday complete. Quick check-out reminder.",
            "Please check out and enjoy your evening.",
            "Evening reminder: clock out for today.",
            "Nice job today. Time to check out.",
        ),
        days=WEEKDAYS,
        times=("18:00",),
    ),
    NotificationRule(
        name="lyda_collagen",
        mentions=("@LidiyaBabyak", "@vi_vi_es"),
        messages=(
            "Collagen reminder: quick sip time.",
            "Time for collagen. One sip now.",
            "Hydration and collagen break right now.",
            "Friendly collagen ping: take it now.",
            "Daily collagen check: please sip now.",
            "Collagen moment: quick and easy.",
            "Do not forget collagen. Sip now.",
        ),
        days=WEEKDAYS,
        times=("11:00",),
    ),
)
