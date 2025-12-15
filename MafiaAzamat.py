from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import random
from collections import Counter
import asyncio
from datetime import datetime, timedelta

API_TOKEN = "8034346294:AAE53a_P73UK_oXP15gnBH1hlXiB5hKUZ74"

# ---------------- GLOBAL GAME DATA -----------------
games = {}  # chat_id -> Game object

ROLES = {
    "Mafia": 2,      # Misol uchun 8-10 kishi bo'lsa moslashtiring
    "Don": 1,
    "Komissar": 1,
    "Shifokor": 1,
    "Tinch aholi": 6
}

# ----------------- GAME CLASS -----------------
class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = []          # list of (user_id, full_name, username)
        self.roles = {}            # user_id -> role
        self.alive = set()         # set of alive user_ids
        self.started = False
        self.phase = "day"         # "day" or "night"
        self.night_actions = {
            "mafia_kill": None,    # oxirgi mafia tanlovi
            "heal": None,
            "check": None
        }
        self.votes = {}            # user_id -> voted_for_user_id (kun fazasi uchun)
        self.vote_messages = {}    # user_id -> message_id (ovoz berish xabarlari)
        self.day_count = 1         # kun raqami
        self.timer_task = None     # taymer vazifasi
        self.vote_end_time = None  # ovoz berish tugash vaqti
        
    def add_player(self, uid, name, username=None):
        if self.started:
            return False
        if uid not in [p[0] for p in self.players]:
            self.players.append((uid, name, username))
            return True
        return False

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
        for pid, name, username in self.players:
            if pid == uid:
                return name
        return "Noma'lum"
    
    def get_player_info(self, uid):
        """O'yinchi haqida to'liq ma'lumot"""
        for pid, name, username in self.players:
            if pid == uid:
                info = f"{name}"
                if username:
                    info += f" (@{username})"
                return info
        return "Noma'lum"
    
    def get_all_roles_table(self):
        """O'yin tugaganda barcha rollarni ko'rsatish"""
        table = "🎭 O'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username in self.players:
            role = self.roles.get(uid, "Noma'lum")  # Xatolikni oldini olish
            alive = "❤️" if uid in self.alive else "💀"
            info = f"{name}"
            if username:
                info += f" (@{username})"
            table += f"{alive} {info}\n🎭 Rol: {role}\n"
            table += "─" * 30 + "\n"
        return table
    
    def get_players_list(self):
        """O'yinchilar ro'yxatini olish"""
        players_text = ""
        for i, (uid, name, username) in enumerate(self.players, 1):
            alive = "❤️" if uid in self.alive else "💀"
            info = f"{name}"
            if username:
                info += f" (@{username})"
            players_text += f"{i}. {alive} {info}\n"
        return players_text
    
    def cancel_timer(self):
        """Taymerni to'xtatish"""
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

# --------------- COMMAND HANDLERS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni ishga tushirish"""
    await update.message.reply_text(
        "🌙 Mafia O'yini!\n\n"
        "Quyidagi buyruqlardan foydalaning:\n"
        "/join - o'yinga qo'shilish\n"
        "/begin - o'yinni boshlash (kamida 5 kishi)\n"
        "/players - o'yinchilar ro'yxatini ko'rish\n"
        "/status - o'yin holatini ko'rish\n"
        "/next - keyingi bosqichga o'tish\n"
        "/stop - o'yinni to'xtatish\n"
        "/rules - o'yin qoidalari"
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yin qoidalari"""
    rules_text = """
📚 MAFIA O'YINI QOIDALARI

🎭 ROLLAR:
• Mafia (2 ta) - Kechasi bir kishini o'ldiradi
• Don (1 ta) - Mafia rahbari, mafia bilan birga harakat qiladi
• Komissar (1 ta) - Kechasi bir kishini tekshirib, uning rolini bilib oladi
• Shifokor (1 ta) - Kechasi bir kishini davolaydi (o'ldirilishdan saqlaydi)
• Tinch aholi - Hech qanday maxsus kuchi yo'q, faqat ovoz beradi

🌙 KECHA (TUN):
1. Mafia bir kishini o'ldirish uchun ovoz beradi
2. Komissar bir kishini tekshiradi
3. Shifokor bir kishini davolaydi

🌞 KUN (KUNDUZ):
1. Barcha tirik o'yinchilar suhbatlashadi
2. Shu kuni kimni chiqarish kerakligi haqida ovoz berishadi
3. Eng ko'p ovoz olgan kishi chiqariladi

🏆 G'ALABA:
• Mafia g'alabasi - Mafia soni tinch aholi soniga teng yoki undan ko'p bo'lsa
• Tinch aholi g'alabasi - Barcha mafia o'ldirilsa

⏰ VAQT CHEGARALARI:
• Kecha: 1 daqiqa
• Kun: 2 daqiqa
• Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi
    """
    
    await update.message.reply_text(rules_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
🆘 YORDAM

Agar quyidagi muammolarga duch kelsangiz:

1. Bot javob bermayapti: /start ni bosing
2. O'yinchi qo'shilmayapti: Guruhda /join buyrug'ini bering
3. Shaxsiy xabar kelmayapti: Botga @botfather orqali /start bosganligingizni tekshiring
4. O'yin to'xtab qoldi: /next yoki /stop buyruqlaridan foydalaning

🎮 QANDAY O'YNASHA KERAK:
1. /join - o'yinchi sifatida qo'shiling
2. /begin - o'yin boshlang
3. Shaxsiy xabarlarda harakatlaringizni bajaring
4. O'yinni diqqat bilan kuzating!
    """
    
    await update.message.reply_text(help_text)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        games[chat_id] = Game(chat_id)
    game = games[chat_id]
    user = update.effective_user
    
    # Username ni olish
    username = user.username
    if game.add_player(user.id, user.full_name, username):
        await update.message.reply_text(
            f"✅ {user.full_name} o'yinga qo'shildi!\n"
            f"👥 Jami o'yinchilar: {len(game.players)} ta"
        )
    else:
        await update.message.reply_text("❌ Siz allaqachon qo'shilgansiz yoki o'yin boshlangan!")

async def players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinchilar ro'yxatini ko'rish"""
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("❌ Hozircha o'yin yo'q. Avval /join buyrug'i bilan qo'shiling!")
        return
    
    game = games[chat_id]
    
    if not game.players:
        await update.message.reply_text("❌ Hozircha o'yinchilar yo'q.")
        return
    
    players_text = f"👥 O'YINCHILAR RO'YXATI:\n\n"
    players_text += f"Jami: {len(game.players)} ta o'yinchi\n\n"
    
    players_text += game.get_players_list()
    
    await update.message.reply_text(players_text)

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("❌ Avval o'yinchilar /join qilishi kerak!")
        return
    
    game = games[chat_id]
    if len(game.players) < 5:
        await update.message.reply_text(f"❌ Kamida 5 ta o'yinchi kerak! Hozir: {len(game.players)} ta")
        return
    
    if game.started:
        await update.message.reply_text("❌ O'yin allaqachon boshlangan!")
        return

    game.started = True
    game.assign_roles()

    # O'yinchilar ro'yxatini ko'rsatamiz
    players_list = "👥 O'YINCHILAR RO'YXATI:\n\n"
    players_list += game.get_players_list()
    
    await update.message.reply_text(
        f"🎉 O'YIN BOSHLANDI!\n\n"
        f"O'yinchilar: {len(game.players)} ta\n\n"
        f"{players_list}\n"
        f"📢 Rollar shaxsiy xabarlarda yuborildi!"
    )
    
    # Har bir o'yinchiga faqat o'z rolini yuboramiz
    for uid, name, username in game.players:
        role = game.roles.get(uid, "Noma'lum")
        try:
            # O'z rolini yuborish
            role_text = f"🎭 Sizning rolingiz: {role}\n\n"
            role_text += f"📋 O'yinchilar: {len(game.players)} ta\n"
            role_text += "💡 Eslatma: Boshqalarning rollari o'yin oxirigacha sir saqlanadi!\n\n"
            
            # O'yinchilar ro'yxati
            role_text += "👥 O'yinchilar:\n"
            role_text += game.get_players_list()
            
            await context.bot.send_message(
                chat_id=uid,
                text=role_text
            )
            
            # Agar Mafia bo'lsa, boshqa mafia a'zolarini ko'rsatish
            if role in ["Mafia", "Don"]:
                mafia_members = []
                for player_id, player_name, player_username in game.players:
                    if player_id != uid and game.roles.get(player_id) in ["Mafia", "Don"]:
                        info = f"{player_name}"
                        if player_username:
                            info += f" (@{player_username})"
                        mafia_members.append(info)
                
                if mafia_members:
                    mafia_list = "\n".join([f"• {info}" for info in mafia_members])
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"🔫 Mafia jamoa a'zolari:\n{mafia_list}\n\n"
                             f"💡 Eslatma: Faqat siz va bu odamlar bir-birlaringizni mafia ekanligingizni bilasiz!"
                    )
        except Exception as e:
            print(f"Xato {name} ga rol yuborishda: {e}")
            await update.message.reply_text(f"⚠️ {name} ga xabar yuborilmadi (botga /start bosilmagan)")

    await night_phase(update, context)

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yinni to'xtatish"""
    chat_id = update.effective_chat.id
    if chat_id in games:
        game = games[chat_id]
        game.cancel_timer()
        
        # O'yin natijalarini ko'rsatish
        result_text = "🛑 O'yin to'xtatildi!\n\n"
        result_text += "🎭 O'YINCHILAR RO'YXATI:\n\n"
        
        for uid, name, username in game.players:
            info = f"{name}"
            if username:
                info += f" (@{username})"
            role = game.roles.get(uid, "Noma'lum")
            alive = "❤️" if uid in game.alive else "💀"
            result_text += f"{alive} {info}\n🎭 Rol: {role}\n"
            result_text += "─" * 30 + "\n"
        
        await update.message.reply_text(result_text)
        
        del games[chat_id]
    else:
        await update.message.reply_text("❌ Faol o'yin yo'q!")

# ---------------- MESSAGE HANDLER -----------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ belgisi bilan boshlanmagan xabarlarni boshqarish"""
    message_text = update.message.text
    
    # Agar xabar faqat "/" bilan boshlansa
    if message_text == '/':
        # Telegram avtomatik ravishda buyruqlar ro'yxatini ko'rsatadi
        # Shuning uchun biz hech narsa qilmaymiz
        pass

# ---------------- STATUS COMMAND -----------------
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'yin holatini ko'rish"""
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("❌ Faol o'yin yo'q!")
        return
    
    game = games[chat_id]
    
    status_text = f"🎮 O'YIN HOLATI:\n\n"
    status_text += f"Faza: {'🌙 Kecha' if game.phase == 'night' else '🌞 Kun'} #{game.day_count}\n"
    status_text += f"Tirik o'yinchilar: {len(game.alive)}/{len(game.players)}\n"
    
    if game.phase == "day":
        status_text += f"Ovoz berganlar: {len(game.votes)}/{len(game.alive)}\n"
    
    status_text += f"\nO'yinchi holati:\n"
    
    # O'yinchilar ro'yxati
    status_text += game.get_players_list()
    
    await update.message.reply_text(status_text)

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

    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🌙 KECHA #{game.day_count} BOSHLANDI!\n"
             "Maxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\n"
             "⏰ Vaqt: 1 daqiqa"
    )

    # Mafia (shu jumladan Don) ga xabar
    mafia_members = [uid for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
    if mafia_members:
        # Mafia jamoasi haqida ma'lumot
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔫 Mafia jamoasi harakat qilmoqda..."
        )
        
        for uid in mafia_members:
            keyboard = []
            for pid in game.alive:
                if pid != uid:
                    player_name = game.get_player_name(pid)
                    keyboard.append([InlineKeyboardButton(player_name, callback_data=f"kill:{pid}")])
            
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="🔫 Kimni o'ldirmoqchisiz?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                print(f"Mafia {uid} ga xabar yuborishda xato: {e}")

    # Komissar
    komissar = next((uid for uid in game.alive if game.roles.get(uid) == "Komissar"), None)
    if komissar:
        try:
            keyboard = []
            for pid in game.alive:
                if pid != komissar:
                    player_name = game.get_player_name(pid)
                    keyboard.append([InlineKeyboardButton(player_name, callback_data=f"check:{pid}")])
            
            await context.bot.send_message(
                chat_id=komissar,
                text="🔍 Kimni tekshirmoqchisiz?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Komissar {komissar} ga xabar yuborishda xato: {e}")

    # Shifokor
    doctor = next((uid for uid in game.alive if game.roles.get(uid) == "Shifokor"), None)
    if doctor:
        try:
            keyboard = []
            for pid in game.alive:
                player_name = game.get_player_name(pid)
                keyboard.append([InlineKeyboardButton(player_name, callback_data=f"heal:{pid}")])
            
            await context.bot.send_message(
                chat_id=doctor,
                text="💉 Kimni davolamoqchisiz? (O'zingizni ham bo'ladi)",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Shifokor {doctor} ga xabar yuborishda xato: {e}")

    # Taymerni boshlash
    game.timer_task = asyncio.create_task(night_timer(context, chat_id))

async def night_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Tungi taymer"""
    await asyncio.sleep(60)  # 1 daqiqa
    
    if chat_id in games:
        game = games[chat_id]
        if game.phase == "night":
            await context.bot.send_message(
                chat_id=chat_id,
                text="⏰ Tungi vaqt tugadi! Natijalar hisoblanmoqda..."
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
        await query.edit_message_text("❌ Bu vaqtda harakat qilish mumkin emas!")
        return
    
    data = query.data
    try:
        action, target_str = data.split(":")
    except:
        await query.edit_message_text("❌ Xato!")
        return
    
    role = game.roles.get(user_id)
    
    if action == "kill" and role in ["Mafia", "Don"]:
        try:
            target = int(target_str)
            if target in game.alive:
                game.night_actions["mafia_kill"] = target
                target_name = game.get_player_info(target)
                await query.edit_message_text(f"✅ {target_name} ni o'ldirish tanlandi.")
            else:
                await query.edit_message_text("❌ Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("❌ Xato!")
    
    elif action == "check" and role == "Komissar":
        try:
            target = int(target_str)
            if target in game.alive:
                checked_role = game.roles.get(target, "Noma'lum")
                game.night_actions["check"] = target
                target_name = game.get_player_info(target)
                await query.edit_message_text(f"✅ {target_name} ni tekshirdingiz. Rol: {checked_role}")
            else:
                await query.edit_message_text("❌ Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("❌ Xato!")
    
    elif action == "heal" and role == "Shifokor":
        try:
            target = int(target_str)
            if target in game.alive:
                game.night_actions["heal"] = target
                target_name = game.get_player_info(target)
                await query.edit_message_text(f"✅ {target_name} ni davolash tanlandi.")
            else:
                await query.edit_message_text("❌ Bu o'yinchi tirik emas!")
        except:
            await query.edit_message_text("❌ Xato!")
    
    # Harakatlarni tekshirish
    check_night_completion(context, chat_id)

# ---------------- CHECK NIGHT COMPLETION -----------------
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
    result_text = f"🌙 KECHA #{game.day_count} NATIJASI:\n\n"
    
    if died:
        killed_name = game.get_player_info(died)
        result_text += f"☠️ {killed_name} kechasi o'ldirildi!\n"
    elif kill_target:
        if heal_target == kill_target:
            result_text += "💊 Shifokor mafianing qurbonini davoladi!\n"
        else:
            result_text += "🌃 Hech kim o'lmadi, kecha tinch o'tdi.\n"
    else:
        result_text += "🌃 Hech kim o'lmadi, kecha tinch o'tdi.\n"
    
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
    alive_players = "❤️ Tirik o'yinchilar:\n"
    alive_players += game.get_players_list()
    
    await context.bot.send_message(chat_id=chat_id, text=alive_players)

    if mafia_alive == 0:
        # TINCH AHOLI G'ALABASI
        victory_text = "🎉🎉 TINCH AHOLI G'ALABA QOZONDI! 🎉🎉\n\n"
        victory_text += "🏆 G'olib o'yinchilar:\n"
        
        # Tirik qolgan barcha tinch aholi
        winners = []
        for uid in game.alive:
            name = game.get_player_info(uid)
            role = game.roles.get(uid, "Noma'lum")
            winners.append((name, role))
        
        for name, role in winners:
            victory_text += f"• {name} ({role})\n"
        
        # O'yin natijalarini ko'rsatish
        victory_text += "\n🎭 O'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username in game.players:
            role = game.roles.get(uid, "Noma'lum")
            info = f"{name}"
            if username:
                info += f" (@{username})"
            victory_text += f"{info} - {role}\n"
        
        await context.bot.send_message(chat_id=chat_id, text=victory_text)
        
        # Barcha o'yinchilarga xabar
        for uid, _, _ in game.players:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=victory_text
                )
            except:
                pass
        
        game.cancel_timer()
        del games[chat_id]
        return
    
    if mafia_alive >= citizens_alive:
        # MAFIA G'ALABASI
        victory_text = "🎉🎉 MAFIA G'ALABA QOZONDI! 🎉🎉\n\n"
        victory_text += "🏆 Mafia jamoasi:\n"
        
        # Barcha mafia a'zolari
        winners = []
        for uid, name, username in game.players:
            if game.roles.get(uid) in ["Mafia", "Don"]:
                role = game.roles.get(uid, "Noma'lum")
                info = f"{name}"
                if username:
                    info += f" (@{username})"
                winners.append((info, role))
        
        for info, role in winners:
            victory_text += f"• {info} ({role})\n"
        
        # O'yin natijalarini ko'rsatish
        victory_text += "\n🎭 O'YINCHILAR VA ROLLARI:\n\n"
        for uid, name, username in game.players:
            role = game.roles.get(uid, "Noma'lum")
            info = f"{name}"
            if username:
                info += f" (@{username})"
            victory_text += f"{info} - {role}\n"
        
        await context.bot.send_message(chat_id=chat_id, text=victory_text)
        
        # Barcha o'yinchilarga xabar
        for uid, _, _ in game.players:
            try:
                await context.bot.send_message(chat_id=uid, text=victory_text)
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

    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🌞 KUN #{game.day_count} BOSHLANDI!\n"
             "Endi ovoz beramiz – kimni chiqaramiz?\n\n"
             f"Tirik o'yinchilar: {len(game.alive)} ta\n"
             "⏰ Ovoz berish vaqti: 2 daqiqa\n"
             "⏰ Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!"
    )

    # Har bir tirik o'yinchiga ovoz berish xabarini yuboramiz
    for uid in game.alive:
        # Ovoz berish uchun tugmalar
        keyboard = []
        for target_uid in game.alive:
            if target_uid != uid:
                player_name = game.get_player_name(target_uid)
                keyboard.append([InlineKeyboardButton(player_name, callback_data=f"vote:{target_uid}")])
        
        # Ovoz bermaslik tugmasi
        keyboard.append([InlineKeyboardButton("❌ Ovoz bermaslik", callback_data="vote:none")])
        
        try:
            message = await context.bot.send_message(
                chat_id=uid,
                text="🗳 Kimni chiqarishni xohlaysiz? (Ovoz berish majburiy)\n⏰ Vaqt: 2 daqiqa",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            game.vote_messages[uid] = message.message_id
        except Exception as e:
            print(f"Ovoz xabarini yuborishda xato {uid}: {e}")
            player_info = game.get_player_info(uid)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ {player_info} ga ovoz berish xabarini yuborib bo'lmadi!"
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
                name = game.get_player_info(uid)
                kicked_players.append(name)
            
            if kicked_players:
                kicked_text = "⏰ Vaqt tugadi! Ovoz bermaganlar:\n"
                for name in kicked_players:
                    kicked_text += f"☠️ {name}\n"
                
                await context.bot.send_message(chat_id=chat_id, text=kicked_text)
        
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
        await query.edit_message_text("❌ Bu vaqtda ovoz berish mumkin emas!")
        return
    
    data = query.data
    user_info = game.get_player_info(user_id)
    
    # Ovozni saqlash
    if data == "vote:none":
        game.votes[user_id] = None
        await query.edit_message_text("✅ Ovoz bermaslik tanlandi.")
        
        # Ovozni guruhga yozish
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🗳 {user_info} → hech kimga ovoz bermadi"
        )
    else:
        try:
            _, target_str = data.split(":")
            target = int(target_str)
            if target in game.alive:
                game.votes[user_id] = target
                voted_info = game.get_player_info(target)
                await query.edit_message_text(f"✅ {voted_info} ga ovoz berdingiz.")
                
                # Ovozni guruhga yozish
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🗳 {user_info} → {voted_info}"
                )
            else:
                await query.edit_message_text("❌ Bu o'yinchi tirik emas!")
                return
        except:
            await query.edit_message_text("❌ Xato!")
            return
    
    # Qolgan vaqtni hisoblash va ko'rsatish
    if game.vote_end_time:
        time_left = game.vote_end_time - datetime.now()
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        if minutes > 0 or seconds > 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📊 Ovoz berdi: {len(game.votes)}/{len(game.alive)} ta\n"
                     f"⏰ Qolgan vaqt: {minutes:02d}:{seconds:02d}"
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
        player_info = game.get_player_info(uid)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"☠️ {player_info} ovoz bermagani uchun chiqarildi!"
        )
    
    # Ovoz natijalarini hisoblash
    valid_votes = [v for v in game.votes.values() if v is not None]
    
    if not valid_votes:
        await context.bot.send_message(chat_id=chat_id, text="❌ Hech kim ovoz bermadi, kun o'tdi.")
        await night_phase(None, context)
        return
    
    # Eng ko'p ovoz olgan(lar)ni topish
    vote_counter = Counter(valid_votes)
    max_votes = max(vote_counter.values())
    candidates = [uid for uid, count in vote_counter.items() if count == max_votes]
    
    # Birdan ortiq bo'lsa, tasodifiy tanlash
    lynched = random.choice(candidates)
    
    # NATIJALARNI E'LON QILISH
    results_text = f"📊 KUN #{game.day_count} OVOZ NATIJALARI:\n\n"
    
    results_text += "📈 Hisobot:\n"
    for uid in game.alive:
        player_info = game.get_player_info(uid)
        votes_received = vote_counter.get(uid, 0)
        results_text += f"{player_info}: {votes_received} ovoz\n"
    
    results_text += f"\n🔥 Eng ko'p ovoz: {max_votes}"
    
    await context.bot.send_message(chat_id=chat_id, text=results_text)
    
    # Linch qilish
    game.alive.discard(lynched)
    player_info = game.get_player_info(lynched)
    
    # Rolni sir saqlaymiz, o'yin oxirigacha
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"☠️ {player_info} chiqarildi (linch)!\n"
             f"🎭 Rol sir saqlanmoqda..."
    )
    
    # G'alaba tekshirish
    await check_victory(context, chat_id)

# ---------------- FORCE NEXT --------------------
async def force_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin komandasi: keyingi bosqichga o'tish"""
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("❌ Faol o'yin yo'q!")
        return
    
    game = games[chat_id]
    
    await update.message.reply_text("⏭️ Keyingi bosqichga o'tilmoqda...")
    
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
    
    # Message handler (faqat "/" uchun)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/$'), message_handler))

    # Tungi harakatlar
    app.add_handler(CallbackQueryHandler(night_callback, pattern="^(kill|check|heal):"))

    # Kun ovoz berish
    app.add_handler(CallbackQueryHandler(day_vote_callback, pattern="^vote"))

    print("✅ Bot ishga tushdi...")
    print("📋 Buyruqlar:")
    print("  / - Telegram standart buyruqlar ro'yxati")
    print("  /start - botni ishga tushirish")
    print("  /join - o'yinga qo'shilish")
    print("  /begin - o'yinni boshlash")
    print("  /players - o'yinchilar ro'yxati")
    print("  /status - o'yin holati")
    print("  /rules - o'yin qoidalari")
    
    app.run_polling()

if __name__ == "__main__":
    main()
