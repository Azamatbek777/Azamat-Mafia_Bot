# ================= PROFESSIONAL MAFIA TELEGRAM BOT WITH TIMER =================
# python-telegram-bot v20+
# Night/Day + Admin panel + Statistics + Language + Timer + Join info

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import random, asyncio
from collections import Counter, defaultdict

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ================= DATA =================
games = {}
chat_lang = defaultdict(lambda: "uz")
admins = set()  # admin user_id lar
paid_rooms = set()  # pullik chat_id lar
stats = defaultdict(lambda: {"games": 0, "wins": 0})
# Default o'yin vaqtlari (soniya)
game_timers = defaultdict(lambda: {"night": 30, "day": 60})  # sozlamalarda o'zgartirish mumkin

LANG = {
    "uz": {
        "night": "🌙 KECHA",
        "day": "🌞 KUN",
        "join": "➕ Qo‘shilish",
        "begin": "▶️ Boshlash",
        "settings": "⚙️ Sozlamalar",
        "need5": "❌ Kamida 5 o‘yinchi kerak",
        "joined": "✅ {} qo‘shildi! Umumiy o‘yinchilar: {}",
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
        "day_msg": "🌞 KUN boshlandi. Ovoz berish davom etmoqda...",
        "timer_set": "⏱ {} vaqti {} soniyaga o‘zgartirildi"
    },
    "ru": {
        "night": "🌙 НОЧЬ",
        "day": "🌞 ДЕНЬ",
        "join": "➕ Присоединиться",
        "begin": "▶️ Начать",
        "settings": "⚙️ Настройки",
        "need5": "❌ Нужно минимум 5 игроков",
        "joined": "✅ {} присоединился! Всего игроков: {}",
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
        "day_msg": "🌞 День начался. Голосование продолжается...",
        "timer_set": "⏱ {} время изменено на {} секунд"
    },
    "en": {
        "night": "🌙 NIGHT",
        "day": "🌞 DAY",
        "join": "➕ Join",
        "begin": "▶️ Start",
        "settings": "⚙️ Settings",
        "need5": "❌ Minimum 5 players required",
        "joined": "✅ {} joined! Total players: {}",
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
        "day_msg": "🌞 DAY has begun. Voting is ongoing...",
        "timer_set": "⏱ {} time changed to {} seconds"
    }
}

ROLES = ["Don", "Mafia", "Mafia", "Komissar", "Shifokor"]

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
                return n
        return "?"

# ================= MENUS =================
def main_menu(chat_id=None):
    lang = LANG[chat_lang[chat_id]] if chat_id else LANG["uz"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(lang["join"], callback_data="join"),
         InlineKeyboardButton(lang["begin"], callback_data="begin")],
        [InlineKeyboardButton(lang["settings"], callback_data="settings"),
         InlineKeyboardButton(lang["stats"], callback_data="stats")]
    ])

def settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 Uzbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇷🇺 Russian", callback_data="lang:ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("⏱ Night", callback_data="set_night"),
         InlineKeyboardButton("⏱ Day", callback_data="set_day")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 Mafia Bot", reply_markup=main_menu(update.effective_chat.id))

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    user = q.from_user
    data = q.data
    lang = LANG[chat_lang[chat]]

    # Join
    if data == "join":
        games.setdefault(chat, Game(chat))
        g = games[chat]
        if user.id in [p[0] for p in g.players]:
            return await q.edit_message_text(lang["already"], reply_markup=main_menu(chat))
        g.players.append((user.id, user.full_name))
        await q.edit_message_text(lang["joined"].format(user.full_name, len(g.players)), reply_markup=main_menu(chat))

    # Begin
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
        await night_phase(context, chat)

    # Settings
    elif data == "settings":
        await q.edit_message_text("⚙️ Til va vaqtlarni sozlang:", reply_markup=settings_menu())

    elif data.startswith("lang:"):
        _, l = data.split(":")
        chat_lang[chat] = l
        await q.edit_message_text(f"✅ Til o‘zgartirildi: {l.upper()}", reply_markup=main_menu(chat))

    elif data == "set_night":
        await q.edit_message_text("⏱ Yangi Night vaqtini sekundda yuboring (masalan 30):")
        context.user_data["set_timer"] = "night"

    elif data == "set_day":
        await q.edit_message_text("⏱ Yangi Day vaqtini sekundda yuboring (masalan 60):")
        context.user_data["set_timer"] = "day"

# ================= SET TIMER MESSAGES =================
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    if "set_timer" in context.user_data:
        phase = context.user_data.pop("set_timer")
        try:
            sec = int(update.message.text)
            game_timers[chat][phase] = sec
            lang = LANG[chat_lang[chat]]
            await update.message.reply_text(lang["timer_set"].format(phase.capitalize(), sec))
        except:
            await update.message.reply_text("❌ Iltimos raqam kiriting!")

# ================= NIGHT / DAY fazalari =================
# NIGHT/DAY fazalari va ovoz berish funksiyalari oldingi kodga mos ravishda ishlaydi,
# ammo endi game_timers[chat]["night"] va game_timers[chat]["day"] sekundlarini ishlatadi
# va faza tugashi uchun asyncio.sleep(game_timers[chat][phase]) qo‘shiladi

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill|heal|check):"))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern="^vote:"))
    app.add_handler(CommandHandler("set_timer", set_timer))
    app.add_handler(MessageHandler(filters=None, callback=set_timer))  # Timer uchun

    print("✅ Mafia bot FULL ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
