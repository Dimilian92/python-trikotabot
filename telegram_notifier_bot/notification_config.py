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
            "Good morning ☀️ Time to check in and shine today.",
            "Rise and slay 💼 Please check in, queen.",
            "Tiny reminder: check in and go be amazing ✨",
            "New day, new wins 🌷 Time to clock in.",
            "Your workday is waiting for its main character — check in 💖",
            "Friendly little nudge: time to check in and sparkle.",
            "Coffee? Maybe. Check-in? Definitely ☕✨",
        ),
        days=WEEKDAYS,
        times=("09:10",),
    ),
    NotificationRule(
        name="lyda_lunch_in",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Lunch o’clock 🍽️ Time to check out and enjoy your yummy break.",
            "Pause, breathe, snack, recharge 💕 Please check out for lunch.",
            "Your lunch break is calling, gorgeous — time to check out 🌮",
            "Midday reset mode: ON ✨ Please check out for lunch.",
            "Go feed the brilliant brain 🧠💖 Time to clock out for lunch.",
            "Lunch break unlocked 🍱 Check out and enjoy.",
            "A gentle reminder from your tiny bot bestie: lunch time, check out 🌸",
        ),
        days=WEEKDAYS,
        times=("12:00",),
    ),
    NotificationRule(
        name="lyda_lunch_out",
        mentions=("@LidiyaBabyak",),
        messages=(
            "Welcome back, superstar ✨ Time to check in after lunch.",
            "Lunch break complete — let’s do this 💪 Please check in.",
            "Hope that was delicious 🍓 Time to clock back in.",
            "Back to business, but still fabulous 💼✨ Check in, please.",
            "Your post-lunch comeback starts now — time to check in 🌷",
            "Recharge complete 🔋 Please check back in.",
            "Tiny nudge: lunch is over, queen. Time to check in 💖",
        ),
        days=WEEKDAYS,
        times=("13:00",),
    ),
    NotificationRule(
        name="lyda_check_out",
        mentions=("@LidiyaBabyak",),
        messages=(
            "You did amazing today 💖 Time to check out and enjoy your evening.",
            "Workday complete, queen 👑 Please clock out and go relax.",
            "That’s enough brilliance for one day ✨ Time to check out.",
            "Go be cozy, you earned it 🌙 Please check out.",
            "Another day, another slay 💅 Time to clock out.",
            "Wrap-up time, superstar 🌸 Check out and enjoy your evening.",
            "Mission accomplished ✅ Time to check out and switch to happy mode.",
        ),
        days=WEEKDAYS,
        times=("18:00",),
    ),
    NotificationRule(
        name="lyda_collagen",
        mentions=("@LidiyaBabyak", "@vi_vi_es"),
        messages=(
            "Collagen fairy is here 🧚‍♀️ Time for a little sip.",
            "Glow reminder ✨ Please take your collagen now.",
            "Beauty potion time 💖 One quick collagen sip.",
            "Friendly sparkly nudge: collagen o’clock 🌸",
            "Sip sip hooray 🥤 Time for collagen.",
            "Tiny reminder for future radiance ✨ Take your collagen now.",
            "Girls, it’s glow-up maintenance time 💅 Collagen sip, please.",
        ),
        days=WEEKDAYS,
        times=("11:00",),
    ),
)
