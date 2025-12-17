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

# Til matnlari - 3 xil til
TEXTS = {
    "uz": {
        "start": "🎮 Mafia O'yini Botiga Xush Kelibsiz!\n\n"
                "📋 Buyruqlar:\n"
                "/join - O'yinga qo'shilish\n"
                "/begin - O'yinni boshlash (min 5 kishi)\n"
                "/players - O'yinchilar ro'yxati\n"
                "/status - O'yin holati\n"
                "/next - Keyingi bosqich\n"
                "/stop - O'yinni to'xtatish\n"
                "/rules - O'yin qoidalari\n"
                "/settings - Sozlamalar\n\n"
                "⚙️ Eslatma: Rollar shaxsiy xabarlarda yuboriladi!",
        "join_button": "🎮 O'yinga Qo'shilish",
        "vote_button": "🗳️ Ovoz berish",
        "back_to_group": "⬅️ Guruhga qaytish",
        "back_to_bot": "🤖 Botga qaytish",
        "vote_in_group": "📢 Guruhda ovoz berish",
        "vote_in_private": "🔒 Shaxsiy ovoz berish",
        "settings_menu": "⚙️ SOZLAMALAR\n\n"
                        "1️⃣ Tungi vaqt: {} sekund\n"
                        "2️⃣ Kunduzgi vaqt: {} sekund\n"
                        "3️⃣ Til: {}\n"
                        "4️⃣ Bonus ballar: {}\n"
                        "5️⃣ Guruhda ovoz berish: {}\n"
                        "6️⃣ Avto-chiqarish: {}",
        "settings_options": [
            ["🌙 Tungi vaqtni o'zgartir", "set_night"],
            ["☀️ Kunduzgi vaqtni o'zgartir", "set_day"],
            ["🌐 Tilni o'zgartir", "set_language"],
            ["🎖️ Bonus ballar", "toggle_bonus"],
            ["📢 Guruhda ovoz", "toggle_group_vote"],
            ["⚡ Avto-chiqarish", "toggle_auto_kick"],
            ["🔙 Orqaga", "back_to_main"]
        ],
        "joined": "{} o'yinga qo'shildi!\n👥 Jami: {} ta\n🎯 Minimal: 5 ta",
        "already_joined": "Siz allaqachon qo'shilgansiz yoki o'yin boshlangan!",
        "not_enough": "Kamida 5 ta o'yinchi kerak!\n📊 Hozir: {} ta\n🎯 Yetishmayotgan: {} ta",
        "game_started": "O'YIN BOSHLANDI!\n\n👥 O'yinchilar: {} ta\n\n📢 Rollar shaxsiy xabarlarda yuborildi!",
        "night_start": "🌙 KECHA #{} BOSHLANDI!\n\n🔒 Maxfiy harakatlar uchun shaxsiy xabarlar orqali tanlang.\n⏰ Vaqt: {} soniya",
        "day_start": "☀️ KUN #{} BOSHLANDI!\n\n🗳️ Endi ovoz beramiz – kimni chiqarish kerak?\n\n❤️ Tirik o'yinchilar: {} ta\n⏰ Ovoz berish vaqti: {} soniya\n⚠️ Vaqt tugagach, ovoz bermaganlar avtomatik chiqariladi!",
        "role_assigned": "Sizning rolingiz: {}\n\n👥 O'yinchilar: {} ta\n🔒 Boshqalarning rollari o'yin oxirigacha sir saqlanadi!\n\n👤 O'yinchilar:\n{}",
        "mafia_team": "Mafia jamoa a'zolari:\n{}\n\n🤝 Faqat siz va bu odamlar bir-birlaringizni mafia ekanligingizni bilasiz!",
        "vote_menu": "Kimni chiqarishni xohlaysiz?\n\n👉 Pastdagi tugmalardan birini tanlang:\n⏰ Vaqt: {} soniya",
        "vote_cast": "{} → {}",
        "vote_none": "{} → hech kimga ovoz bermadi",
        "vote_stats": "📊 Ovoz berdi: {}/{} ta\n⏰ Qolgan vaqt: {:02d}:{:02d}",
        "time_up": "⏰ Vaqt tugadi! Ovoz bermaganlar:\n{}",
        "vote_results": "KUN #{} OVOZ NATIJALARI:\n\n📈 Hisobot:\n{}\n\n🔥 Eng ko'p ovoz: {}",
        "lynched": "{} chiqarildi (linch)!\n🎭 Rol sir saqlanmoqda...",
        "night_results": "KECHA #{} NATIJALARI:\n\n{}",
        "killed": "{} kechasi o'ldirildi!",
        "healed": "💊 Shifokor mafianing qurbonini davoladi!",
        "peaceful": "🌃 Hech kim o'lmadi, kecha tinch o'tdi.",
        "alive_players": "❤️ Tirik o'yinchilar:\n{}",
        "citizen_win": "🎉 TINCH AHOLI G'ALABA QOZONDI!\n\n🏆 G'olib o'yinchilar:\n{}\n\n🎭 O'YINCHILAR VA ROLLARI:\n\n{}",
        "mafia_win": "🎉 MAFIA G'ALABA QOZONDI!\n\n🏆 Mafia jamoasi:\n{}\n\n🎭 O'YINCHILAR VA ROLLARI:\n\n{}",
        "game_stopped": "O'yin to'xtatildi!\n\n🎭 O'YINCHILAR RO'YXATI:\n\n{}",
        "rules": """📚 MAFIA O'YINI QOIDALARI:

1. O'yin ikkita asosiy bosqichdan iborat:
   - 🌙 Kecha (tun) - mafia, don, komissar va shifokor harakat qiladi
   - ☀️ Kun (kunduz) - hamma o'yinchilar ovoz beradi

2. Rollar:
   - 🎭 Mafia (2 ta) - kechasi bir kishini o'ldiradi
   - 👑 Don (1 ta) - mafia bilan birga, komissarga ko'rinmaydi
   - 🔍 Komissar (1 ta) - kechasi bir kishining rolini bilib oladi
   - 💊 Shifokor (1 ta) - kechasi bir kishini davolaydi
   - 👨‍👩‍👧‍👦 Tinch aholi (6+ ta) - mafialarni topish kerak

3. G'alaba:
   - Tinch aholi g'alaba qiladi: barcha mafia va don o'ldirilsa
   - Mafia g'alaba qiladi: mafia soni tinch aholiga teng yoki undan ortiq bo'lsa

4. Ovoz berish:
   - Kun davomida hamma tirik o'yinchilar kimni o'ldirish kerak deb o'ylasa, ovoz beradi
   - Eng ko'p ovoz olgan kishi o'ldiriladi

5. Eslatmalar:
   - Rollar sir saqlanadi
   - Kecha harakatlari shaxsiy xabarlarda amalga oshiriladi
   - Vaqt chegarasi bor""",
        "status_template": """🎮 O'YIN HOLATI:

📊 Bosqich: {phase}
📅 Kun: #{day_count}
👥 Jami o'yinchilar: {total_players} ta
❤️ Tirik o'yinchilar: {alive_players} ta
☠️ O'lgan o'yinchilar: {dead_players} ta

{additional_info}""",
        "execute_vote_start": "⚖️ {} ni o'ldirish yoki o'ldirmaslik bo'yicha ovoz berish boshlandi!\n\nOvoz berish muddati: {} soniya",
        "execute_vote_menu": "{} ni o'ldirish kerakmi?\n\nHa - o'ldirish kerak\nYo'q - o'ldirish kerak emas",
        "execute_vote_stats": "🗳️ Ovoz natijalari:\n✅ Ha: {} ovoz\n❌ Yo'q: {} ovoz\n\nQaror: {}",
        "execute_killed": "✅ {} o'ldirildi!",
        "execute_spared": "❌ {} omon qoldirildi!",
        "kill_vote_menu": "Kimni o'ldirmoqchisiz?\n\nShaxsiy xabarlar orqali tanlang.",
        "check_vote_menu": "Kimni tekshirmoqchisiz?\n\nShaxsiy xabarlar orqali tanlang.",
        "heal_vote_menu": "Kimni davolamoqchisiz?\n\nShaxsiy xabarlar orqali tanlang.",
        "language_set": "✅ Til {} ga o'zgartirildi!",
        "bonus_toggled": "✅ Bonus ballar: {}",
        "group_vote_toggled": "✅ Guruhda ovoz berish: {}",
        "auto_kick_toggled": "✅ Avto-chiqarish: {}",
        "time_set": "✅ {} vaqti {} soniyaga o'zgartirildi!",
        "yes": "Ha",
        "no": "Yo'q",
        "enabled": "Yoqilgan",
        "disabled": "O'chirilgan"
    },
    "ru": {
        "start": "🎮 Добро пожаловать в бота игры Мафия!\n\n"
                "📋 Команды:\n"
                "/join - Присоединиться к игре\n"
                "/begin - Начать игру (мин 5 человек)\n"
                "/players - Список игроков\n"
                "/status - Статус игры\n"
                "/next - Следующий этап\n"
                "/stop - Остановить игру\n"
                "/rules - Правила игры\n"
                "/settings - Настройки\n\n"
                "⚙️ Примечание: Роли отправляются в личные сообщения!",
        "join_button": "🎮 Присоединиться к игре",
        "vote_button": "🗳️ Голосовать",
        "back_to_group": "⬅️ Вернуться в группу",
        "back_to_bot": "🤖 Вернуться к боту",
        "vote_in_group": "📢 Голосовать в группе",
        "vote_in_private": "🔒 Голосовать в личке",
        "settings_menu": "⚙️ НАСТРОЙКИ\n\n"
                        "1️⃣ Ночное время: {} секунд\n"
                        "2️⃣ Дневное время: {} секунд\n"
                        "3️⃣ Язык: {}\n"
                        "4️⃣ Бонусные очки: {}\n"
                        "5️⃣ Голосование в группе: {}\n"
                        "6️⃣ Авто-исключение: {}",
        "settings_options": [
            ["🌙 Изменить ночное время", "set_night"],
            ["☀️ Изменить дневное время", "set_day"],
            ["🌐 Изменить язык", "set_language"],
            ["🎖️ Бонусные очки", "toggle_bonus"],
            ["📢 Голосование в группе", "toggle_group_vote"],
            ["⚡ Авто-исключение", "toggle_auto_kick"],
            ["🔙 Назад", "back_to_main"]
        ],
        "joined": "{} присоединился к игре!\n👥 Всего: {} чел.\n🎯 Минимум: 5 чел.",
        "already_joined": "Вы уже присоединились или игра началась!",
        "not_enough": "Нужно минимум 5 игроков!\n📊 Сейчас: {} чел.\n🎯 Не хватает: {} чел.",
        "game_started": "ИГРА НАЧАЛАСЬ!\n\n👥 Игроков: {} чел.\n\n📢 Роли отправлены в личные сообщения!",
        "night_start": "🌙 НОЧЬ #{} НАЧАЛАСЬ!\n\n🔒 Для секретных действий используйте личные сообщения.\n⏰ Время: {} секунд",
        "day_start": "☀️ ДЕНЬ #{} НАЧАЛСЯ!\n\n🗳️ Теперь голосуем – кого выгнать?\n\n❤️ Живые игроки: {} чел.\n⏰ Время голосования: {} секунд\n⚠️ По окончании времени не проголосовавшие будут исключены!",
        "role_assigned": "Ваша роль: {}\n\n👥 Игроков: {} чел.\n🔒 Роли других игроков остаются в секрете до конца игры!\n\n👤 Игроки:\n{}",
        "mafia_team": "Члены мафии:\n{}\n\n🤝 Только вы и эти люди знаете, что вы мафия!",
        "vote_menu": "Кого хотите выгнать?\n\n👉 Выберите одну из кнопок ниже:\n⏰ Время: {} секунд",
        "vote_cast": "{} → {}",
        "vote_none": "{} → не голосовал",
        "vote_stats": "📊 Проголосовало: {}/{} чел.\n⏰ Осталось времени: {:02d}:{:02d}",
        "time_up": "⏰ Время вышло! Не проголосовавшие:\n{}",
        "vote_results": "ДЕНЬ #{} РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ:\n\n📈 Отчет:\n{}\n\n🔥 Больше всего голосов: {}",
        "lynched": "{} выгнан (линчеван)!\n🎭 Роль остается в секрете...",
        "night_results": "НОЧЬ #{} РЕЗУЛЬТАТЫ:\n\n{}",
        "killed": "{} убит ночью!",
        "healed": "💊 Доктор вылечил жертву мафии!",
        "peaceful": "🌃 Никто не умер, ночь прошла спокойно.",
        "alive_players": "❤️ Живые игроки:\n{}",
        "citizen_win": "🎉 МИРНЫЕ ЖИТЕЛИ ПОБЕДИЛИ!\n\n🏆 Победители:\n{}\n\n🎭 ИГРОКИ И ИХ РОЛИ:\n\n{}",
        "mafia_win": "🎉 МАФИЯ ПОБЕДИЛА!\n\n🏆 Команда мафии:\n{}\n\n🎭 ИГРОКИ И ИХ РОЛИ:\n\n{}",
        "game_stopped": "Игра остановлена!\n\n🎭 СПИСОК ИГРОКОВ:\n\n{}",
        "rules": """📚 ПРАВИЛА ИГРЫ МАФИЯ:

1. Игра состоит из двух основных этапов:
   - 🌙 Ночь - действуют мафия, дон, комиссар и доктор
   - ☀️ День - все игроки голосуют

2. Роли:
   - 🎭 Мафия (2 чел.) - ночью убивает одного человека
   - 👑 Дон (1 чел.) - вместе с мафией, невидим для комиссара
   - 🔍 Комиссар (1 чел.) - ночью проверяет роль одного игрока
   - 💊 Доктор (1 чел.) - ночью лечит одного игрока
   - 👨‍👩‍👧‍👦 Мирные жители (6+ чел.) - должны найти мафию

3. Победа:
   - Мирные жители побеждают: когда все мафия и дон убиты
   - Мафия побеждает: когда мафии столько же или больше, чем мирных жителей

4. Голосование:
   - Днем все живые игроки голосуют, кого казнить
   - Игрок с наибольшим количеством голосов казнится

5. Примечания:
   - Роли сохраняются в секрете
   - Ночные действия совершаются в личных сообщениях
   - Есть временные ограничения""",
        "status_template": """🎮 СТАТУС ИГРЫ:

📊 Этап: {phase}
📅 День: #{day_count}
👥 Всего игроков: {total_players} чел.
❤️ Живых игроков: {alive_players} чел.
☠️ Мертвых игроков: {dead_players} чел.

{additional_info}""",
        "execute_vote_start": "⚖️ Началось голосование по казни {}!\n\nВремя голосования: {} секунд",
        "execute_vote_menu": "Казнить {}?\n\nДа - казнить\nНет - не казнить",
        "execute_vote_stats": "🗳️ Результаты голосования:\n✅ Да: {} голосов\n❌ Нет: {} голосов\n\nРешение: {}",
        "execute_killed": "✅ {} казнен!",
        "execute_spared": "❌ {} оставлен в живых!",
        "kill_vote_menu": "Кого хотите убить?\n\nВыберите через личные сообщения.",
        "check_vote_menu": "Кого хотите проверить?\n\nВыберите через личные сообщения.",
        "heal_vote_menu": "Кого хотите вылечить?\n\nВыберите через личные сообщения.",
        "language_set": "✅ Язык изменен на {}!",
        "bonus_toggled": "✅ Бонусные очки: {}",
        "group_vote_toggled": "✅ Голосование в группе: {}",
        "auto_kick_toggled": "✅ Авто-исключение: {}",
        "time_set": "✅ Время {} изменено на {} секунд!",
        "yes": "Да",
        "no": "Нет",
        "enabled": "Включено",
        "disabled": "Выключено"
    },
    "en": {
        "start": "🎮 Welcome to Mafia Game Bot!\n\n"
                "📋 Commands:\n"
                "/join - Join the game\n"
                "/begin - Start game (min 5 players)\n"
                "/players - Players list\n"
                "/status - Game status\n"
                "/next - Next phase\n"
                "/stop - Stop game\n"
                "/rules - Game rules\n"
                "/settings - Settings\n\n"
                "⚙️ Note: Roles are sent in private messages!",
        "join_button": "🎮 Join Game",
        "vote_button": "🗳️ Vote",
        "back_to_group": "⬅️ Back to Group",
        "back_to_bot": "🤖 Back to Bot",
        "vote_in_group": "📢 Vote in Group",
        "vote_in_private": "🔒 Vote Privately",
        "settings_menu": "⚙️ SETTINGS\n\n"
                        "1️⃣ Night time: {} seconds\n"
                        "2️⃣ Day time: {} seconds\n"
                        "3️⃣ Language: {}\n"
                        "4️⃣ Bonus points: {}\n"
                        "5️⃣ Group voting: {}\n"
                        "6️⃣ Auto-kick: {}",
        "settings_options": [
            ["🌙 Change Night Time", "set_night"],
            ["☀️ Change Day Time", "set_day"],
            ["🌐 Change Language", "set_language"],
            ["🎖️ Bonus Points", "toggle_bonus"],
            ["📢 Group Voting", "toggle_group_vote"],
            ["⚡ Auto-kick", "toggle_auto_kick"],
            ["🔙 Back", "back_to_main"]
        ],
        "joined": "{} joined the game!\n👥 Total: {} players\n🎯 Minimum: 5 players",
        "already_joined": "You've already joined or the game has started!",
        "not_enough": "Need at least 5 players!\n📊 Current: {} players\n🎯 Missing: {} players",
        "game_started": "GAME STARTED!\n\n👥 Players: {} players\n\n📢 Roles sent to private messages!",
        "night_start": "🌙 NIGHT #{} STARTED!\n\n🔒 Use private messages for secret actions.\n⏰ Time: {} seconds",
        "day_start": "☀️ DAY #{} STARTED!\n\n🗳️ Now let's vote – who to eliminate?\n\n❤️ Alive players: {} players\n⏰ Voting time: {} seconds\n⚠️ After time ends, non-voters will be kicked!",
        "role_assigned": "Your role: {}\n\n👥 Players: {} players\n🔒 Other players' roles remain secret until game end!\n\n👤 Players:\n{}",
        "mafia_team": "Mafia members:\n{}\n\n🤝 Only you and these people know you're mafia!",
        "vote_menu": "Who do you want to eliminate?\n\n👉 Choose one of the buttons below:\n⏰ Time: {} seconds",
        "vote_cast": "{} → {}",
        "vote_none": "{} → didn't vote",
        "vote_stats": "📊 Voted: {}/{} players\n⏰ Time left: {:02d}:{:02d}",
        "time_up": "⏰ Time's up! Non-voters:\n{}",
        "vote_results": "DAY #{} VOTING RESULTS:\n\n📈 Report:\n{}\n\n🔥 Most votes: {}",
        "lynched": "{} was eliminated (lynched)!\n🎭 Role remains secret...",
        "night_results": "NIGHT #{} RESULTS:\n\n{}",
        "killed": "{} was killed at night!",
        "healed": "💊 Doctor healed the mafia's victim!",
        "peaceful": "🌃 No one died, the night was peaceful.",
        "alive_players": "❤️ Alive players:\n{}",
        "citizen_win": "🎉 CITIZENS WIN!\n\n🏆 Winners:\n{}\n\n🎭 PLAYERS AND THEIR ROLES:\n\n{}",
        "mafia_win": "🎉 MAFIA WINS!\n\n🏆 Mafia team:\n{}\n\n🎭 PLAYERS AND THEIR ROLES:\n\n{}",
        "game_stopped": "Game stopped!\n\n🎭 PLAYERS LIST:\n\n{}",
        "rules": """📚 MAFIA GAME RULES:

1. The game consists of two main phases:
   - 🌙 Night - mafia, don, commissioner, and doctor act
   - ☀️ Day - all players vote

2. Roles:
   - 🎭 Mafia (2 players) - kills one person at night
   - 👑 Don (1 player) - with mafia, invisible to commissioner
   - 🔍 Commissioner (1 player) - checks one player's role at night
   - 💊 Doctor (1 player) - heals one player at night
   - 👨‍👩‍👧‍👦 Citizens (6+ players) - must find the mafia

3. Victory:
   - Citizens win: when all mafia and don are killed
   - Mafia wins: when mafia are equal or more than citizens

4. Voting:
   - During day, all alive players vote who to execute
   - Player with most votes is executed

5. Notes:
   - Roles are kept secret
   - Night actions are done via private messages
   - There are time limits""",
        "status_template": """🎮 GAME STATUS:

📊 Phase: {phase}
📅 Day: #{day_count}
👥 Total players: {total_players} players
❤️ Alive players: {alive_players} players
☠️ Dead players: {dead_players} players

{additional_info}""",
        "execute_vote_start": "⚖️ Execution vote for {} has started!\n\nVoting time: {} seconds",
        "execute_vote_menu": "Execute {}?\n\nYes - execute\nNo - don't execute",
        "execute_vote_stats": "🗳️ Voting results:\n✅ Yes: {} votes\n❌ No: {} votes\n\nDecision: {}",
        "execute_killed": "✅ {} was executed!",
        "execute_spared": "❌ {} was spared!",
        "kill_vote_menu": "Who do you want to kill?\n\nChoose via private messages.",
        "check_vote_menu": "Who do you want to check?\n\nChoose via private messages.",
        "heal_vote_menu": "Who do you want to heal?\n\nChoose via private messages.",
        "language_set": "✅ Language changed to {}!",
        "bonus_toggled": "✅ Bonus points: {}",
        "group_vote_toggled": "✅ Group voting: {}",
        "auto_kick_toggled": "✅ Auto-kick: {}",
        "time_set": "✅ {} time changed to {} seconds!",
        "yes": "Yes",
        "no": "No",
        "enabled": "Enabled",
        "disabled": "Disabled"
    }
}

# GIF'lar faqat kecha va kun uchun
GIFS = {
    "night": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "https://media.giphy.com/media/3o7aD2sRhnv7oKf0I0/giphy.gif",
        "https://media.giphy.com/media/26tknCqiJrBQG6DrW/giphy.gif",
    ],
    "day": [
        "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",
        "https://media.giphy.com/media/l0MYJfGZleVbqvaWQ/giphy.gif",
        "https://media.giphy.com/media/26tknCqiJrBQG6DrW/giphy.gif",
    ]
}

# Stickerlar faqat 5 ta rolda
STICKERS = {
    "uz": {
        "Mafia": "CAACAgIAAxkBAAEL6MJnaM1qYfq9UZfO3eFJk_rUqUJp-gAC2gADVp29Cmob68TH-pQrNAQ",
        "Don": "CAACAgIAAxkBAAEL6MRnaM1uEBzG_NmxWp19i_xhZKQkTwAC5wADVp29Cv2LKYyHXZ3RNAQ",
        "Shifokor": "CAACAgIAAxkBAAEL6MZnaM1wuxD-VJ9uBQwK6tAQkU0_pQAC7AADVp29Cr-TzSY2BM6zNAQ",
        "Komissar": "CAACAgIAAxkBAAEL6MhnaM1zONp98_YJXrBc8GTIFVlBXAAC8gADVp29CsdKPYX4T-MoNAQ",
        "Tinch aholi": "CAACAgIAAxkBAAEL6MpnaM12xHkUTly5-JvNqZ8Lkw4G_QAC9gADVp29CofxwFauq2D0NAQ"
    },
    "ru": {
        "Mafia": "CAACAgIAAxkBAAEL6MJnaM1qYfq9UZfO3eFJk_rUqUJp-gAC2gADVp29Cmob68TH-pQrNAQ",
        "Don": "CAACAgIAAxkBAAEL6MRnaM1uEBzG_NmxWp19i_xhZKQkTwAC5wADVp29Cv2LKYyHXZ3RNAQ",
        "Doktor": "CAACAgIAAxkBAAEL6MZnaM1wuxD-VJ9uBQwK6tAQkU0_pQAC7AADVp29Cr-TzSY2BM6zNAQ",
        "Komissar": "CAACAgIAAxkBAAEL6MhnaM1zONp98_YJXrBc8GTIFVlBXAAC8gADVp29CsdKPYX4T-MoNAQ",
        "Mernye zhytely": "CAACAgIAAxkBAAEL6MpnaM12xHkUTly5-JvNqZ8Lkw4G_QAC9gADVp29CofxwFauq2D0NAQ"
    },
    "en": {
        "Mafia": "CAACAgIAAxkBAAEL6MJnaM1qYfq9UZfO3eFJk_rUqUJp-gAC2gADVp29Cmob68TH-pQrNAQ",
        "Don": "CAACAgIAAxkBAAEL6MRnaM1uEBzG_NmxWp19i_xhZKQkTwAC5wADVp29Cv2LKYyHXZ3RNAQ",
        "Doctor": "CAACAgIAAxkBAAEL6MZnaM1wuxD-VJ9uBQwK6tAQkU0_pQAC7AADVp29Cr-TzSY2BM6zNAQ",
        "Commissioner": "CAACAgIAAxkBAAEL6MhnaM1zONp98_YJXrBc8GTIFVlBXAAC8gADVp29CsdKPYX4T-MoNAQ",
        "Citizen": "CAACAgIAAxkBAAEL6MpnaM12xHkUTly5-JvNqZ8Lkw4G_QAC9gADVp29CofxwFauq2D0NAQ"
    }
}

ROLES = {
    "uz": {
        "Mafia": 2,
        "Don": 1,
        "Komissar": 1,
        "Shifokor": 1,
        "Tinch aholi": 6
    },
    "ru": {
        "Mafia": 2,
        "Don": 1,
        "Komissar": 1,
        "Doktor": 1,
        "Mernye zhytely": 6
    },
    "en": {
        "Mafia": 2,
        "Don": 1,
        "Commissioner": 1,
        "Doctor": 1,
        "Citizen": 6
    }
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

def get_role_key(role, lang=None):
    """Get role key for current language"""
    if lang is None:
        lang = settings.get("language", "uz")
    
    # Find matching role in current language
    role_mapping = {
        "uz": {"Mafia": "Mafia", "Don": "Don", "Komissar": "Komissar", "Shifokor": "Shifokor", "Tinch aholi": "Tinch aholi"},
        "ru": {"Mafia": "Mafia", "Don": "Don", "Komissar": "Komissar", "Shifokor": "Doktor", "Tinch aholi": "Mernye zhytely"},
        "en": {"Mafia": "Mafia", "Don": "Don", "Komissar": "Commissioner", "Shifokor": "Doctor", "Tinch aholi": "Citizen"}
    }
    
    return role_mapping[lang].get(role, role)

def create_user_mention(user_id, name, username=None):
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
        self.execute_vote_target = None
        self.execute_votes = {"yes": [], "no": []}
       
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
    
    def get_players_list(self):
        lang = settings.get("language", "uz")
        players_text = ""
        for i, (uid, name, username, mention, bonus) in enumerate(self.players, 1):
            alive = "❤️" if uid in self.alive else "☠️"
            bonus_text = f" [+{bonus}]" if bonus > 0 else ""
            players_text += f"{i}. {alive} {mention}{bonus_text}\n"
        return players_text
    
    def assign_roles(self):
        lang = settings.get("language", "uz")
        pool = []
        for role, count in ROLES[lang].items():
            pool.extend([role] * count)
        extra_citizens = len(self.players) - len(pool)
        if extra_citizens > 0:
            base_role = "Tinch aholi" if lang == "uz" else "Mernye zhytely" if lang == "ru" else "Citizen"
            pool.extend([base_role] * extra_citizens)
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
        [InlineKeyboardButton("📋 Qoidalar", callback_data="rules"),
         InlineKeyboardButton("👥 O'yinchilar", callback_data="players")],
        [InlineKeyboardButton("📊 Holat", callback_data="status"),
         InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings")]
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
    
    lang_names = {"uz": "O'zbek 🇺🇿", "ru": "Русский 🇷🇺", "en": "English 🇺🇸"}
    current_lang = lang_names.get(lang, "O'zbek 🇺🇿")
    
    status_text = get_text("enabled", lang) if settings.get("bonus_points", True) else get_text("disabled", lang)
    group_vote_text = get_text("enabled", lang) if settings.get("vote_from_group", True) else get_text("disabled", lang)
    auto_kick_text = get_text("enabled", lang) if settings.get("auto_kick", True) else get_text("disabled", lang)
    
    message = get_text("settings_menu", lang).format(
        settings["night_duration"],
        settings["day_duration"],
        current_lang,
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
        text=f"👥 O'yinchilar: {len(game.players)} ta\n🎯 Minimal: 5 ta\n\n"
             f"✅ O'yinga qo'shilish uchun tugmani bosing!",
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
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.reply_text(message)
        return
    
    game = games[chat_id]
    
    if not game.players:
        message = "Hozircha o'yinchilar yo'q."
        if update.message:
            await update.message.reply_text(message)
        elif update.callback_query:
            await update.callback_query.message.reply_text(message)
        return
    
    players_text = f"👥 O'YINCHILAR RO'YXATI:\n\n"
    players_text += f"🎯 Jami: {len(game.players)} ta o'yinchi\n\n"
    players_text += game.get_players_list()
    players_text += f"\n📊 Minimal o'yinchilar: 5 ta"
    
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
                role_text += f"\n\n🎖️ Bonus ballaringiz: +{bonus}"
            
            await context.bot.send_message(
                chat_id=uid,
                text=role_text,
                parse_mode='HTML'
            )
            
            # Stiker yuborish
            sticker_lang = STICKERS.get(lang, STICKERS["uz"])
            if role in sticker_lang:
                try:
                    await context.bot.send_sticker(chat_id=uid, sticker=sticker_lang[role])
                except:
                    pass
            
            # Mafia uchun maxsus xabar
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
    
    await night_phase(context, chat_id)

# ---------------- NIGHT PHASE ----------------------
async def night_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    game.phase = "night"
    game.night_actions = {"mafia_kill": None, "heal": None, "check": None}
    game.votes.clear()
    game.vote_messages.clear()
    
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
    
    # Mafia va Don uchun
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
                    text=get_text("kill_vote_menu", lang),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                print(f"Mafia {uid} ga xabar yuborishda xato: {e}")
    
    # Komissar uchun
    komissar = next((uid for uid in game.alive if game.roles.get(uid) in ["Komissar", "Commissioner"]), None)
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
                text=get_text("check_vote_menu", lang),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Komissar {komissar} ga xabar yuborishda xato: {e}")
    
    # Shifokor/Doktor uchun
    doctor_key = "Shifokor" if lang == "uz" else "Doktor" if lang == "ru" else "Doctor"
    doctor = next((uid for uid in game.alive if game.roles.get(uid) == doctor_key), None)
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
                text=get_text("heal_vote_menu", lang),
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
                text="⏰ Tungi vaqt tugadi! Natijalar hisoblanmoqda..."
            )
            await resolve_night(context, chat_id)

async def resolve_night(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    
    victim = game.night_actions.get("mafia_kill")
    healed = game.night_actions.get("heal")
    
    night_result = ""
    
    if victim:
        if victim != healed:
            game.alive.discard(victim)
            victim_mention = game.get_player_mention(victim)
            night_result += get_text("killed", lang).format(victim_mention) + "\n"
        else:
            night_result += get_text("healed", lang) + "\n"
    else:
        night_result += get_text("peaceful", lang) + "\n"
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=get_text("night_results", lang).format(game.day_count, night_result),
        parse_mode='HTML'
    )
    
    # Check game end
    mafia_count = sum(1 for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"])
    citizens_count = sum(1 for uid in game.alive if game.roles.get(uid) not in ["Mafia", "Don"])
    
    if mafia_count == 0:
        await end_game(context, chat_id, "citizen")
        return
    elif mafia_count >= citizens_count:
        await end_game(context, chat_id, "mafia")
        return
    
    game.day_count += 1
    await day_phase(context, chat_id)

# ---------------- DAY PHASE ----------------------
async def day_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    game.phase = "day"
    game.votes.clear()
    game.vote_messages.clear()
    game.execute_vote_target = None
    game.execute_votes = {"yes": [], "no": []}
    game.vote_end_time = datetime.now() + timedelta(seconds=settings["day_duration"])
    
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
    
    # Create voting buttons
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
    
    keyboard.append([InlineKeyboardButton("❌ " + get_text("vote_none", lang).split("→")[0].strip(), callback_data="vote:none")])
    
    if settings.get("vote_from_group", True):
        keyboard.append([
            InlineKeyboardButton(get_text("vote_in_private", lang), callback_data="vote_private"),
            InlineKeyboardButton(get_text("back_to_bot", lang), url=f"https://t.me/{context.bot.username}")
        ])
    
    vote_text = get_text("vote_menu", lang).format(settings["day_duration"])
    
    if settings.get("vote_from_group", True):
        vote_message = await context.bot.send_message(
            chat_id=chat_id,
            text=vote_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        game.group_vote_message_id = vote_message.message_id
    
    for uid in game.alive:
        try:
            private_keyboard = keyboard.copy()
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

async def resolve_day(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    
    if not game.votes:
        await context.bot.send_message(chat_id=chat_id, text="Hech kim ovoz bermadi. O'yin davom etadi.")
        await night_phase(context, chat_id)
        return
    
    vote_counts = Counter(game.votes.values())
    
    if "none" in vote_counts:
        del vote_counts["none"]
    
    if not vote_counts:
        await context.bot.send_message(chat_id=chat_id, text="Hech kimga ovoz berilmadi. O'yin davom etadi.")
        await night_phase(context, chat_id)
        return
    
    max_votes = max(vote_counts.values())
    candidates = [uid for uid, count in vote_counts.items() if count == max_votes]
    
    vote_report = ""
    for voter_id, target_id in game.votes.items():
        voter_name = game.get_player_name(voter_id)
        if target_id == "none":
            vote_report += get_text("vote_none", lang).format(voter_name) + "\n"
        else:
            target_name = game.get_player_name(target_id)
            vote_report += get_text("vote_cast", lang).format(voter_name, target_name) + "\n"
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=get_text("vote_results", lang).format(game.day_count, vote_report, ", ".join([game.get_player_name(uid) for uid in candidates])),
        parse_mode='HTML'
    )
    
    if len(candidates) == 1:
        target_uid = candidates[0]
        target_mention = game.get_player_mention(target_uid)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("execute_vote_start", lang).format(target_mention, 30)
        )
        
        game.execute_vote_target = target_uid
        game.execute_votes = {"yes": [], "no": []}
        
        keyboard = [
            [InlineKeyboardButton("✅ " + get_text("yes", lang), callback_data="execute_yes")],
            [InlineKeyboardButton("❌ " + get_text("no", lang), callback_data="execute_no")]
        ]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("execute_vote_menu", lang).format(target_mention),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await asyncio.sleep(30)
        
        await resolve_execute_vote(context, chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="Teng ovoz bo'ldi. Hech kim o'ldirilmaydi.")
        await night_phase(context, chat_id)

async def resolve_execute_vote(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    
    if not game.execute_vote_target:
        await context.bot.send_message(chat_id=chat_id, text="Ovoz berish bekor qilindi.")
        await night_phase(context, chat_id)
        return
    
    yes_votes = len(game.execute_votes["yes"])
    no_votes = len(game.execute_votes["no"])
    target_mention = game.get_player_mention(game.execute_vote_target)
    
    result_text = get_text("execute_vote_stats", lang).format(yes_votes, no_votes, "")
    
    if yes_votes > no_votes:
        game.alive.discard(game.execute_vote_target)
        result_text += get_text("execute_killed", lang).format(target_mention)
    else:
        result_text += get_text("execute_spared", lang).format(target_mention)
    
    await context.bot.send_message(chat_id=chat_id, text=result_text, parse_mode='HTML')
    
    mafia_count = sum(1 for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"])
    citizens_count = sum(1 for uid in game.alive if game.roles.get(uid) not in ["Mafia", "Don"])
    
    if mafia_count == 0:
        await end_game(context, chat_id, "citizen")
        return
    elif mafia_count >= citizens_count:
        await end_game(context, chat_id, "mafia")
        return
    
    await night_phase(context, chat_id)

async def end_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int, winner: str):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    
    game.cancel_timer()
    
    players_with_roles = ""
    for uid, name, username, mention, bonus in game.players:
        role = game.roles.get(uid, "Noma'lum")
        alive = "❤️" if uid in game.alive else "☠️"
        players_with_roles += f"• {alive} {mention}: {role}\n"
    
    if winner == "citizen":
        winners = [game.get_player_mention(uid) for uid in game.alive if game.roles.get(uid) not in ["Mafia", "Don"]]
        winner_text = get_text("citizen_win", lang).format("\n".join(winners), players_with_roles)
    else:
        winners = [game.get_player_mention(uid) for uid in game.alive if game.roles.get(uid) in ["Mafia", "Don"]]
        winner_text = get_text("mafia_win", lang).format("\n".join(winners), players_with_roles)
    
    await context.bot.send_message(chat_id=chat_id, text=winner_text, parse_mode='HTML')
    
    del games[chat_id]

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        await update.message.reply_text("Hozircha o'yin yo'q!")
        return
    
    game = games[chat_id]
    game.cancel_timer()
    
    players_list = game.get_players_list()
    
    await update.message.reply_text(
        get_text("game_stopped", lang).format(players_list),
        parse_mode='HTML'
    )
    
    del games[chat_id]

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = settings.get("language", "uz")
    rules_text = get_text("rules", lang)
    
    await update.message.reply_text(rules_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        await update.message.reply_text(get_text("game_stopped", lang).format("Hozircha o'yin yo'q!"))
        return
    
    game = games[chat_id]
    
    phase_text = "🌙 Kecha" if game.phase == "night" else "☀️ Kun"
    phase_text = "🌙 Ночь" if lang == "ru" and game.phase == "night" else "☀️ День" if lang == "ru" and game.phase == "day" else phase_text
    phase_text = "🌙 Night" if lang == "en" and game.phase == "night" else "☀️ Day" if lang == "en" and game.phase == "day" else phase_text
    
    additional_info = ""
    if game.phase == "day":
        additional_info = f"⏰ Ovoz berish vaqti: {settings['day_duration']} soniya\n"
        additional_info += f"🗳️ Ovoz berdi: {len(game.votes)}/{len(game.alive)} ta\n"
        if lang == "ru":
            additional_info = f"⏰ Время голосования: {settings['day_duration']} секунд\n"
            additional_info += f"🗳️ Проголосовало: {len(game.votes)}/{len(game.alive)} чел.\n"
        elif lang == "en":
            additional_info = f"⏰ Voting time: {settings['day_duration']} seconds\n"
            additional_info += f"🗳️ Voted: {len(game.votes)}/{len(game.alive)} players\n"
    else:
        additional_info = f"⏰ Kecha vaqti: {settings['night_duration']} soniya\n"
        if lang == "ru":
            additional_info = f"⏰ Ночное время: {settings['night_duration']} секунд\n"
        elif lang == "en":
            additional_info = f"⏰ Night time: {settings['night_duration']} seconds\n"
    
    status_text = get_text("status_template", lang).format(
        phase=phase_text,
        day_count=game.day_count,
        total_players=len(game.players),
        alive_players=len(game.alive),
        dead_players=len(game.players) - len(game.alive),
        additional_info=additional_info
    )
    
    await update.message.reply_text(status_text)

# ---------------- CALLBACK HANDLERS -----------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    lang = settings.get("language", "uz")
    chat_id = query.message.chat.id
    
    if data == "join_game":
        if chat_id not in games:
            games[chat_id] = Game(chat_id)
        
        game = games[chat_id]
        user = query.from_user
        
        if game.add_player(user.id, user.full_name, user.username):
            await update_join_button(context, chat_id, lang)
            await query.edit_message_text(
                get_text("joined", lang).format(user.full_name, len(game.players)),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Yangilash", callback_data="join_game")]])
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
        lang_names = {"uz": "tungi", "ru": "ночного", "en": "night"}
        time_name = lang_names.get(lang, "tungi")
        await query.edit_message_text(
            f"🌙 {time_name.capitalize()} vaqtni kiriting (soniyada):\n"
            f"Masalan: 60, 90, 120\n\n"
            f"Joriy vaqt: {settings['night_duration']} soniya"
        )
        context.user_data["waiting_for"] = "night_time"
    
    elif data == "set_day":
        lang_names = {"uz": "kunduzgi", "ru": "дневного", "en": "day"}
        time_name = lang_names.get(lang, "kunduzgi")
        await query.edit_message_text(
            f"☀️ {time_name.capitalize()} vaqtni kiriting (soniyada):\n"
            f"Masalan: 120, 180, 240\n\n"
            f"Joriy vaqt: {settings['day_duration']} soniya"
        )
        context.user_data["waiting_for"] = "day_time"
    
    elif data == "set_language":
        keyboard = [
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton("🔙 " + get_text("back_to_group", lang).split()[0], callback_data="settings")]
        ]
        await query.edit_message_text(
            "🌐 Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("lang_"):
        lang_code = data.split("_")[1]
        settings["language"] = lang_code
        save_settings()
        
        lang_names = {"uz": "O'zbek", "ru": "Русский", "en": "English"}
        lang_name = lang_names.get(lang_code, "O'zbek")
        
        await query.answer(get_text("language_set", lang_code).format(lang_name), show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_bonus":
        settings["bonus_points"] = not settings.get("bonus_points", True)
        save_settings()
        status = get_text("enabled", lang) if settings["bonus_points"] else get_text("disabled", lang)
        await query.answer(get_text("bonus_toggled", lang).format(status), show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_group_vote":
        settings["vote_from_group"] = not settings.get("vote_from_group", True)
        save_settings()
        status = get_text("enabled", lang) if settings["vote_from_group"] else get_text("disabled", lang)
        await query.answer(get_text("group_vote_toggled", lang).format(status), show_alert=True)
        await settings_command(update, context)
    
    elif data == "toggle_auto_kick":
        settings["auto_kick"] = not settings.get("auto_kick", True)
        save_settings()
        status = get_text("enabled", lang) if settings["auto_kick"] else get_text("disabled", lang)
        await query.answer(get_text("auto_kick_toggled", lang).format(status), show_alert=True)
        await settings_command(update, context)
    
    elif data == "back_to_main":
        await start(update, context)
    
    elif data.startswith("vote:"):
        await handle_vote_callback(query, context, data)
    
    elif data == "vote:none":
        await handle_vote_none(query, context)
    
    elif data == "vote_private":
        await query.answer("Shaxsiy xabarlaringizni tekshiring!", show_alert=True)
    
    elif data.startswith("kill:"):
        await handle_night_action(query, context, data, "mafia_kill")
    
    elif data.startswith("check:"):
        await handle_night_action(query, context, data, "check")
    
    elif data.startswith("heal:"):
        await handle_night_action(query, context, data, "heal")
    
    elif data == "execute_yes":
        await handle_execute_vote(query, context, "yes")
    
    elif data == "execute_no":
        await handle_execute_vote(query, context, "no")

async def handle_vote_callback(query, context, data):
    chat_id = query.message.chat.id
    if chat_id not in games:
        return
    
    game = games[chat_id]
    voter_id = query.from_user.id
    
    if voter_id not in game.alive or game.phase != "day":
        await query.answer("Siz ovoz bera olmaysiz!", show_alert=True)
        return
    
    target_id = int(data.split(":")[1])
    
    if target_id not in game.alive:
        await query.answer("Bu o'yinchi tirik emas!", show_alert=True)
        return
    
    game.votes[voter_id] = target_id
    target_name = game.get_player_name(target_id)
    
    lang = settings.get("language", "uz")
    await query.answer(f"Ovozingiz {target_name} uchun qabul qilindi!", show_alert=True)
    
    try:
        await query.edit_message_text(f"✅ Siz {target_name} uchun ovoz berdingiz!")
    except:
        pass

async def handle_vote_none(query, context):
    chat_id = query.message.chat.id
    if chat_id not in games:
        return
    
    game = games[chat_id]
    voter_id = query.from_user.id
    
    if voter_id not in game.alive or game.phase != "day":
        await query.answer("Siz ovoz bera olmaysiz!", show_alert=True)
        return
    
    game.votes[voter_id] = "none"
    
    await query.answer("Hech kimga ovoz bermadingiz!", show_alert=True)
    
    try:
        await query.edit_message_text("✅ Siz hech kimga ovoz bermadingiz!")
    except:
        pass

async def handle_night_action(query, context, data, action_type):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    if chat_id not in games:
        return
    
    game = games[chat_id]
    lang = settings.get("language", "uz")
    
    if game.phase != "night":
        await query.answer("Bu kecha harakati emas!", show_alert=True)
        return
    
    # Check action permission
    if action_type == "mafia_kill" and game.roles.get(user_id) not in ["Mafia", "Don"]:
        await query.answer("Siz mafia emassiz!", show_alert=True)
        return
    elif action_type == "check" and game.roles.get(user_id) not in ["Komissar", "Commissioner"]:
        await query.answer("Siz komissar emassiz!", show_alert=True)
        return
    elif action_type == "heal":
        doctor_key = "Shifokor" if lang == "uz" else "Doktor" if lang == "ru" else "Doctor"
        if game.roles.get(user_id) != doctor_key:
            await query.answer("Siz shifokor emassiz!", show_alert=True)
            return
    
    target_id = int(data.split(":")[1])
    game.night_actions[action_type] = target_id
    target_name = game.get_player_name(target_id)
    
    if action_type == "mafia_kill":
        await query.answer(f"{target_name} ni o'ldirishni tanladingiz!", show_alert=True)
    elif action_type == "check":
        role = game.roles.get(target_id, "Noma'lum")
        await query.answer(f"{target_name} ning roli: {role}", show_alert=True)
    elif action_type == "heal":
        await query.answer(f"{target_name} ni davolashni tanladingiz!", show_alert=True)
    
    try:
        await query.edit_message_text(f"✅ Tanlovingiz qabul qilindi!")
    except:
        pass

async def handle_execute_vote(query, context, vote_type):
    chat_id = query.message.chat.id
    if chat_id not in games:
        return
    
    game = games[chat_id]
    voter_id = query.from_user.id
    
    if not game.execute_vote_target:
        await query.answer("Ovoz berish jarayoni tugagan!", show_alert=True)
        return
    
    if voter_id not in game.alive:
        await query.answer("Siz tirik emassiz!", show_alert=True)
        return
    
    # Check if already voted
    if voter_id in game.execute_votes["yes"] or voter_id in game.execute_votes["no"]:
        await query.answer("Siz allaqachon ovoz bergansiz!", show_alert=True)
        return
    
    game.execute_votes[vote_type].append(voter_id)
    
    lang = settings.get("language", "uz")
    if vote_type == "yes":
        await query.answer(get_text("yes", lang) + " - ovoz berdingiz!", show_alert=True)
    else:
        await query.answer(get_text("no", lang) + " - ovoz berdingiz!", show_alert=True)

# ---------------- MESSAGE HANDLER FOR SETTINGS -----------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for" in context.user_data:
        waiting_for = context.user_data.pop("waiting_for", None)
        text = update.message.text
        
        try:
            value = int(text)
            if value < 30:
                await update.message.reply_text("❌ Vaqt 30 soniyadan kam bo'lmasligi kerak!")
                return
            if value > 300:
                await update.message.reply_text("❌ Vaqt 5 daqiqadan (300 sekund) ko'p bo'lmasligi kerak!")
                return
            
            lang = settings.get("language", "uz")
            if waiting_for == "night_time":
                settings["night_duration"] = value
                time_name = "tungi" if lang == "uz" else "ночное" if lang == "ru" else "night"
                await update.message.reply_text(get_text("time_set", lang).format(time_name.capitalize(), value))
            elif waiting_for == "day_time":
                settings["day_duration"] = value
                time_name = "kunduzgi" if lang == "uz" else "дневное" if lang == "ru" else "day"
                await update.message.reply_text(get_text("time_set", lang).format(time_name.capitalize(), value))
            
            save_settings()
            await settings_command(update, context)
            
        except ValueError:
            await update.message.reply_text("❌ Iltimos, faqat raqam kiriting!")

# ---------------- MAIN ------------------------
def main():
    load_settings()
    
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
    app.add_handler(CommandHandler("next", lambda u, c: next_phase(u, c)))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handler (sozlamalar uchun)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🎮 Mafia Bot ishga tushdi!")
    print("📋 Buyruqlar:")
    print(" /start - Botni ishga tushirish")
    print(" /join - O'yinga qo'shilish")
    print(" /begin - O'yinni boshlash")
    print(" /players - O'yinchilar ro'yxati")
    print(" /status - O'yin holati")
    print(" /rules - O'yin qoidalari")
    print(" /settings - Sozlamalar")
    print(" /stop - O'yinni to'xtatish")
    print(" /next - Keyingi bosqichga o'tish")
    
    app.run_polling()

async def next_phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = settings.get("language", "uz")
    
    if chat_id not in games:
        await update.message.reply_text("Hozircha o'yin yo'q!")
        return
    
    game = games[chat_id]
    
    if not game.started:
        await update.message.reply_text("O'yin boshlanmagan!")
        return
    
    game.cancel_timer()
    
    if game.phase == "night":
        await resolve_night(context, chat_id)
    elif game.phase == "day":
        await resolve_day(context, chat_id)

if __name__ == "__main__":
    main()
