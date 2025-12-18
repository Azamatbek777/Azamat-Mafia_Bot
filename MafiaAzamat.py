# ===============================
# PROFESSIONAL MAFIA TELEGRAM BOT (FULL ROLES)
# Mafia, Doctor, Komissar, Don, Tinch aholi
# python-telegram-bot v20+
# ===============================

import random
import asyncio
from collections import Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ===============================
# GAME STRUCTURE
# ===============================
class MafiaGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}
        self.roles = {}
        self.alive = set()
        self.state = "waiting"
        self.votes = {}
        self.night_actions = {}
        self.round = 0

    def alive_players(self):
        return {uid: self.players[uid] for uid in self.alive}

# ===============================
# GLOBAL STORAGE
# ===============================
games = {}

ROLES = ["Mafia", "Don", "Komissar", "Doctor", "Citizen", "Citizen", "Citizen"]

# ===============================
# COMMANDS WITH BUTTONS
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("🆕 Create Game", callback_data="create")],
        [InlineKeyboardButton("➕ Join Game", callback_data="join")],
        [InlineKeyboardButton("▶️ Begin Game", callback_data="begin")],
        [InlineKeyboardButton("👥 Players", callback_data="players")]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎮 Mafia Royale Bot - Tugmalar bilan o‘ynang", reply_markup=markup)

# ===============================
# GAME BUTTON HANDLERS
# ===============================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat.id

    if query.data == "create":
        if chat_id in games:
            await query.edit_message_text("❗ O‘yin allaqachon mavjud")
            return
        games[chat_id] = MafiaGame(chat_id)
        await query.edit_message_text("🎮 Yangi Mafia o‘yini yaratildi!")

    elif query.data == "join":
        if chat_id not in games:
            await query.edit_message_text("❗ Avval Create tugmasini bosing")
            return
        game = games[chat_id]
        if game.state != "waiting":
            await query.edit_message_text("❗ O‘yin boshlangan")
            return
        game.players[user.id] = user.full_name
        game.alive.add(user.id)
        await query.edit_message_text(f"✅ {user.full_name} o‘yinga qo‘shildi")

    elif query.data == "players":
        game = games.get(chat_id)
        if not game:
            await query.edit_message_text("❗ O‘yin mavjud emas")
            return
        text = "👥 O‘yinchilar:\n" + "\n".join(game.players.values())
        await query.edit_message_text(text)

    elif query.data == "begin":
        game = games.get(chat_id)
        if not game or len(game.players) < 5:
            await query.edit_message_text("❗ Kamida 5 o‘yinchi kerak")
            return
        roles = ROLES.copy()
        random.shuffle(roles)
        for uid, role in zip(game.players.keys(), roles):
            game.roles[uid] = role
            await context.bot.send_message(uid, f"🎭 Sizning rolingiz: {role}")
        game.state = "night"
        game.round = 1
        await night_phase(context, game)

# ===============================
# NIGHT PHASE WITH BUTTONS
# ===============================
async def night_phase(context, game: MafiaGame):
    game.votes.clear()
    game.night_actions.clear()
    await context.bot.send_message(game.chat_id, f"🌙 TUN {game.round} - Maxsus rollar harakat qiladi")

    # Mafia & Don action buttons
    mafia_ids = [uid for uid, r in game.roles.items() if r in ["Mafia", "Don"] and uid in game.alive]
    targets_buttons = [InlineKeyboardButton(game.players[uid], callback_data=f"kill_{uid}") for uid in game.alive]
    markup = InlineKeyboardMarkup([targets_buttons[i:i+2] for i in range(0, len(targets_buttons), 2)])
    for mid in mafia_ids:
        await context.bot.send_message(mid, "🔪 Kimni o‘ldiramiz?", reply_markup=markup)

    # Doctor action buttons
    doctor_ids = [uid for uid, r in game.roles.items() if r == "Doctor" and uid in game.alive]
    for did in doctor_ids:
        await context.bot.send_message(did, "💉 Kimni davolaysiz?", reply_markup=markup)

    # Komissar action buttons
    komissar_ids = [uid for uid, r in game.roles.items() if r == "Komissar" and uid in game.alive]
    for kid in komissar_ids:
        await context.bot.send_message(kid, "🕵️ Kim mafia ekanligini tekshirasiz?", reply_markup=markup)

    await asyncio.sleep(20)
    await resolve_night(context, game)

# ===============================
# CALLBACKS FOR NIGHT & DAY
# ===============================
async def night_day_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat.id
    game = games.get(chat_id)
    if not game:
        return

    data = query.data
    if data.startswith("kill_") or data.startswith("vote_"):
        target = int(data.split("_")[1])
        game.votes[target] = game.votes.get(target, 0) + 1
        await query.edit_message_text("✅ Ovoz qabul qilindi")

# ===============================
# RESOLVE NIGHT & DAY
# ===============================
async def resolve_night(context, game: MafiaGame):
    if not game.votes:
        await context.bot.send_message(game.chat_id, "🌅 Hech kim o‘ldirilmadi")
    else:
        victim = Counter(game.votes).most_common(1)[0][0]
        game.alive.remove(victim)
        await context.bot.send_message(game.chat_id, f"💀 {game.players[victim]} o‘ldirildi")
    await day_phase(context, game)

async def day_phase(context, game: MafiaGame):
    game.state = "day"
    await context.bot.send_message(game.chat_id, f"☀️ KUN {game.round} - Muhokama va ovoz berish")

    buttons = [InlineKeyboardButton(game.players[uid], callback_data=f"vote_{uid}") for uid in game.alive]
    markup = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    await context.bot.send_message(game.chat_id, "🗳 Kimni chiqaramiz?", reply_markup=markup)
    await asyncio.sleep(20)
    await resolve_day(context, game)

async def resolve_day(context, game: MafiaGame):
    if not game.votes:
        await context.bot.send_message(game.chat_id, "🤷 Hech kim chiqarilmadi")
    else:
        out = Counter(game.votes).most_common(1)[0][0]
        game.alive.remove(out)
        await context.bot.send_message(game.chat_id, f"🚫 {game.players[out]} o‘yindan chiqarildi")
    await check_winner(context, game)

# ===============================
# WIN CHECK
# ===============================
async def check_winner(context, game: MafiaGame):
    mafia = [uid for uid in game.alive if game.roles[uid] in ["Mafia", "Don"]]
    citizens = [uid for uid in game.alive if game.roles[uid] not in ["Mafia", "Don"]]
    if not mafia:
        await context.bot.send_message(game.chat_id, "🏆 Tinch aholi g‘alaba qozondi!")
        game.state = "ended"
        return
    if len(mafia) >= len(citizens):
        await context.bot.send_message(game.chat_id, "🏆 Mafia g‘alaba qozondi!")
        game.state = "ended"
        return
    game.round += 1
    game.state = "night"
    await night_phase(context, game)

# ===============================
# MAIN
# ===============================
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(create|join|begin|players)$'))
    app.add_handler(CallbackQueryHandler(night_day_callback, pattern='^(kill_|vote_)'))

    print("Mafia bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
