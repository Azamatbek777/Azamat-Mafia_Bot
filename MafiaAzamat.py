# ================= PROFESSIONAL MAFIA TELEGRAM BOT =================
# python-telegram-bot v20+
# Night/Day (kill/heal/check) + Admin panel + Statistika + Til sozlamalari (UZ/RU/EN) + Timer

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import random, asyncio
from collections import Counter, defaultdict

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"  # Telegram bot tokeningizni yozing

# ================= DATA =================
games = {}
chat_lang = defaultdict(lambda: "uz")
admins = set()  # admin user_id lar
paid_rooms = set()
stats = defaultdict(lambda: {"games": 0, "wins": 0})
timers = defaultdict(lambda: {"day": 60, "night": 30})  # default sekundlarda

ROLES = ["Don", "Mafia", "Mafia", "Komissar", "Shifokor"]

LANG = {
    "uz": {
        "night": "🌙 KECHA",
        "day": "🌞 KUN",
        "join": "➕ Qo‘shilish ({count})",
        "begin": "▶️ Boshlash",
        "settings": "⚙️ Sozlamalar",
        "need5": "❌ Kamida 5 o‘yinchi kerak",
        "joined": "✅ Siz o‘yinga qo‘shildingiz",
        "already": "❌ Siz allaqachon o‘yindasiz",
        "started": "🎉 O‘yin boshlandi!",
        "vote": "🗳 Ovoz bering",
        "killed": "☠️ O‘ldirildi",
        "saved": "💉 Shifokor saqlab qoldi",
        "checked": "🕵️ Tekshirildi",
        "admin": "👑 Admin panel",
        "stats": "📊 Statistika",
        "paid": "💰 Pullik xona",
        "winner": "🏆 O‘yin yakunlandi! G‘oliblar: {}",
        "night_msg": "🌙 KECHA boshlandi. Maxfiy harakatlar qilinmoqda...",
        "day_msg": "🌞 KUN boshlandi. Ovoz berish davom etmoqda..."
    },
    "ru": {
        "night": "🌙 НОЧЬ",
        "day": "🌞 ДЕНЬ",
        "join": "➕ Присоединиться ({count})",
        "begin": "▶️ Начать",
        "settings": "⚙️ Настройки",
        "need5": "❌ Нужно минимум 5 игроков",
        "joined": "✅ Вы присоединились к игре",
        "already": "❌ Вы уже в игре",
        "started": "🎉 Игра началась!",
        "vote": "🗳 Голосуйте",
        "killed": "☠️ Убит",
        "saved": "💉 Врач спас",
        "checked": "🕵️ Проверено",
        "admin": "👑 Панель администратора",
        "stats": "📊 Статистика",
        "paid": "💰 Платная комната",
        "winner": "🏆 Игра окончена! Победители: {}",
        "night_msg": "🌙 Ночь началась. Совершаются секретные действия...",
        "day_msg": "🌞 День начался. Голосование продолжается..."
    },
    "en": {
        "night": "🌙 NIGHT",
        "day": "🌞 DAY",
        "join": "➕ Join ({count})",
        "begin": "▶️ Start",
        "settings": "⚙️ Settings",
        "need5": "❌ Minimum 5 players required",
        "joined": "✅ You joined the game",
        "already": "❌ You are already in the game",
        "started": "🎉 Game started!",
        "vote": "🗳 Vote",
        "killed": "☠️ Killed",
        "saved": "💉 Doctor saved",
        "checked": "🕵️ Checked",
        "admin": "👑 Admin panel",
        "stats": "📊 Statistics",
        "paid": "💰 Paid room",
        "winner": "🏆 Game over! Winners: {}",
        "night_msg": "🌙 NIGHT has begun. Secret actions are happening...",
        "day_msg": "🌞 DAY has begun. Voting is ongoing..."
    }
}

# ================= GAME CLASS =================
class Game:
    def __init__(self, chat):
        self.chat = chat
        self.players = []  # (id, name)
        self.roles = {}
        self.alive = set()
        self.phase = "lobby"
        self.votes = {}
        self.night = {"kill": None, "heal": None, "check": None}

    def name(self, uid):
        for i, n in self.players:
            if i == uid:
                return f"[{n}](tg://user?id={uid})"
        return "?"

# ================= MENUS =================
def main_menu(chat_id=None):
    lang = LANG[chat_lang[chat_id]] if chat_id else LANG["uz"]
    g = games.get(chat_id)
    count = len(g.players) if g else 0
    join_text = lang["join"].format(count=count)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(join_text, callback_data="join"), InlineKeyboardButton(lang["begin"], callback_data="begin")],
        [InlineKeyboardButton(lang["settings"], callback_data="settings"), InlineKeyboardButton(lang["stats"], callback_data="stats")]
    ])

def settings_menu(chat_id=None):
    timer = timers[chat_id] if chat_id else {"day": 60, "night": 30}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 Uzbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇷🇺 Russian", callback_data="lang:ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(f"⏱ Tun: {timer['night']}s", callback_data="timer_night"),
         InlineKeyboardButton(f"⏱ Kun: {timer['day']}s", callback_data="timer_day")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 Mafia Bot", reply_markup=main_menu(update.effective_chat.id))

# ================= ADMIN COMMANDS =================
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admins:
        await update.message.reply_text("❌ Siz admin emassiz")
        return
    paid_rooms.add(update.effective_chat.id)
    await update.message.reply_text("💰 Bu xona endi pullik")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games.pop(update.effective_chat.id, None)
    await update.message.reply_text("♻️ O‘yin reset qilindi")

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    user = q.from_user
    data = q.data
    lang = LANG[chat_lang[chat]]

    if data == "join":
        games.setdefault(chat, Game(chat))
        g = games[chat]
        if user.id in [p[0] for p in g.players]:
            return await q.edit_message_text(lang["already"], reply_markup=main_menu(chat))
        g.players.append((user.id, user.full_name))
        await q.edit_message_text(lang["joined"], reply_markup=main_menu(chat))

    elif data == "begin":
        g = games.get(chat)
        if not g or len(g.players) < 5:
            return await q.edit_message_text(lang["need5"], reply_markup=main_menu(chat))

        pool = ROLES.copy()
        while len(pool) < len(g.players):
            pool.append("Tinch aholi")
        random.shuffle(pool)

        for i, (uid, _) in enumerate(g.players):
            g.roles[uid] = pool[i]
            g.alive.add(uid)
            try:
                await context.bot.send_message(uid, f"🎭 Sizning rolingiz: {pool[i]}")
            except:
                pass

        g.phase = "night"
        await context.bot.send_message(chat, lang["night_msg"])
        asyncio.create_task(night_phase(context, chat))

    elif data == "settings":
        await q.edit_message_text("⚙️ Til va taymer sozlamalari:", reply_markup=settings_menu(chat))

    elif data.startswith("lang:"):
        _, l = data.split(":")
        chat_lang[chat] = l
        await q.edit_message_text(f"✅ Til o‘zgartirildi: {l.upper()}", reply_markup=main_menu(chat))

    elif data.startswith("timer_"):
        t_type = "night" if "night" in data else "day"
        timers[chat][t_type] = (timers[chat][t_type] + 10) % 300 or 10
        await q.edit_message_text("⏱ Taymer o‘zgartirildi", reply_markup=settings_menu(chat))

    elif data == "stats":
        s = stats[user.id]
        await q.edit_message_text(f"📊 Statistika:\nO‘yinlar: {s['games']}\nG‘alabalar: {s['wins']}")

# ================= NIGHT CALLBACK =================
async def night_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    g = games.get(chat)
    if not g or g.phase != "night":
        return
    user = q.from_user.id
    action, target = q.data.split(":")
    target = int(target)
    if user not in g.alive:
        return
    role = g.roles[user]
    if action == "kill" and role in ("Mafia", "Don"):
        g.night["kill"] = target
        await q.edit_message_text(f"🔫 Tanlandi: {g.name(target)}")
    elif action == "heal" and role == "Shifokor":
        g.night["heal"] = target
        await q.edit_message_text(f"💉 Saqlandi: {g.name(target)}")
    elif action == "check" and role == "Komissar":
        result = "MAFIA" if g.roles[target] in ("Mafia", "Don") else "TINCH"
        await q.edit_message_text(f"🕵️ Natija: {g.name(target)} — {result}")
    if g.night["kill"] is not None and g.night["heal"] is not None:
        await resolve_night(context, chat)

# ================= VOTE CALLBACK =================
async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    g = games.get(chat)
    if not g or g.phase != "day":
        return
    voter = q.from_user.id
    if voter not in g.alive:
        return
    action, target = q.data.split(":")
    target = int(target)
    g.votes[voter] = target
    await q.edit_message_text(f"✅ Siz {g.name(target)} ga ovoz berdingiz")
    if len(g.votes) == len(g.alive):
        await resolve_day(context, chat)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill|heal|check):"))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern="^vote:"))
    print("✅ Mafia bot FULL ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
