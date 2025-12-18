# ================= FULL MAFIA TELEGRAM BOT =================
# python-telegram-bot v20+

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import random
import asyncio
from collections import Counter, defaultdict

# ================= TOKEN =================
TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ================= GLOBAL DATA =================
games = {}
admins = set()           # admin user_id
paid_rooms = set()       # premium chat_id
chat_lang = defaultdict(lambda: "uz")
chat_timer = defaultdict(lambda: 30)  # day/night timer (sec)

stats = defaultdict(lambda: {"games": 0, "wins": 0})

ROLES_BASE = ["Don", "Mafia", "Mafia", "Komissar", "Shifokor"]

# ================= LANG =================
LANG = {
    "uz": {
        "menu": "🎩 Mafia o‘yini\n👥 O‘yinchilar: {}/{}",
        "joined": "➕ {name} qo‘shildi",
        "already": "❌ Siz allaqachon o‘yindasiz",
        "need5": "❌ Kamida 5 o‘yinchi kerak",
        "started": "🎮 O‘yin boshlandi!",
        "night": "🌙 KECHA boshlandi",
        "day": "🌞 KUN boshlandi",
        "vote": "🗳 Kimni chiqaramiz?",
        "winner": "🏆 O‘yin tugadi!\nG‘oliblar:\n{}",
        "roles": "\n\n🎭 Rollar:\n{}",
        "stats": "📊 Statistika\nO‘yinlar: {}\nG‘alabalar: {}",
        "settings": "⚙️ Sozlamalar",
        "timer": "⏱ Taymer: {} soniya",
        "lang": "🌐 Til o‘zgartirildi"
    },
    "ru": {
        "menu": "🎩 Игра Mafia\n👥 Игроки: {}/{}",
        "joined": "➕ {name} присоединился",
        "already": "❌ Вы уже в игре",
        "need5": "❌ Нужно минимум 5 игроков",
        "started": "🎮 Игра началась!",
        "night": "🌙 НОЧЬ",
        "day": "🌞 ДЕНЬ",
        "vote": "🗳 Голосование",
        "winner": "🏆 Игра окончена!\nПобедители:\n{}",
        "roles": "\n\n🎭 Роли:\n{}",
        "stats": "📊 Статистика\nИгр: {}\nПобед: {}",
        "settings": "⚙️ Настройки",
        "timer": "⏱ Таймер: {} секунд",
        "lang": "🌐 Язык изменён"
    },
    "en": {
        "menu": "🎩 Mafia Game\n👥 Players: {}/{}",
        "joined": "➕ {name} joined",
        "already": "❌ You are already in",
        "need5": "❌ Minimum 5 players required",
        "started": "🎮 Game started!",
        "night": "🌙 NIGHT",
        "day": "🌞 DAY",
        "vote": "🗳 Vote",
        "winner": "🏆 Game Over!\nWinners:\n{}",
        "roles": "\n\n🎭 Roles:\n{}",
        "stats": "📊 Stats\nGames: {}\nWins: {}",
        "settings": "⚙️ Settings",
        "timer": "⏱ Timer: {} seconds",
        "lang": "🌐 Language changed"
    }
}

# ================= GAME CLASS =================
class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}     # uid: name
        self.roles = {}
        self.alive = set()
        self.phase = "lobby"
        self.votes = {}
        self.night = {}

    def mention(self, uid):
        name = self.players[uid]
        return f"<a href='tg://user?id={uid}'>{name}</a>"

# ================= MENUS =================
def main_menu(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Join", callback_data="join"),
            InlineKeyboardButton("▶ Begin", callback_data="begin")
        ],
        [
            InlineKeyboardButton("⚙ Settings", callback_data="settings"),
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        ]
    ])

def settings_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱ 30s", callback_data="timer:30"),
            InlineKeyboardButton("⏱ 60s", callback_data="timer:60")
        ],
        [
            InlineKeyboardButton("🇺🇿 UZ", callback_data="lang:uz"),
            InlineKeyboardButton("🇷🇺 RU", callback_data="lang:ru"),
            InlineKeyboardButton("🇬🇧 EN", callback_data="lang:en")
        ]
    ])

# ================= SHOW MENU =================
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        try:
            await update.message.delete()
        except:
            pass

        chat = update.effective_chat.id
        games.setdefault(chat, Game(chat))
        g = games[chat]
        lang = LANG[chat_lang[chat]]

        await context.bot.send_message(
            chat,
            lang["menu"].format(len(g.players), "∞"),
            reply_markup=main_menu(chat),
            parse_mode="HTML"
        )

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    user = q.from_user
    lang = LANG[chat_lang[chat]]

    g = games.setdefault(chat, Game(chat))

    # JOIN
    if q.data == "join":
        if user.id in g.players:
            await q.edit_message_text(lang["already"], reply_markup=main_menu(chat))
            return

        g.players[user.id] = user.full_name
        await context.bot.send_message(
            chat,
            lang["joined"].format(name=g.mention(user.id)),
            parse_mode="HTML"
        )
        await q.edit_message_text(
            lang["menu"].format(len(g.players), "∞"),
            reply_markup=main_menu(chat),
            parse_mode="HTML"
        )

    # BEGIN
    elif q.data == "begin":
        if len(g.players) < 5:
            await q.edit_message_text(lang["need5"], reply_markup=main_menu(chat))
            return

        roles = ROLES_BASE.copy()
        while len(roles) < len(g.players):
            roles.append("Tinch")

        random.shuffle(roles)

        for uid, role in zip(g.players.keys(), roles):
            g.roles[uid] = role
            g.alive.add(uid)
            try:
                await context.bot.send_message(uid, f"🎭 Sizning rolingiz: {role}")
            except:
                pass

        g.phase = "night"
        await context.bot.send_message(chat, lang["started"])
        await night_phase(context, chat)

    # SETTINGS
    elif q.data == "settings":
        await q.edit_message_text(lang["settings"], reply_markup=settings_menu())

    elif q.data.startswith("lang:"):
        chat_lang[chat] = q.data.split(":")[1]
        await q.edit_message_text(lang["lang"], reply_markup=main_menu(chat))

    elif q.data.startswith("timer:"):
        chat_timer[chat] = int(q.data.split(":")[1])
        await q.edit_message_text(lang["timer"].format(chat_timer[chat]), reply_markup=main_menu(chat))

    # STATS
    elif q.data == "stats":
        s = stats[user.id]
        await q.edit_message_text(lang["stats"].format(s["games"], s["wins"]))

# ================= NIGHT =================
async def night_phase(context, chat):
    g = games[chat]
    lang = LANG[chat_lang[chat]]
    await context.bot.send_message(chat, lang["night"])
    await asyncio.sleep(chat_timer[chat])
    await day_phase(context, chat)

# ================= DAY =================
async def day_phase(context, chat):
    g = games[chat]
    g.phase = "day"
    g.votes = {}
    lang = LANG[chat_lang[chat]]

    buttons = [
        [InlineKeyboardButton(g.players[uid], callback_data=f"vote:{uid}")]
        for uid in g.alive
    ]

    for uid in g.alive:
        try:
            await context.bot.send_message(
                uid,
                lang["vote"],
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except:
            pass

    await context.bot.send_message(chat, lang["day"])

# ================= VOTE =================
async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    g = games.get(chat)

    voter = q.from_user.id
    target = int(q.data.split(":")[1])

    if voter not in g.alive:
        return

    g.votes[voter] = target

    if len(g.votes) == len(g.alive):
        await resolve_day(context, chat)

# ================= RESOLVE =================
async def resolve_day(context, chat):
    g = games[chat]
    votes = Counter(g.votes.values())
    out = votes.most_common(1)[0][0]
    g.alive.remove(out)

    await context.bot.send_message(
        chat,
        f"☠️ Chiqarildi: {g.players[out]}"
    )

    await check_end(context, chat)

# ================= END =================
async def check_end(context, chat):
    g = games[chat]
    mafia = [u for u in g.alive if g.roles[u] in ("Mafia", "Don")]
    others = [u for u in g.alive if g.roles[u] not in ("Mafia", "Don")]

    if mafia and others:
        await night_phase(context, chat)
        return

    winners = mafia if mafia else others
    names = "\n".join(g.players[u] for u in winners)
    roles = "\n".join(f"{g.players[u]} — {g.roles[u]}" for u in g.players)

    lang = LANG[chat_lang[chat]]

    await context.bot.send_message(
        chat,
        lang["winner"].format(names) + lang["roles"].format(roles)
    )

    for uid in g.players:
        stats[uid]["games"] += 1
        if uid in winners:
            stats[uid]["wins"] += 1

    games.pop(chat)

# ================= ADMIN =================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games.pop(update.effective_chat.id, None)
    await update.message.reply_text("♻ Reset")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, show_menu))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern="^vote:"))
    app.add_handler(CommandHandler("reset", reset))

    print("✅ Mafia bot ishlayapti")
    app.run_polling()

if __name__ == "__main__":
    main()
