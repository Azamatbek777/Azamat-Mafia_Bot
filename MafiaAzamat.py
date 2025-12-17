from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from collections import Counter
import asyncio
from datetime import datetime, timedelta
import json
import os

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ---------------- SETTINGS -----------------
SETTINGS_FILE = "mafia_settings.json"
DEFAULT_SETTINGS = {
    "night_duration": 60,
    "day_duration": 120,
    "language": "uz",
    "bonus_points": True,
    "vote_from_group": True,
    "auto_kick": True,
}

# ---------------- GLOBAL GAME DATA -----------------
games = {}
settings = DEFAULT_SETTINGS.copy()

# Til matnlari (emojilar olib tashlandi)
TEXTS = {
    "uz": {
        "start": "Mafia O'yini Botiga Xush Kelibsiz!\n\n"
                "Buyruqlar:\n"
                "/join - O'yinga qo'shilish\n"
                "/begin - O'yinni boshlash (min 5 kishi)\n"
                "/players - O'yinchilar ro'yxati\n"
                "/status - O'yin holati\n"
                "/next - Keyingi bosqich\n"
                "/stop - O'yinni to'xtatish\n"
                "/rules - O'yin qoidalari\n"
                "/settings - Sozlamalar\n\n"
                "Eslatma: Rollar shaxsiy xabarlarda yuboriladi!",
        "join_button": "O'yinga Qo'shilish",
        "vote_button": "Ovoz berish",
        "back_to_group": "Guruhga qaytish",
        "back_to_bot": "Botga qaytish",
        "vote_in_group": "Guruhda ovoz berish",
        "vote_in_private": "Shaxsiy ovoz berish",
        "settings_menu": "SOZLAMALAR\n\n"
                        "1 Tungi vaqt: {} sekund\n"
                        "2 Kunduzgi vaqt: {} sekund\n"
                        "3 Til: O'zbek\n"
                        "4 Bonus ballar: {}\n"
                        "5 Guruhda ovoz berish: {}\n"
                        "6 Avto-chiqarish: {}",
        "settings_options": [
            ["Tungi vaqtni o'zgartir", "set_night"],
            ["Kunduzgi vaqtni o'zgartir", "set_day"],
            ["Tilni o'zgartir", "set_language"],
            ["Bonus ballar", "toggle_bonus"],
            ["Guruhda ovoz", "toggle_group_vote"],
            ["Avto-chiqarish", "toggle_auto_kick"],
            ["Orqaga", "back_to_main"]
        ],
        "joined": "{} o'yinga qo'shildi!\nJami: {} ta\nMinimal: 5 ta",
        "already_joined": "Siz allaqachon qo'shilgansiz yoki o'yin boshlangan!",
        "not_enough": "Kamida 5 ta o'yinchi kerak!\nHozir: {} ta\nYetishmayotgan: {} ta",
        "game_started": "O'YIN BOSHLANDI!\n\nO'yinchilar: {} ta\n\nRollar shaxsiy xabarlarda yuborildi!",
        "night_start": "KECHA #{} BOSHLANDI!\n\nMaxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\nVaqt: {} soniya",
        "day_start": "KUN #{} BOSHLANDI!\n\nEndi ovoz beramiz – kimni chiqarish kerak?\n\nTirik o'yinchilar: {} ta\nOvoz berish vaqti: {} soniya\nVaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!",
        "role_assigned": "Sizning rolingiz: {}\n\nO'yinchilar: {} ta\nBoshqalarning rollari o'yin oxirigacha sir saqlanadi!\n\nO'yinchilar:\n{}",
        "mafia_team": "Mafia jamoa a'zolari:\n{}\n\nFaqat siz va bu odamlar bir-birlaringizni mafia ekanligingizni bilasiz!",
        "vote_menu": "Kimni chiqarishni xohlaysiz?\n\nPastdagi tugmalardan birini tanlang:\nVaqt: {} soniya",
        "vote_cast": "{} -> {}",
        "vote_none": "{} -> hech kimga ovoz bermadi",
        "vote_stats": "Ovoz berdi: {}/{} ta\nQolgan vaqt: {:02d}:{:02d}",
        "time_up": "Vaqt tugadi! Ovoz bermaganlar:\n{}",
        "vote_results": "KUN #{} OVOZ NATIJALARI:\n\nHisobot:\n{}\n\nEng ko'p ovoz: {}",
        "lynched": "{} chiqarildi (linch)!\nRol sir saqlanmoqda...",
        "night_results": "KECHA #{} NATIJASASI:\n\n{}",
        "killed": "{} kechasi o'ldirildi!",
        "healed": "Shifokor mafianing qurbonini davoladi!",
        "peaceful": "Hech kim o'lmadi, kecha tinch o'tdi.",
        "alive_players": "Tirik o'yinchilar:\n{}",
        "citizen_win": "TINCH AHOLI G'ALABA QOZONDI!\n\nG'olib o'yinchilar:\n{}\n\nO'YINCHILAR VA ROLLARI:\n\n{}",
        "mafia_win": "MAFIA G'ALABA QOZONDI!\n\nMafia jamoasi:\n{}\n\nO'YINCHILAR VA ROLLARI:\n\n{}",
        "game_stopped": "O'yin to'xtatildi!\n\nO'YINCHILAR RO'YXATI:\n\n{}",
        "kill_question": "{} ni o'ldiramizmi?\n\nO'ldirish -> Ha\nO'ldirmaslik -> Yo'q",
        "kill_vote_result": "O'ldirish ovoz natijasi:\nHa: {} ovoz\nYo'q: {} ovoz\n{}"
    }
}

# Xiva shahri rasmlari (Tun va Kun)
GIFS = {
    "night": [
        "https://telegra.ph/file/5e4b8d9e8c9d8e8d8e8d8.jpg",  # Xiva tungi 1
        "https://telegra.ph/file/4d3b2a1e0f9e8d7c6b5a4.jpg",  # Xiva tungi 2
        "https://telegra.ph/file/3c2b1a0e9f8d7c6b5a4.jpg",    # Xiva tungi 3
    ],
    "day": [
        "https://telegra.ph/file/6e5d4c3b2a1e0f9e8d7.jpg",    # Xiva kunduz 1
        "https://telegra.ph/file/7f6e5d4c3b2a1e0f9e8.jpg",    # Xiva kunduz 2
        "https://telegra.ph/file/8f7e6d5c4b3a2e1f0f9.jpg",    # Xiva kunduz 3
    ]
}

ROLES = {
    "Mafia": 2,
    "Don": 1,
    "Komissar": 1,
    "Shifokor": 1,
    "Tinch aholi": 6
}

# ---------------- HELPER FUNCTIONS -----------------
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                settings.update(loaded)
        except:
            pass

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_text(key, lang=None):
    if lang is None:
        lang = settings.get("language", "uz")
    return TEXTS.get(lang, TEXTS["uz"]).get(key, key)

def create_user_mention(user_id, name, username=None):
    """Profil havolasini yaratish (HTML format)"""
    if username:
        return f'<a href="tg://user?id={user_id}">{name}</a> (@{username})'
    return f'<a href="tg://user?id={user_id}">{name}</a>'

# ---------------- GAME CLASS -----------------
class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = []  # (user_id, name, username, mention, bonus)
        self.roles = {}
        self.alive = set()
        self.started = False
        self.phase = "day"
        self.night_actions = {"mafia_kill": None, "heal": None, "check": None}
        self.votes = {}
        self.vote_messages = {}
        self.day_count = 1
        self.timer_task = None
        self.vote_end_time = None
        self.join_button_message_id = None
        self.group_vote_message_id = None
        self.mafia_kill_votes = {}  # {player_id: "yes"/"no"}
        self.kill_target = None  # O'ldirish uchun tanlangan odam
       
    def add_player(self, uid, name, username=None):
        if self.started:
            return False
        if uid not in [p[0] for p in self.players]:
            mention = create_user_mention(uid, name, username)
            bonus = 0
            if settings.get("bonus_points", True):
                bonus = random.randint(1, 10)
            self.players.append((uid, name, username, mention, bonus))
            return True
        return False
    
    def get_player_mention(self, uid):
        for pid, name, username, mention, bonus in self.players:
            if pid == uid:
                return mention
        return f'<a href="tg://user?id={uid}">Noma\'lum</a>'
    
    def get_player_name(self, uid):
        for pid, name, username, mention, bonus in self.players:
            if pid == uid:
                return name
        return "Noma'lum"
    
    def get_player_info(self, uid):
        for pid, name, username, mention, bonus in self.players:
            if pid == uid:
                return mention
        return "Noma'lum"
    
    def get_players_list(self):
        players_text = ""
        for i, (uid, name, username, mention, bonus) in enumerate(self.players, 1):
            alive = "Tirik" if uid in self.alive else "O'lik"
            bonus_text = f" (+{bonus})" if bonus > 0 else ""
            players_text += f"{i}. {mention} ({alive}){bonus_text}\n"
        return players_text
    
    def assign_roles(self):
        pool = []
        for role, count in ROLES.items():
            pool.extend([role] * count)
        extra_citizens = len(self.players) - len(pool)
        if extra_citizens > 0:
            pool.extend(["Tinch aholi"] * extra_citizens)
        random.shuffle(pool)
        self.roles = {self.players[i][0]: pool[i] for i in range(len(self.players))}
        self.alive = set(self.roles.keys())
    
    def cancel_timer(self):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

# --------------- COMMAND HANDLERS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = settings.get("language", "uz")
    keyboard = [
        [InlineKeyboardButton(get_text("join_button", lang), callback_data="join_game")],
        [InlineKeyboardButton("Qoidalar", callback_data="rules"),
         InlineKeyboardButton("O'yinchilar", callback_data="players")],
        [InlineKeyboardButton("Holat", callback_data="status"),
         InlineKeyboardButton("Sozlamalar", callback_data="settings")]
    ]
    
    await update.message.reply_text(
        get_text("start", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = settings.get("language", "uz")
    keyboard = []
    
    for text, callback in get_text("settings_options", lang):
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    status_text = "Yoqilgan" if settings.get("bonus_points", True) else "O'chirilgan"
    group_vote_text = "Yoqilgan" if settings.get("vote_from_group", True) else "O'chirilgan"
    auto_kick_text = "Yoqilgan" if settings.get("auto_kick", True) else "O'chirilgan"
    
    message = get_text("settings_menu", lang).format(
        settings["night_duration"],
        settings["day_duration"],
        status_text,
        group_vote_text,
        auto_kick_text
    )
    
    if update.message:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        games[chat_id] = Game(chat_id)
    
    game = games[chat_id]
    
    if game.add_player(user.id, user.full_name, user.username):
        await update_join_button(context, chat_id, lang)
        
        await update.message.reply_text(
            get_text("joined", lang).format(user.full_name, len(game.players)),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(get_text("already_joined", lang))

async def update_join_button(context: ContextTypes.DEFAULT_TYPE, chat_id: int, lang: str):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    if game.join_button_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game.join_button_message_id)
        except:
            pass
    
    keyboard = [
        [InlineKeyboardButton(get_text("join_button", lang), callback_data="join_game")],
        [InlineKeyboardButton(get_text("back_to_group", lang), url=f"https://t.me/{context.bot.username}")]
    ]
    
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"O'yinchilar: {len(game.players)} ta\nMinimal: 5 ta\n\n"
             f"O'yinga qo'shilish uchun tugmani bosing!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    game.join_button_message_id = message.message_id

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if update.callback_query:
        chat_id = update.callback_query.message.chat.id
    
    if chat_id not in games:
        message = "Hozircha o'yin yo'q. Avval /join buyrug'i bilan qo'shiling!"
        if update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.message.reply_text(message, parse_mode='HTML')
        return
    
    game = games[chat_id]
    
    if not game.players:
        message = "Hozircha o'yinchilar yo'q."
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.reply_text(message)
        return
    
    players_text = f"O'YINCHILAR RO'YXATI:\n\n"
    players_text += f"Jami: {len(game.players)} ta o'yinchi\n\n"
    players_text += game.get_players_list()
    players_text += f"\nMinimal o'yinchilar: 5 ta"
    
    keyboard = [[InlineKeyboardButton(get_text("back_to_group", lang), url=f"https://t.me/{context.bot.username}")]]
    
    if update.message:
        await update.message.reply_text(players_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.reply_text(players_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        await update.message.reply_text("Avval o'yinchilar /join qilishi kerak!")
        return
    
    game = games[chat_id]
    
    if len(game.players) < 5:
        await update.message.reply_text(
            get_text("not_enough", lang).format(len(game.players), 5 - len(game.players))
        )
        return
    
    if game.started:
        await update.message.reply_text("O'yin allaqachon boshlangan!")
        return
    
    game.started = True
    game.assign_roles()
    
    if game.join_button_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game.join_button_message_id)
            game.join_button_message_id = None
        except:
            pass
    
    await update.message.reply_text(
        get_text("game_started", lang).format(len(game.players))
    )
    
    for uid, name, username, mention, bonus in game.players:
        role = game.roles.get(uid, "Noma'lum")
        try:
            players_list = "\n".join([f"• {pmention}" for _, _, _, pmention, _ in game.players])
            role_text = get_text("role_assigned", lang).format(role, len(game.players), players_list)
            
            if bonus > 0:
                role_text += f"\n\nBonus ballaringiz: +{bonus}"
            
            await context.bot.send_message(
                chat_id=uid,
                text=role_text,
                parse_mode='HTML'
            )
            
            if role in ["Mafia", "Don"]:
                mafia_members = []
                for player_id, _, _, player_mention, _ in game.players:
                    if player_id != uid and game.roles.get(player_id) in ["Mafia", "Don"]:
                        mafia_members.append(player_mention)
                
                if mafia_members:
                    mafia_list = "\n".join([f"• {member}" for member in mafia_members])
                    await context.bot.send_message(
                        chat_id=uid,
                        text=get_text("mafia_team", lang).format(mafia_list),
                        parse_mode='HTML'
                    )
        except Exception as e:
            print(f"Xato {name} ga rol yuborishda: {e}")
    
    await night_phase(update, context)

# ---------------- NIGHT PHASE ----------------------
async def night_phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        return
    
    game = games[chat_id]
    game.phase = "night"
    game.night_actions = {"mafia_kill": None, "heal": None, "check": None}
    game.votes.clear()
    game.vote_messages.clear()
    game.mafia_kill_votes.clear()
    game.kill_target = None
    
    # Xiva tungi rasmi
    try:
        gif_url = random.choice(GIFS["night"])
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=get_text("night_start", lang).format(game.day_count, settings["night_duration"])
        )
    except:
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("night_start", lang).format(game.day_count, settings["night_duration"])
        )
    
    # Mafia a'zolari uchun o'ldirish tanlash (faqat birinchi mafia)
    mafia_members = [uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
    if mafia_members:
        # Faqat birinchi mafia tanlaydi
        mafia_leader = mafia_members[0]
        keyboard = []
        row = []
        for pid in game.alive:
            if pid != mafia_leader:
                player_name = game.get_player_name(pid)
                row.append(InlineKeyboardButton(f"{player_name[:10]}", callback_data=f"kill_target:{pid}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        
        try:
            await context.bot.send_message(
                chat_id=mafia_leader,
                text="Kimni o'ldirmoqchisiz?\n\nTugmalardan birini tanlang:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Mafia {mafia_leader} ga xabar yuborishda xato: {e}")
    
    # Komissar
    komissar = next((uid for uid in game.alive if game.roles.get(uid) == "Komissar"), None)
    if komissar:
        try:
            keyboard = []
            row = []
            for pid in game.alive:
                if pid != komissar:
                    player_name = game.get_player_name(pid)
                    row.append(InlineKeyboardButton(f"{player_name[:10]}", callback_data=f"check:{pid}"))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            if row:
                keyboard.append(row)
            
            await context.bot.send_message(
                chat_id=komissar,
                text="Kimni tekshirmoqchisiz?\n\nTugmalardan birini tanlang:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Komissar {komissar} ga xabar yuborishda xato: {e}")
    
    # Shifokor
    doctor = next((uid for uid in game.alive if game.roles.get(uid) == "Shifokor"), None)
    if doctor:
        try:
            keyboard = []
            row = []
            for pid in game.alive:
                player_name = game.get_player_name(pid)
                row.append(InlineKeyboardButton(f"{player_name[:10]}", callback_data=f"heal:{pid}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            await context.bot.send_message(
                chat_id=doctor,
                text="Kimni davolamoqchisiz?\n\nTugmalardan birini tanlang:\nEslatma: O'zingizni ham davolashingiz mumkin!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Shifokor {doctor} ga xabar yuborishda xato: {e}")
    
    game.timer_task = asyncio.create_task(night_timer(context, chat_id))

async def night_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await asyncio.sleep(settings["night_duration"])
    
    if chat_id in games:
        game = games[chat_id]
        if game.phase == "night":
            await context.bot.send_message(
                chat_id=chat_id,
                text="Tungi vaqt tugadi! Natijalar hisoblanmoqda..."
            )
            await resolve_night(context, chat_id)

# ---------------- DAY PHASE ----------------------
async def day_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    game.phase = "day"
    game.votes.clear()
    game.vote_messages.clear()
    game.vote_end_time = datetime.now() + timedelta(seconds=settings["day_duration"])
    
    # Xiva kunduzgi rasmi
    try:
        gif_url = random.choice(GIFS["day"])
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=get_text("day_start", lang).format(game.day_count, len(game.alive), settings["day_duration"])
        )
    except:
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("day_start", lang).format(game.day_count, len(game.alive), settings["day_duration"])
        )
    
    # Ovoz berish tugmalarini yaratish
    keyboard = []
    row = []
    
    for target_uid in game.alive:
        player_name = game.get_player_name(target_uid)
        row.append(InlineKeyboardButton(f"{player_name[:10]}", callback_data=f"vote:{target_uid}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Ovoz bermaslik", callback_data="vote:none")])
    
    # Guruhda ovoz berish imkoniyati
    if settings.get("vote_from_group", True):
        keyboard.append([
            InlineKeyboardButton(get_text("back_to_bot", lang), url=f"https://t.me/{context.bot.username}")
        ])
    
    vote_text = get_text("vote_menu", lang).format(settings["day_duration"])
    
    # Guruhda ovoz berish xabarini yuborish
    if settings.get("vote_from_group", True):
        vote_message = await context.bot.send_message(
            chat_id=chat_id,
            text=vote_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        game.group_vote_message_id = vote_message.message_id
    
    # Har bir o'yinchiga shaxsiy ovoz berish xabari
    for uid in game.alive:
        try:
            private_keyboard = keyboard.copy()
            if game.group_vote_message_id:
                private_keyboard.append([InlineKeyboardButton(get_text("vote_in_group", lang), url=f"https://t.me/c/{str(chat_id)[4:]}/{game.group_vote_message_id}")])
            
            message = await context.bot.send_message(
                chat_id=uid,
                text=vote_text,
                reply_markup=InlineKeyboardMarkup(private_keyboard)
            )
            game.vote_messages[uid] = message.message_id
        except Exception as e:
            print(f"Ovoz xabarini yuborishda xato {uid}: {e}")
    
    game.timer_task = asyncio.create_task(day_timer(context, chat_id))

async def day_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await asyncio.sleep(settings["day_duration"])
    
    if chat_id in games:
        game = games[chat_id]
        if game.phase == "day":
            if settings.get("auto_kick", True):
                non_voters = [uid for uid in game.alive if uid not in game.votes]
                
                if non_voters:
                    kicked_players = []
                    for uid in non_voters:
                        game.alive.discard(uid)
                        mention = game.get_player_mention(uid)
                        kicked_players.append(mention)
                    
                    if kicked_players:
                        kicked_text = get_text("time_up", "uz").format("\n".join(kicked_players))
                        await context.bot.send_message(chat_id=chat_id, text=kicked_text, parse_mode='HTML')
            
            await resolve_day(context, chat_id)

# ---------------- CALLBACK HANDLERS -----------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    lang = settings.get("language", "uz")
    
    if data == "join_game":
        chat_id = query.message.chat.id
        user = query.from_user
        
        if chat_id not in games:
            games[chat_id] = Game(chat_id)
        
        game = games[chat_id]
        
        if game.add_player(user.id, user.full_name, user.username):
            await update_join_button(context, chat_id, lang)
            await query.edit_message_text(
                get_text("joined", lang).format(user.full_name, len(game.players)),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Yangilash", callback_data="join_game")]])
            )
        else:
            await query.answer(get_text("already_joined", lang), show_alert=True)
    
    elif data == "rules":
        await rules_command(update, context)
    
    elif data == "players":
        await players_command(update, context)
    
    elif data == "status":
        await status_command(update, context)
    
    elif data == "settings":
        await settings_command(update, context)
    
    elif data == "set_night":
        await query.edit_message_text(
            "Tungi vaqtni kiriting (soniyada):\n"
            "Masalan: 60, 90, 120\n\n"
            "Joriy vaqt: {} soniya".format(settings["night_duration"])
        )
        context.user_data["waiting_for"] = "night_time"
    
    elif data == "set_day":
        await query.edit_message_text(
            "Kunduzgi vaqtni kiriting (soniyada):\n"
            "Masalan: 120, 180, 240\n\n"
            "Joriy vaqt: {} soniya".format(settings["day_duration"])
        )
        context.user_data["waiting_for"] = "day_time"
    
    elif data == "set_language":
        keyboard = [
            [InlineKeyboardButton("O'zbek", callback_data="lang_uz")],
            [InlineKeyboardButton("Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("English", callback_data="lang_en")],
            [InlineKeyboardButton("Orqaga", callback_data="settings")]
        ]
        await query.edit_message_text(
            "Tilni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("lang_"):
        lang_code = data.split("_")[1]
        settings["language"] = lang_code
        save_settings()
        await query.answer("Til o'zgartirildi!", show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_bonus":
        settings["bonus_points"] = not settings.get("bonus_points", True)
        save_settings()
        status = "Yoqilgan" if settings["bonus_points"] else "O'chirilgan"
        await query.answer(f"Bonus ballar: {status}", show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_group_vote":
        settings["vote_from_group"] = not settings.get("vote_from_group", True)
        save_settings()
        status = "Yoqilgan" if settings["vote_from_group"] else "O'chirilgan"
        await query.answer(f"Guruhda ovoz berish: {status}", show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_auto_kick":
        settings["auto_kick"] = not settings.get("auto_kick", True)
        save_settings()
        status = "Yoqilgan" if settings["auto_kick"] else "O'chirilgan"
        await query.answer(f"Avto-chiqarish: {status}", show_alert=True)
        await settings_command(update, context)
    
    elif data == "back_to_main":
        await start(update, context)
    
    elif data.startswith("kill_target:"):
        # Mafia rahbari o'ldirish uchun odam tanladi
        try:
            target = int(data.split(":")[1])
            game = None
            chat_id = None
            user_id = query.from_user.id
            
            for cid, g in games.items():
                if user_id in g.alive:
                    game = g
                    chat_id = cid
                    break
            
            if game and game.phase == "night":
                game.kill_target = target
                target_mention = game.get_player_mention(target)
                
                # Barcha mafia a'zolariga ovoz berish uchun xabar yuborish
                mafia_members = [uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
                
                for mafia_id in mafia_members:
                    try:
                        keyboard = [
                            [InlineKeyboardButton("Ha", callback_data="kill_yes")],
                            [InlineKeyboardButton("Yo'q", callback_data="kill_no")]
                        ]
                        
                        await context.bot.send_message(
                            chat_id=mafia_id,
                            text=get_text("kill_question", lang).format(target_mention),
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"Xato mafia {mafia_id} ga xabar yuborishda: {e}")
                
                await query.edit_message_text(f"{target_mention} ni o'ldirish tanlandi. Endi barcha mafia a'zolari ovoz beradi.", parse_mode='HTML')
        
        except:
            await query.edit_message_text("Xato!")

async def night_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = settings.get("language", "uz")
    
    # Qaysi o'yinda ekanligini topish
    game = None
    chat_id = None
    for cid, g in games.items():
        if user_id in g.alive:
            game = g
            chat_id = cid
            break
    
    if not game or game.phase != "night":
        await query.edit_message_text("Bu vaqtda harakat qilish mumkin emas!")
        return
    
    data = query.data
    
    if data.startswith("kill_"):
        # Mafia o'ldirish ovozini qabul qilish
        vote = data.split("_")[1]  # "yes" yoki "no"
        game.mafia_kill_votes[user_id] = vote
        
        vote_text = "Ha" if vote == "yes" else "Yo'q"
        await query.edit_message_text(f"Ovozingiz: {vote_text}")
        
        # Barcha mafia ovoz berganini tekshirish
        mafia_members = [uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
        if len(game.mafia_kill_votes) == len(mafia_members):
            # Ovoz natijalarini hisoblash
            yes_votes = sum(1 for v in game.mafia_kill_votes.values() if v == "yes")
            no_votes = len(mafia_members) - yes_votes
            
            if yes_votes > no_votes:
                game.night_actions["mafia_kill"] = game.kill_target
                result_text = f"O'ldirish qarori qabul qilindi. {game.get_player_mention(game.kill_target)} o'ldiriladi."
            else:
                game.night_actions["mafia_kill"] = None
                result_text = "O'ldirish qarori rad etildi. Hech kim o'ldirilmaydi."
            
            # Mafia a'zolariga natijalarni xabar qilish
            for mafia_id in mafia_members:
                try:
                    await context.bot.send_message(
                        chat_id=mafia_id,
                        text=get_text("kill_vote_result", lang).format(yes_votes, no_votes, result_text),
                        parse_mode='HTML'
                    )
                except:
                    pass
    
    elif data.startswith("check:"):
        try:
            target = int(data.split(":")[1])
            if target in game.alive:
                checked_role = game.roles.get(target, "Noma'lum")
                game.night_actions["check"] = target
                target_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{target_mention} ni tekshirdingiz.\nRol: {checked_role}", parse_mode='HTML')
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("Xato!")
    
    elif data.startswith("heal:"):
        try:
            target = int(data.split(":")[1])
            if target in game.alive:
                game.night_actions["heal"] = target
                target_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{target_mention} ni davolash tanlandi.", parse_mode='HTML')
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("Xato!")

async def day_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = settings.get("language", "uz")
    
    # Qaysi o'yinda ekanligini topish
    game = None
    chat_id = None
    for cid, g in games.items():
        if user_id in g.alive:
            game = g
            chat_id = cid
            break
    
    if not game or game.phase != "day":
        await query.edit_message_text("Bu vaqtda ovoz berish mumkin emas!")
        return
    
    data = query.data
    user_mention = game.get_player_mention(user_id)
    
    # Ovozni saqlash
    if data == "vote:none":
        game.votes[user_id] = None
        await query.edit_message_text("Ovoz bermaslik tanlandi.")
        
        # Ovozni guruhga yozish
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("vote_none", lang).format(user_mention),
            parse_mode='HTML'
        )
    else:
        try:
            _, target_str = data.split(":")
            target = int(target_str)
            if target in game.alive:
                game.votes[user_id] = target
                voted_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{voted_mention} ga ovoz berdingiz.", parse_mode='HTML')
                
                # Ovozni guruhga yozish
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=get_text("vote_cast", lang).format(user_mention, voted_mention),
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
                return
        except:
            await query.edit_message_text("Xato!")
            return
    
    # Qolgan vaqtni hisoblash va ko'rsatish
    if game.vote_end_time:
        time_left = game.vote_end_time - datetime.now()
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        if minutes > 0 or seconds > 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=get_text("vote_stats", lang).format(len(game.votes), len(game.alive), minutes, seconds)
            )
    
    # Hammasi ovoz berdimi?
    if len(game.votes) == len(game.alive):
        # Taymerni to'xtatish
        if game.timer_task:
            game.timer_task.cancel()
            game.timer_task = None
        
        await resolve_day(context, chat_id)

# ---------------- MESSAGE HANDLER FOR SETTINGS -----------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for" in context.user_data:
        waiting_for = context.user_data.pop("waiting_for", None)
        text = update.message.text
        
        try:
            value = int(text)
            if value < 30:
                await update.message.reply_text("Vaqt 30 soniyadan kam bo'lmasligi kerak!")
                return
            if value > 300:
                await update.message.reply_text("Vaqt 5 daqiqadan (300 sekund) ko'p bo'lmasligi kerak!")
                return
            
            if waiting_for == "night_time":
                settings["night_duration"] = value
                await update.message.reply_text(f"Tungi vaqt {value} soniyaga o'zgartirildi!")
            elif waiting_for == "day_time":
                settings["day_duration"] = value
                await update.message.reply_text(f"Kunduzgi vaqt {value} soniyaga o'zgartirildi!")
            
            save_settings()
            await settings_command(update, context)
            
        except ValueError:
            await update.message.reply_text("Iltimos, faqat raqam kiriting!")

# ---------------- MAIN ------------------------
def main():
    # Sozlamalarni yuklash
    load_settings()
    
    # Application yaratish
    app = ApplicationBuilder().token(API_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("begin", begin))
    app.add_handler(CommandHandler("players", players_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_game))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("settings", settings_command))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handler (sozlamalar uchun)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Tungi harakatlar
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill_target|kill_yes|kill_no|check|heal):"))
    
    # Kun ovoz berish
    app.add_handler(CallbackQueryHandler(day_vote_callback, pattern="^vote"))
    
    print("Mafia Bot ishga tushdi!")
    print("Buyruqlar:")
    print(" /start - Botni ishga tushirish")
    print(" /join - O'yinga qo'shilish")
    print(" /begin - O'yinni boshlash")
    print(" /players - O'yinchilar ro'yxati")
    print(" /status - O'yin holati")
    print(" /rules - O'yin qoidalari")
    print(" /settings - Sozlamalar")
    print(" /stop - O'yinni to'xtatish")
    
    app.run_polling()

if __name__ == "__main__":
    main()
