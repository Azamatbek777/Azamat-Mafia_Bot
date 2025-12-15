from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from collections import Counter
import asyncio
from datetime import datetime, timedelta

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ---------------- GLOBAL GAME DATA -----------------
games = {} # chat_id -> Game object

ROLES = {
    "Mafia": 2,
    "Don": 1,
    "Komissar": 1,
    "Shifokor": 1,
    "Tinch aholi": 6
}

# Xiva shahri suratlari (tun va kun)
GIFS = {
    "night": [
        "https://telegra.ph/file/5e4b8d9e8c9d8e8d8e8d8.jpg",
        "https://telegra.ph/file/4d3b2a1e0f9e8d7c6b5a4.jpg",
        "https://telegra.ph/file/3c2b1a0e9f8d7c6b5a4.jpg",
        "https://telegra.ph/file/2b1a0e9f8d7c6b5a4.jpg",
        "https://telegra.ph/file/1a0e9f8d7c6b5a4.jpg"
    ],
    "day": [
        "https://telegra.ph/file/6e5d4c3b2a1e0f9e8d7.jpg",
        "https://telegra.ph/file/7f6e5d4c3b2a1e0f9e8.jpg",
        "https://telegra.ph/file/8f7e6d5c4b3a2e1f0f9.jpg",
        "https://telegra.ph/file/9f8e7d6c5b4a3e2f1f0.jpg",
        "https://telegra.ph/file/0f9e8d7c6b5a4e3f2f1.jpg"
    ]
}

# Yedek GIF'lar
BACKUP_GIFS = {
    "night": [
        "https://media.giphy.com/media/26tknCqiJrBQG6DrW/giphy.gif",
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "https://media.giphy.com/media/3o7aD2sRhnv7oKf0I0/giphy.gif"
    ],
    "day": [
        "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",
        "https://media.giphy.com/media/l0MYJfGZleVbqvaWQ/giphy.gif",
        "https://media.giphy.com/media/26tknCqiJrBQG6DrW/giphy.gif"
    ]
}

# ---------------- GAME CLASS -----------------
class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = [] # list of (user_id, full_name, username, mention)
        self.roles = {} # user_id -> role
        self.alive = set() # set of alive user_ids
        self.started = False
        self.phase = "day" # "day" or "night"
        self.night_actions = {
            "mafia_kill": None,
            "heal": None,
            "check": None
        }
        self.votes = {} # user_id -> voted_for_user_id
        self.vote_messages = {} # user_id -> message_id
        self.day_count = 1
        self.timer_task = None
        self.vote_end_time = None
        self.join_button_message_id = None  # Qo'shilish tugmasi xabar ID si
       
    def add_player(self, uid, name, username=None):
        if self.started:
            return False
        if uid not in [p[0] for p in self.players]:
            # Profil havolasini yaratish
            mention = f"<a href='tg://user?id={uid}'>{name}</a>"
            self.players.append((uid, name, username, mention))
            return True
        return False
    
    def get_player_mention(self, uid):
        """O'yinchi uchun profil havolasini olish"""
        for pid, name, username, mention in self.players:
            if pid == uid:
                return mention
        return f"<a href='tg://user?id={uid}'>Noma'lum</a>"
    
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
    
    def get_player_name(self, uid):
        for pid, name, username, mention in self.players:
            if pid == uid:
                return name
        return "Noma'lum"
    
    def get_player_info(self, uid):
        """O'yinchi haqida to'liq ma'lumot"""
        for pid, name, username, mention in self.players:
            if pid == uid:
                info = f"{mention}"
                if username:
                    info += f" (@{username})"
                return info
        return "Noma'lum"
    
    def get_all_roles_table(self):
        """O'yin tugaganda barcha rollarni ko'rsatish"""
        table = "O'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username, mention in self.players:
            role = self.roles.get(uid, "Noma'lum")
            alive = "Tirik" if uid in self.alive else "O'lik"
            info = f"{mention}"
            table += f"{alive} - {info}\nRol: {role}\n"
            table += "─" * 30 + "\n"
        return table
    
    def get_players_list(self):
        """O'yinchilar ro'yxatini olish"""
        players_text = ""
        for i, (uid, name, username, mention) in enumerate(self.players, 1):
            alive = "Tirik" if uid in self.alive else "O'lik"
            players_text += f"{i}. {mention} ({alive})\n"
        return players_text
    
    def cancel_timer(self):
        """Taymerni to'xtatish"""
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

# --------------- COMMAND HANDLERS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni ishga tushirish"""
    keyboard = [
        [InlineKeyboardButton("Qoidalar", callback_data="rules")],
        [InlineKeyboardButton("O'yinchilar", callback_data="players")],
        [InlineKeyboardButton("Holat", callback_data="status")]
    ]
    
    await update.message.reply_text(
        "Mafia O'yini Botiga Xush Kelibsiz!\n\n"
        "Buyruqlar:\n"
        "/join - O'yinga qo'shilish\n"
        "/begin - O'yinni boshlash (min 5 kishi)\n"
        "/players - O'yinchilar ro'yxati\n"
        "/status - O'yin holati\n"
        "/next - Keyingi bosqich\n"
        "/stop - O'yinni to'xtatish\n"
        "/rules - O'yin qoidalari\n\n"
        "Eslatma: Rollar shaxsiy xabarlarda yuboriladi!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yin qoidalari"""
    rules_text = """
MAFIA O'YINI QOIDALARI

ROLLAR:
• Mafia (2) - Kechasi bir kishini o'ldiradi
• Don (1) - Mafia rahbari
• Komissar (1) - Kechasi bir kishini tekshiradi
• Shifokor (1) - Kechasi bir kishini davolaydi
• Tinch aholi - Ovoz berish orqali mafiani topadi

KECHA (TUN):
1. Mafia - kimni o'ldirishni tanlaydi
2. Komissar - kimni tekshirishni tanlaydi
3. Shifokor - kimni davolashni tanlaydi

KUN (KUNDUZ):
1. Barcha suhbatlashadi
2. Kimni chiqarishni ovoz berishadi
3. Eng ko'p ovoz olgan chiqariladi

G'ALABA:
• Mafia g'alabasi - Mafia soni tinch aholiga teng yoki ko'p bo'lsa
• Tinch aholi g'alabasi - Barcha mafia o'ldirilsa

VAQT:
• Kecha: 1 daqiqa
• Kun: 2 daqiqa
"""
    
    if update.message:
        await update.message.reply_text(rules_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(rules_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
YORDAM

Muammolar:
1. Bot javob bermayapti - /start ni bosing
2. O'yinchi qo'shilmayapti - Guruhda /join buyrug'ini bering
3. Shaxsiy xabar kelmayapti - Botga /start bosganligingizni tekshiring
4. O'yin to'xtab qoldi - /next yoki /stop buyruqlaridan foydalaning

O'ynash:
1. /join - o'yinchi sifatida qo'shiling
2. /begin - o'yin boshlang
3. Shaxsiy xabarlarda harakatlaringizni bajaring
4. O'yinni kuzating!
"""
    
    await update.message.reply_text(help_text)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in games:
        games[chat_id] = Game(chat_id)
    
    game = games[chat_id]
    
    if game.add_player(user.id, user.full_name, user.username):
        # Qo'shilish tugmasini yangilash
        await update_join_button(context, chat_id)
        
        await update.message.reply_text(
            f"{user.full_name} o'yinga qo'shildi!\n"
            f"Jami: {len(game.players)} ta\n"
            f"Minimal: 5 ta"
        )
    else:
        await update.message.reply_text("Siz allaqachon qo'shilgansiz yoki o'yin boshlangan!")

async def update_join_button(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Qo'shilish tugmasini yangilash"""
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    # Eski qo'shilish tugmasi xabarini o'chirish
    if game.join_button_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game.join_button_message_id)
        except:
            pass
    
    # Yangi qo'shilish tugmasi yaratish
    keyboard = [[InlineKeyboardButton("O'yinga Qo'shilish", callback_data="join_game")]]
    
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"O'yinchilar: {len(game.players)} ta\n"
             f"Minimal: 5 ta\n\n"
             f"O'yinga qo'shilish uchun tugmani bosing!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    game.join_button_message_id = message.message_id

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinchilar ro'yxatini ko'rish"""
    chat_id = update.effective_chat.id
    
    # Callback query uchun chat_id ni olish
    if update.callback_query:
        chat_id = update.callback_query.message.chat.id
    
    if chat_id not in games:
        if update.message:
            await update.message.reply_text("Hozircha o'yin yo'q. Avval /join buyrug'i bilan qo'shiling!")
        elif update.callback_query:
            await update.callback_query.message.reply_text("Hozircha o'yin yo'q. Avval /join buyrug'i bilan qo'shiling!")
        return
    
    game = games[chat_id]
    
    if not game.players:
        if update.message:
            await update.message.reply_text("Hozircha o'yinchilar yo'q.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("Hozircha o'yinchilar yo'q.")
        return
    
    players_text = f"O'YINCHILAR RO'YXATI:\n\n"
    players_text += f"Jami: {len(game.players)} ta o'yinchi\n\n"
    players_text += game.get_players_list()
    players_text += f"\nMinimal o'yinchilar: 5 ta"
    
    if update.message:
        await update.message.reply_text(players_text, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.message.reply_text(players_text, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yin holatini ko'rish"""
    chat_id = update.effective_chat.id
    
    # Callback query uchun chat_id ni olish
    if update.callback_query:
        chat_id = update.callback_query.message.chat.id
    
    if chat_id not in games:
        if update.message:
            await update.message.reply_text("Faol o'yin yo'q!")
        elif update.callback_query:
            await update.callback_query.message.reply_text("Faol o'yin yo'q!")
        return
    
    game = games[chat_id]
    
    status_text = f"O'YIN HOLATI:\n\n"
    status_text += f"Faza: {'Kecha' if game.phase == 'night' else 'Kun'} #{game.day_count}\n"
    status_text += f"Tirik o'yinchilar: {len(game.alive)}/{len(game.players)}\n"
    
    if game.phase == "day":
        status_text += f"Ovoz berganlar: {len(game.votes)}/{len(game.alive)}\n"
    
    status_text += f"\nO'yinchi holati:\n"
    status_text += game.get_players_list()
    
    if update.message:
        await update.message.reply_text(status_text, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.message.reply_text(status_text, parse_mode='HTML')

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("Avval o'yinchilar /join qilishi kerak!")
        return
    
    game = games[chat_id]
    
    if len(game.players) < 5:
        await update.message.reply_text(
            f"Kamida 5 ta o'yinchi kerak!\n"
            f"Hozir: {len(game.players)} ta\n"
            f"Yetishmayotgan: {5 - len(game.players)} ta"
        )
        return
    
    if game.started:
        await update.message.reply_text("O'yin allaqachon boshlangan!")
        return
    
    game.started = True
    game.assign_roles()
    
    # Qo'shilish tugmasini o'chirish
    if game.join_button_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=game.join_button_message_id)
            game.join_button_message_id = None
        except:
            pass
    
    await update.message.reply_text(
        f"O'YIN BOSHLANDI!\n\n"
        f"O'yinchilar: {len(game.players)} ta\n\n"
        f"Rollar shaxsiy xabarlarda yuborildi!"
    )
    
    # Har bir o'yinchiga faqat o'z rolini yuboramiz
    for uid, name, username, mention in game.players:
        role = game.roles.get(uid, "Noma'lum")
        try:
            # O'z rolini yuborish
            role_text = f"Sizning rolingiz: {role}\n\n"
            role_text += f"O'yinchilar: {len(game.players)} ta\n"
            role_text += "Boshqalarning rollari o'yin oxirigacha sir saqlanadi!\n\n"
            
            # O'yinchilar ro'yxati (faqat ismlar)
            role_text += "O'yinchilar:\n"
            for pid, pname, pusername, pmention in game.players:
                role_text += f"• {pmention}\n"
            
            await context.bot.send_message(
                chat_id=uid,
                text=role_text,
                parse_mode='HTML'
            )
            
            # Agar Mafia bo'lsa, boshqa mafia a'zolarini ko'rsatish
            if role in ["Mafia", "Don"]:
                mafia_members = []
                for player_id, player_name, player_username, player_mention in game.players:
                    if player_id != uid and game.roles.get(player_id) in ["Mafia", "Don"]:
                        mafia_members.append(player_mention)
                
                if mafia_members:
                    mafia_list = "\n".join([f"• {member}" for member in mafia_members])
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"Mafia jamoa a'zolari:\n{mafia_list}\n\n"
                             f"Faqat siz va bu odamlar bir-birlaringizni mafia ekanligingizni bilasiz!",
                        parse_mode='HTML'
                    )
        except Exception as e:
            print(f"Xato {name} ga rol yuborishda: {e}")
            await update.message.reply_text(f"{name} ga xabar yuborilmadi (botga /start bosilmagan)")
    
    await night_phase(update, context)

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinni to'xtatish"""
    chat_id = update.effective_chat.id
    if chat_id in games:
        game = games[chat_id]
        game.cancel_timer()
        
        # O'yin natijalarini ko'rsatish
        result_text = "O'yin to'xtatildi!\n\n"
        result_text += "O'YINCHILAR RO'YXATI:\n\n"
        
        for uid, name, username, mention in game.players:
            role = game.roles.get(uid, "Noma'lum")
            alive = "Tirik" if uid in game.alive else "O'lik"
            result_text += f"{alive} - {mention}\nRol: {role}\n"
            result_text += "─" * 30 + "\n"
        
        await update.message.reply_text(result_text, parse_mode='HTML')
        
        del games[chat_id]
    else:
        await update.message.reply_text("Faol o'yin yo'q!")

# ---------------- CALLBACK HANDLERS -----------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha callback query'larni boshqarish"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "join_game":
        # Qo'shilish tugmasi bosilganda
        chat_id = query.message.chat.id
        user = query.from_user
        
        if chat_id not in games:
            games[chat_id] = Game(chat_id)
        
        game = games[chat_id]
        
        if game.add_player(user.id, user.full_name, user.username):
            await update_join_button(context, chat_id)
            # Foydalanuvchiga tasdiq xabari
            await query.edit_message_text(
                f"{user.full_name} o'yinga qo'shildi!\n"
                f"Jami o'yinchilar: {len(game.players)} ta",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Yangilash", callback_data="join_game")]])
            )
        else:
            await query.answer("Siz allaqachon qo'shilgansiz!", show_alert=True)
    
    elif data == "rules":
        await rules_command(update, context)
    
    elif data == "players":
        await players_command(update, context)
    
    elif data == "status":
        await status_command(update, context)

# ---------------- NIGHT PHASE ----------------------
async def night_phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        return
    
    game = games[chat_id]
    game.phase = "night"
    game.night_actions = {"mafia_kill": None, "heal": None, "check": None}
    game.votes.clear()
    game.vote_messages.clear()
    
    # Tungi surat yuborish
    try:
        gif_url = random.choice(GIFS["night"])
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=f"KECHA #{game.day_count} BOSHLANDI!\n\n"
                   "Maxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\n"
                   "Vaqt: 1 daqiqa"
        )
    except:
        # Agar Xiva suratlari ishlamasa, yedek GIF'lar
        try:
            backup_gif = random.choice(BACKUP_GIFS["night"])
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=backup_gif,
                caption=f"KECHA #{game.day_count} BOSHLANDI!\n\n"
                       "Maxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\n"
                       "Vaqt: 1 daqiqa"
            )
        except:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"KECHA #{game.day_count} BOSHLANDI!\n\n"
                     "Maxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\n"
                     "Vaqt: 1 daqiqa"
            )
    
    # Mafia (shu jumladan Don) ga xabar
    mafia_members = [uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
    if mafia_members:
        for uid in mafia_members:
            keyboard = []
            row = []
            for pid in game.alive:
                if pid != uid:
                    player_name = game.get_player_name(pid)
                    row.append(InlineKeyboardButton(f"{player_name[:10]}", callback_data=f"kill:{pid}"))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            if row:
                keyboard.append(row)
            
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="Kimni o'ldirmoqchisiz?\n\n"
                         "Tugmalardan birini tanlang:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                print(f"Mafia {uid} ga xabar yuborishda xato: {e}")
    
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
                text="Kimni tekshirmoqchisiz?\n\n"
                     "Tugmalardan birini tanlang:",
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
                text="Kimni davolamoqchisiz?\n\n"
                     "Tugmalardan birini tanlang:\n"
                     "Eslatma: O'zingizni ham davolashingiz mumkin!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Shifokor {doctor} ga xabar yuborishda xato: {e}")
    
    # Taymerni boshlash
    game.timer_task = asyncio.create_task(night_timer(context, chat_id))

async def night_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Tungi taymer"""
    await asyncio.sleep(60) # 1 daqiqa
    
    if chat_id in games:
        game = games[chat_id]
        if game.phase == "night":
            await context.bot.send_message(
                chat_id=chat_id,
                text="Tungi vaqt tugadi! Natijalar hisoblanmoqda..."
            )
            await resolve_night(context, chat_id)

# ---------------- NIGHT CALLBACK HANDLER -----------------
async def night_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
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
    try:
        action, target_str = data.split(":")
    except:
        await query.edit_message_text("Xato!")
        return
    
    role = game.roles.get(user_id)
    
    if action == "kill" and role in ["Mafia", "Don"]:
        try:
            target = int(target_str)
            if target in game.alive:
                game.night_actions["mafia_kill"] = target
                target_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{target_mention} ni o'ldirish tanlandi.")
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("Xato!")
    
    elif action == "check" and role == "Komissar":
        try:
            target = int(target_str)
            if target in game.alive:
                checked_role = game.roles.get(target, "Noma'lum")
                game.night_actions["check"] = target
                target_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{target_mention} ni tekshirdingiz.\nRol: {checked_role}")
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("Xato!")
    
    elif action == "heal" and role == "Shifokor":
        try:
            target = int(target_str)
            if target in game.alive:
                game.night_actions["heal"] = target
                target_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{target_mention} ni davolash tanlandi.")
            else:
                await query.edit_message_text("Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("Xato!")
    
    # Harakatlarni tekshirish
    check_night_completion(context, chat_id)

def check_night_completion(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    # Harakatlarni tekshirish
    all_done = True
    
    # Mafia borligini tekshirish
    mafia_exists = any(game.roles.get(uid) in ["Mafia", "Don"] for uid in game.alive)
    if mafia_exists and game.night_actions["mafia_kill"] is None:
        all_done = False
    
    # Komissar borligini tekshirish
    komissar_exists = any(game.roles.get(uid) == "Komissar" for uid in game.alive)
    if komissar_exists and game.night_actions["check"] is None:
        all_done = False
    
    # Shifokor borligini tekshirish
    doctor_exists = any(game.roles.get(uid) == "Shifokor" for uid in game.alive)
    if doctor_exists and game.night_actions["heal"] is None:
        all_done = False
    
    if all_done:
        # Taymerni to'xtatish
        if game.timer_task:
            game.timer_task.cancel()
            game.timer_task = None
        
        # Kechani hal qilish
        context.application.create_task(resolve_night(context, chat_id))

# ---------------- RESOLVE NIGHT --------------------
async def resolve_night(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    kill_target = game.night_actions["mafia_kill"]
    heal_target = game.night_actions["heal"]
    died = None
    
    if kill_target is not None and kill_target != heal_target:
        died = kill_target
        game.alive.discard(died)
    
    # Tungi natijalarni e'lon qilish
    result_text = f"KECHA #{game.day_count} NATIJASI:\n\n"
    
    if died:
        killed_mention = game.get_player_mention(died)
        result_text += f"{killed_mention} kechasi o'ldirildi!\n"
    elif kill_target:
        if heal_target == kill_target:
            result_text += "Shifokor mafianing qurbonini davoladi!\n"
        else:
            result_text += "Hech kim o'lmadi, kecha tinch o'tdi.\n"
    else:
        result_text += "Hech kim o'lmadi, kecha tinch o'tdi.\n"
    
    await context.bot.send_message(chat_id=chat_id, text=result_text)
    
    # G'alaba tekshirish
    await check_victory(context, chat_id)

# ---------------- CHECK VICTORY --------------------
async def check_victory(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    mafia_alive = len([uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]])
    citizens_alive = len(game.alive) - mafia_alive
    
    # Tirik o'yinchilar ro'yxati
    alive_players = "Tirik o'yinchilar:\n"
    alive_players += game.get_players_list()
    
    await context.bot.send_message(chat_id=chat_id, text=alive_players, parse_mode='HTML')
    
    if mafia_alive == 0:
        # TINCH AHOLI G'ALABASI
        victory_text = "TINCH AHOLI G'ALABA QOZONDI!\n\n"
        victory_text += "G'olib o'yinchilar:\n"
        
        # Tirik qolgan barcha tinch aholi
        winners = []
        for uid in game.alive:
            mention = game.get_player_mention(uid)
            role = game.roles.get(uid, "Noma'lum")
            winners.append((mention, role))
        
        for mention, role in winners:
            victory_text += f"• {mention} ({role})\n"
        
        # O'yin natijalarini ko'rsatish
        victory_text += "\nO'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username, mention in game.players:
            role = game.roles.get(uid, "Noma'lum")
            victory_text += f"{mention} - {role}\n"
        
        await context.bot.send_message(chat_id=chat_id, text=victory_text, parse_mode='HTML')
        
        # Barcha o'yinchilarga xabar
        for uid, _, _, _ in game.players:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=victory_text,
                    parse_mode='HTML'
                )
            except:
                pass
        
        game.cancel_timer()
        del games[chat_id]
        return
    
    if mafia_alive >= citizens_alive:
        # MAFIA G'ALABASI
        victory_text = "MAFIA G'ALABA QOZONDI!\n\n"
        victory_text += "Mafia jamoasi:\n"
        
        # Barcha mafia a'zolari
        winners = []
        for uid, name, username, mention in game.players:
            if game.roles.get(uid) in ["Mafia", "Don"]:
                role = game.roles.get(uid, "Noma'lum")
                winners.append((mention, role))
        
        for mention, role in winners:
            victory_text += f"• {mention} ({role})\n"
        
        # O'yin natijalarini ko'rsatish
        victory_text += "\nO'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username, mention in game.players:
            role = game.roles.get(uid, "Noma'lum")
            victory_text += f"{mention} - {role}\n"
        
        await context.bot.send_message(chat_id=chat_id, text=victory_text, parse_mode='HTML')
        
        # Barcha o'yinchilarga xabar
        for uid, _, _, _ in game.players:
            try:
                await context.bot.send_message(chat_id=uid, text=victory_text, parse_mode='HTML')
            except:
                pass
        
        game.cancel_timer()
        del games[chat_id]
        return
    
    # Keyingi bosqichga o'tish
    game.day_count += 1
    await day_phase(context, chat_id)

# ---------------- DAY PHASE ----------------------
async def day_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    game.phase = "day"
    game.votes.clear()
    game.vote_messages.clear()
    game.vote_end_time = datetime.now() + timedelta(minutes=2)
    
    # Kunduzgi surat yuborish
    try:
        gif_url = random.choice(GIFS["day"])
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=f"KUN #{game.day_count} BOSHLANDI!\n\n"
                   "Endi ovoz beramiz – kimni chiqaramiz?\n\n"
                   f"Tirik o'yinchilar: {len(game.alive)} ta\n"
                   "Ovoz berish vaqti: 2 daqiqa\n"
                   "Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!"
        )
    except:
        # Agar Xiva suratlari ishlamasa, yedek GIF'lar
        try:
            backup_gif = random.choice(BACKUP_GIFS["day"])
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=backup_gif,
                caption=f"KUN #{game.day_count} BOSHLANDI!\n\n"
                       "Endi ovoz beramiz – kimni chiqaramiz?\n\n"
                       f"Tirik o'yinchilar: {len(game.alive)} ta\n"
                       "Ovoz berish vaqti: 2 daqiqa\n"
                       "Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!"
            )
        except:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"KUN #{game.day_count} BOSHLANDI!\n\n"
                     "Endi ovoz beramiz – kimni chiqaramiz?\n\n"
                     f"Tirik o'yinchilar: {len(game.alive)} ta\n"
                     "Ovoz berish vaqti: 2 daqiqa\n"
                     "Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!"
            )
    
    # Guruhga ovoz berish tugmalarini yuborish
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
    
    vote_message = await context.bot.send_message(
        chat_id=chat_id,
        text="O'z ovozingizni berish uchun tugmalardan birini bosing:\n"
             "Har bir o'yinchi faqat bir marta ovoz berishi mumkin!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Har bir tirik o'yinchiga ovoz berish xabarini yuboramiz
    for uid in game.alive:
        try:
            message = await context.bot.send_message(
                chat_id=uid,
                text="Kimni chiqarishni xohlaysiz?\n\n"
                     "Tugmalardan birini tanlang:\n"
                     "Vaqt: 2 daqiqa",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            game.vote_messages[uid] = message.message_id
        except Exception as e:
            print(f"Ovoz xabarini yuborishda xato {uid}: {e}")
            player_info = game.get_player_info(uid)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{player_info} ga ovoz berish xabarini yuborib bo'lmadi!"
            )
    
    # Taymerni boshlash
    game.timer_task = asyncio.create_task(day_timer(context, chat_id))

async def day_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Kunduzgi taymer"""
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    # 2 daqiqa kutamiz
    await asyncio.sleep(120)
    
    if chat_id in games and game.phase == "day":
        # Ovoz bermaganlarni aniqlash
        non_voters = [uid for uid in game.alive if uid not in game.votes]
        
        if non_voters:
            # Ovoz bermaganlarni chiqarish
            kicked_players = []
            for uid in non_voters:
                game.alive.discard(uid)
                mention = game.get_player_mention(uid)
                kicked_players.append(mention)
            
            if kicked_players:
                kicked_text = "Vaqt tugadi! Ovoz bermaganlar:\n"
                for mention in kicked_players:
                    kicked_text += f"{mention}\n"
                
                await context.bot.send_message(chat_id=chat_id, text=kicked_text, parse_mode='HTML')
        
        await resolve_day(context, chat_id)

# ---------------- DAY VOTE CALLBACK -----------------
async def day_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
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
            text=f"{user_mention} → hech kimga ovoz bermadi"
        )
    else:
        try:
            _, target_str = data.split(":")
            target = int(target_str)
            if target in game.alive:
                game.votes[user_id] = target
                voted_mention = game.get_player_mention(target)
                await query.edit_message_text(f"{voted_mention} ga ovoz berdingiz.")
                
                # Ovozni guruhga yozish
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{user_mention} → {voted_mention}"
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
                text=f"Ovoz berdi: {len(game.votes)}/{len(game.alive)} ta\n"
                     f"Qolgan vaqt: {minutes:02d}:{seconds:02d}"
            )
    
    # Hammasi ovoz berdimi?
    if len(game.votes) == len(game.alive):
        # Taymerni to'xtatish
        if game.timer_task:
            game.timer_task.cancel()
            game.timer_task = None
        
        await resolve_day(context, chat_id)

# ---------------- RESOLVE DAY --------------------
async def resolve_day(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    
    # Ovoz bermaganlarni chiqarish (agar hali chiqarilmagan bo'lsa)
    non_voters = [uid for uid in game.alive if uid not in game.votes]
    for uid in non_voters:
        game.alive.discard(uid)
        player_mention = game.get_player_mention(uid)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{player_mention} ovoz bermagani uchun chiqarildi!"
        )
    
    # Ovoz natijalarini hisoblash
    valid_votes = [v for v in game.votes.values() if v is not None]
    
    if not valid_votes:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Hech kim ovoz bermadi, kun o'tdi."
        )
        await night_phase(None, context)
        return
    
    # Eng ko'p ovoz olgan(lar)ni topish
    vote_counter = Counter(valid_votes)
    max_votes = max(vote_counter.values())
    candidates = [uid for uid, count in vote_counter.items() if count == max_votes]
    
    # Birdan ortiq bo'lsa, tasodifiy tanlash
    lynched = random.choice(candidates)
    
    # NATIJALARNI E'LON QILISH
    results_text = f"KUN #{game.day_count} OVOZ NATIJALARI:\n\n"
    
    results_text += "Hisobot:\n"
    for uid in game.alive:
        player_mention = game.get_player_mention(uid)
        votes_received = vote_counter.get(uid, 0)
        results_text += f"{player_mention}: {votes_received} ovoz\n"
    
    results_text += f"\nEng ko'p ovoz: {max_votes}"
    
    await context.bot.send_message(chat_id=chat_id, text=results_text, parse_mode='HTML')
    
    # Linch qilish
    game.alive.discard(lynched)
    player_mention = game.get_player_mention(lynched)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{player_mention} chiqarildi (linch)!\n"
             f"Rol sir saqlanmoqda...",
        parse_mode='HTML'
    )
    
    # G'alaba tekshirish
    await check_victory(context, chat_id)

# ---------------- FORCE NEXT --------------------
async def force_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin komandasi: keyingi bosqichga o'tish"""
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("Faol o'yin yo'q!")
        return
    
    game = games[chat_id]
    
    await update.message.reply_text("Keyingi bosqichga o'tilmoqda...")
    
    # Taymerni to'xtatish
    if game.timer_task:
        game.timer_task.cancel()
        game.timer_task = None
    
    if game.phase == "night":
        await resolve_night(context, chat_id)
    elif game.phase == "day":
        await resolve_day(context, chat_id)

# ---------------- MAIN ------------------------
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("begin", begin))
    app.add_handler(CommandHandler("players", players_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("next", force_next))
    app.add_handler(CommandHandler("stop", stop_game))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Tungi harakatlar
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill|check|heal):"))
    
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
    print(" /next - Keyingi bosqich")
    print(" /stop - O'yinni to'xtatish")
    
    app.run_polling()

if __name__ == "__main__":
    main()
