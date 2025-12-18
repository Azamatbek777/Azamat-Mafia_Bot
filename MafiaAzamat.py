from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random, asyncio
from collections import Counter, defaultdict

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ================= DATA =================
games = {}
chat_lang = defaultdict(lambda: "uz")
admins = {6698039974}  # o'z Telegram user_id'ingizni yozing
paid_rooms = set()
stats = defaultdict(lambda: {"games": 0, "wins": 0})
timers = defaultdict(lambda: {"day": 60, "night": 30})
users_started = set()  # botga start bosgan foydalanuvchilar
timer_setup = {}  # {chat_id: {"user_id": user_id, "type": "night/day"}}

ROLES = ["Don", "Mafia", "Mafia", "Komissar", "Shifokor"]

LANG = {
    "uz": {
        "night": "🌙 KECHA",
        "day": "🌞 KUN",
        "join": "➕ Qo'shilish ({count})",
        "begin": "▶️ Boshlash",
        "stop": "⏹ To'xtatish",
        "settings": "⚙️ Sozlamalar",
        "need5": "❌ Kamida 5 o'yinchi kerak",
        "joined": "✅ Siz o'yinga qo'shildingiz",
        "already": "❌ Siz allaqachon o'yindasiz",
        "started": "🎉 O'yin boshlandi!",
        "vote": "🗳 Ovoz bering",
        "killed": "☠️ O'ldirildi",
        "saved": "💉 Shifokor saqlab qoldi",
        "checked": "🕵️ Tekshirildi",
        "admin": "👑 Admin panel",
        "stats": "📊 Statistika",
        "paid": "💰 Pullik xona",
        "winner": "🏆 O'yin yakunlandi! G'oliblar: {}",
        "night_msg": "🌙 KECHA boshlandi. Maxfiy harakatlar qilinmoqda...",
        "day_msg": "🌞 KUN boshlandi. Ovoz berish davom etmoqda...",
        "timer_set": "⏱ Taymer o'zgartirildi: {} - {}s",
        "lang_set": "✅ Til o'zgartirildi: {}",
        "timer_input": "⏱ {} vaqtini kiriting (5-300 soniyada):",
        "timer_invalid": "❌ Noto'g'ri son! Faqat 5 dan 300 gacha son kiriting.",
        "timer_canceled": "❌ Taymer sozlash bekor qilindi.",
        "timer_updated": "✅ {} vaqti {} soniyaga sozlandi.",
        "not_in_game": "❌ Siz o'yinda emassiz!",
        "current_timer": "⏱ Joriy vaqtlar:\nTun: {}s\nKun: {}s"
    },
    "ru": {
        "night": "🌙 НОЧЬ",
        "day": "🌞 ДЕНЬ",
        "join": "➕ Присоединиться ({count})",
        "begin": "▶️ Начать",
        "stop": "⏹ Остановить",
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
        "day_msg": "🌞 День начался. Голосование продолжается...",
        "timer_set": "⏱ Таймер изменён: {} - {}s",
        "lang_set": "✅ Язык изменён: {}",
        "timer_input": "⏱ Введите время для {} (5-300 секунд):",
        "timer_invalid": "❌ Неверное число! Введите только число от 5 до 300.",
        "timer_canceled": "❌ Настройка таймера отменена.",
        "timer_updated": "✅ Время {} установлено на {} секунд.",
        "not_in_game": "❌ Вы не в игре!",
        "current_timer": "⏱ Текущее время:\nНочь: {}s\nДень: {}s"
    },
    "en": {
        "night": "🌙 NIGHT",
        "day": "🌞 DAY",
        "join": "➕ Join ({count})",
        "begin": "▶️ Start",
        "stop": "⏹ Stop",
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
        "day_msg": "🌞 DAY has begun. Voting is ongoing...",
        "timer_set": "⏱ Timer set to: {} - {}s",
        "lang_set": "✅ Language changed: {}",
        "timer_input": "⏱ Enter time for {} (5-300 seconds):",
        "timer_invalid": "❌ Invalid number! Enter only number from 5 to 300.",
        "timer_canceled": "❌ Timer setup canceled.",
        "timer_updated": "✅ {} time set to {} seconds.",
        "not_in_game": "❌ You are not in the game!",
        "current_timer": "⏱ Current timers:\nNight: {}s\nDay: {}s"
    }
}

# ================= GAME CLASS =================
class Game:
    def __init__(self, chat):
        self.chat = chat
        self.players = []
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
        [InlineKeyboardButton(lang["stop"], callback_data="stop"), InlineKeyboardButton(lang["settings"], callback_data="settings")]
    ])

def settings_menu(chat_id):
    timer = timers[chat_id]
    lang = LANG[chat_lang[chat_id]]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 Uzbek", callback_data="lang:uz"),
         InlineKeyboardButton("🇷🇺 Russian", callback_data="lang:ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(f"⏱ Tun: {timer['night']}s", callback_data="timer:night"),
         InlineKeyboardButton(f"⏱ Kun: {timer['day']}s", callback_data="timer:day")],
        [InlineKeyboardButton("📊 Joriy vaqtlar", callback_data="show_timers")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]
    ])

def timer_cancel_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="timer_cancel")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_started.add(update.effective_user.id)
    await update.message.reply_text(
        "🎮 Mafia Botga xush kelibsiz!\nO'yinda qatnashish uchun botga /start bosing.",
        reply_markup=main_menu(update.effective_chat.id)
    )

# ================= ADMIN HELP =================
def is_admin(user_id):
    return user_id in admins

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Siz admin emassiz")
        return
    paid_rooms.add(update.effective_chat.id)
    await update.message.reply_text("💰 Bu xona endi pullik")

async def advert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Siz admin emassiz")
        return
    if not context.args:
        await update.message.reply_text("❌ Reklama matnini yozing:\n/advert <matn>")
        return
    ad_text = " ".join(context.args)
    ad_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Batafsil", url="https://t.me/your_channel")]])

    # Shaxsiy chatlar
    for uid in users_started:
        try:
            await context.bot.send_message(uid, f"📢 Reklama:\n\n{ad_text}", reply_markup=ad_button)
        except:
            pass

    # Guruhdagi o'yinlar
    for chat_id in games.keys():
        try:
            await context.bot.send_message(chat_id, f"📢 Reklama:\n\n{ad_text}", reply_markup=ad_button)
        except:
            pass

    await update.message.reply_text("✅ Reklama barcha foydalanuvchilarga yuborildi")

# ================= TIMER FUNCTIONS =================
async def timer_setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE, timer_type: str):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Faqat o'yindagi o'yinchilar vaqtni o'zgartirishi mumkin
    g = games.get(chat_id)
    if g and user_id not in [p[0] for p in g.players]:
        await update.callback_query.answer("❌ Siz o'yinda emassiz!", show_alert=True)
        return
    
    timer_setup[chat_id] = {
        "user_id": user_id,
        "type": timer_type
    }
    
    lang = LANG[chat_lang[chat_id]]
    current_time = timers[chat_id][timer_type]
    
    timer_name = lang["night"] if timer_type == "night" else lang["day"]
    
    await update.callback_query.edit_message_text(
        lang["timer_input"].format(timer_name) + f"\n\n⏱ Joriy vaqt: {current_time}s",
        reply_markup=timer_cancel_menu()
    )

async def handle_timer_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Timer sozlamasi faolmi?
    if chat_id not in timer_setup or timer_setup[chat_id]["user_id"] != user_id:
        return
    
    setup = timer_setup[chat_id]
    timer_type = setup["type"]
    
    try:
        # Matndan sonni ajratib olish
        text = update.message.text.strip()
        seconds = int(text)
        
        # Validation
        if seconds < 5 or seconds > 300:
            await update.message.reply_text(
                LANG[chat_lang[chat_id]]["timer_invalid"],
                reply_markup=timer_cancel_menu()
            )
            return
        
        # Taymerni sozlash
        timers[chat_id][timer_type] = seconds
        
        lang = LANG[chat_lang[chat_id]]
        timer_name = lang["night"] if timer_type == "night" else lang["day"]
        
        # Taymer setup'ni tozalash
        timer_setup.pop(chat_id, None)
        
        # Xabar yuborish
        await update.message.reply_text(
            lang["timer_updated"].format(timer_name, seconds),
            reply_markup=main_menu(chat_id)
        )
        
    except ValueError:
        await update.message.reply_text(
            LANG[chat_lang[chat_id]]["timer_invalid"],
            reply_markup=timer_cancel_menu()
        )

# ================= STOP =================
async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        games.pop(chat_id)
        await update.message.reply_text("⏹ O'yin to'xtatildi", reply_markup=main_menu(chat_id))
    else:
        await update.message.reply_text("❌ Hech qanday o'yin boshlanmagan", reply_markup=main_menu(chat_id))

# ================= CALLBACK =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat = q.message.chat.id
    user = q.from_user
    data = q.data
    lang = LANG[chat_lang[chat]]

    # JOIN
    if data == "join":
        if user.id not in users_started:
            await q.answer("❌ Avvalo botga /start bosing!", show_alert=True)
            return
        games.setdefault(chat, Game(chat))
        g = games[chat]
        if user.id in [p[0] for p in g.players]:
            return await q.edit_message_text(lang["already"], reply_markup=main_menu(chat))
        g.players.append((user.id, user.full_name))
        await q.edit_message_text(lang["joined"], reply_markup=main_menu(chat))

    # BEGIN
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

    # STOP
    elif data == "stop":
        await stop_game(update, context)
        return

    # SETTINGS
    elif data == "settings":
        await q.edit_message_text("⚙️ Til va taymer sozlamalari:", reply_markup=settings_menu(chat))
    
    # BACK TO MAIN
    elif data == "back_to_main":
        await q.edit_message_text("🎮 Asosiy menyu", reply_markup=main_menu(chat))
    
    # LANGUAGE SETTINGS
    elif data.startswith("lang:"):
        _, l = data.split(":")
        chat_lang[chat] = l
        await q.edit_message_text(LANG[chat_lang[chat]]["lang_set"].format(l.upper()), reply_markup=main_menu(chat))
    
    # TIMER SETTINGS
    elif data.startswith("timer:"):
        _, timer_type = data.split(":")
        await timer_setup_start(update, context, timer_type)
    
    # SHOW CURRENT TIMERS
    elif data == "show_timers":
        timer = timers[chat]
        lang = LANG[chat_lang[chat]]
        await q.edit_message_text(
            lang["current_timer"].format(timer["night"], timer["day"]),
            reply_markup=settings_menu(chat)
        )
    
    # TIMER CANCEL
    elif data == "timer_cancel":
        timer_setup.pop(chat, None)
        await q.edit_message_text(lang["timer_canceled"], reply_markup=settings_menu(chat))

# ================= NIGHT / DAY LOGIC =================
async def night_phase(context, chat_id):
    g = games.get(chat_id)
    if not g or g.phase != "night":
        return
    await asyncio.sleep(timers[chat_id]["night"])
    await resolve_night(context, chat_id)

async def resolve_night(context, chat_id):
    g = games.get(chat_id)
    if not g:
        return
    killed = g.night["kill"]
    healed = g.night["heal"]

    if killed and killed != healed:
        g.alive.discard(killed)
        await context.bot.send_message(chat_id, f"☠️ {g.name(killed)} o'ldirildi!")
    elif killed:
        await context.bot.send_message(chat_id, f"💉 {g.name(killed)} saqlab qolindi!")

    g.night = {"kill": None, "heal": None, "check": None}
    g.phase = "day"
    g.votes = {}
    await context.bot.send_message(chat_id, LANG[chat_lang[chat_id]]["day_msg"])
    await asyncio.sleep(timers[chat_id]["day"])
    await resolve_day(context, chat_id)

async def resolve_day(context, chat_id):
    g = games.get(chat_id)
    if not g:
        return
    if g.votes:
        vote_counts = Counter(g.votes.values())
        target = max(vote_counts, key=vote_counts.get)
        g.alive.discard(target)
        await context.bot.send_message(chat_id, f"🗳 {g.name(target)} o'yindan chiqarildi!")
    mafia_alive = [uid for uid in g.alive if g.roles[uid] in ("Mafia","Don")]
    town_alive = [uid for uid in g.alive if g.roles[uid] not in ("Mafia","Don")]
    if not mafia_alive:
        winners = [g.name(uid) for uid in town_alive]
        await context.bot.send_message(chat_id, LANG[chat_lang[chat_id]]["winner"].format(", ".join(winners)))
        games.pop(chat_id)
    elif not town_alive or len(mafia_alive) >= len(town_alive):
        winners = [g.name(uid) for uid in mafia_alive]
        await context.bot.send_message(chat_id, LANG[chat_lang[chat_id]]["winner"].format(", ".join(winners)))
        games.pop(chat_id)
    else:
        g.phase = "night"
        await context.bot.send_message(chat_id, LANG[chat_lang[chat_id]]["night_msg"])
        asyncio.create_task(night_phase(context, chat_id))

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
    if action == "kill" and role in ("Mafia","Don"):
        g.night["kill"] = target
        await q.edit_message_text(f"🔫 Tanlandi: {g.name(target)}")
    elif action == "heal" and role == "Shifokor":
        g.night["heal"] = target
        await q.edit_message_text(f"💉 Saqlandi: {g.name(target)}")
    elif action == "check" and role == "Komissar":
        result = "MAFIA" if g.roles[target] in ("Mafia","Don") else "TINCH"
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

# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Taymer sozlash uchun matnli xabarlarni tekshirish
    if update.message and update.message.text:
        await handle_timer_input(update, context)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("advert", advert))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill|heal|check):"))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern="^vote:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Mafia bot FULL ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
