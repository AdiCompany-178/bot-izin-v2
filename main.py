from datetime import datetime, timedelta
import os
import telebot
import threading
import time

API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Konfigurasi
IZIN_BATAS = {
    "toilet": 4.5,     # 4 menit 30 detik
    "bab": 16,
    "smoking": 11,
    "smoke": 11
}
BATAS_HARIAN = 75
DENDA_MELEBIHI_BATAS = 100
DENDA_PERINGATAN = 10
jam_rekap = "00:00"

izin_log = {}         # msg_id: data izin
harian_durasi = {}    # user_id: total_menit
peringatan_user = {}  # user_id: warning_count
rekap_data = {}       # group_id: {user_id: total_menit}

# Utilitas waktu
def now():
    return datetime.now()

def reset_harian():
    global harian_durasi, peringatan_user, rekap_data
    harian_durasi = {}
    peringatan_user = {}
    rekap_data = {}

def kirim_rekap():
    for group_id, user_data in rekap_data.items():
        if not user_data:
            continue
        pesan = "📊 Rekap Harian Izin:\n"
        for user_id, total in user_data.items():
            mention = f"<a href='tg://user?id={user_id}'>User</a>"
            pesan += f"• {mention}: {round(total, 2)} menit\n"
            if total > BATAS_HARIAN:
                pesan += f"  ⚠️ Melebihi batas. Sanksi: ${DENDA_MELEBIHI_BATAS}\n"
        try:
            bot.send_message(group_id, pesan, parse_mode="HTML")
        except:
            pass

def scheduler():
    while True:
        if datetime.now().strftime("%H:%M") == jam_rekap:
            kirim_rekap()
            reset_harian()
        time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

# Reminder Timer
def set_reminder(chat_id, msg_id, user_id, jenis, waktu_mulai, batas):
    waktu_habis = waktu_mulai + timedelta(minutes=batas)
    waktu_reminder = waktu_habis - timedelta(minutes=1)

    delay = (waktu_reminder - now()).total_seconds()
    if delay > 0:
        time.sleep(delay)

    if msg_id in izin_log:
        nama = izin_log[msg_id]["nama"]
        username = izin_log[msg_id]["username"]
        mention = f"@{username}" if username else nama
        try:
            bot.send_message(chat_id, f"⏰ {mention} belum kembali dari {jenis.title()}\nBatas waktu {batas} menit segera habis!")
        except:
            pass

# Handler
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip().lower()
    username = message.from_user.username
    nama = message.from_user.first_name
    mention = f"@{username}" if username else nama

    # Balasan (selesai izin)
    if message.reply_to_message and message.reply_to_message.message_id in izin_log:
        data = izin_log.pop(message.reply_to_message.message_id)
        waktu_mulai = data["timestamp"]
        jenis = data["jenis"]
        durasi = round((now() - waktu_mulai).total_seconds() / 60, 2)
        batas = IZIN_BATAS[jenis]

        harian_durasi[user_id] = harian_durasi.get(user_id, 0) + durasi
        rekap_data.setdefault(chat_id, {})
        rekap_data[chat_id][user_id] = rekap_data[chat_id].get(user_id, 0) + durasi

        if durasi <= batas:
            bot.reply_to(message, f"✅ {jenis.title()} oleh {mention} selesai dalam {durasi} menit. Tepat waktu.")
        else:
            bot.reply_to(message, f"⚠️ {mention} terlambat kembali ({durasi} menit). Batas {batas} menit untuk {jenis.title()}. Sanksi: ${DENDA_PERINGATAN}")

        if harian_durasi[user_id] > BATAS_HARIAN:
            bot.send_message(chat_id, f"⚠️ Total izin harian melebihi {BATAS_HARIAN} menit.\nSanksi: ${DENDA_MELEBIHI_BATAS}")
        return

    # Perintah izin
    perintah = text.replace("/", "")
    if perintah in ["toilet", "bab", "smoking", "smoke"]:
        izin_log[message.message_id] = {
            "user_id": user_id,
            "timestamp": now(),
            "jenis": perintah,
            "nama": nama,
            "username": username
        }
        bot.reply_to(message, f"✅ Izin {perintah.title()} dicatat. Balas pesan ini saat kembali.")
        batas = IZIN_BATAS[perintah]
        threading.Thread(target=set_reminder, args=(chat_id, message.message_id, user_id, perintah, now(), batas), daemon=True).start()
        return

    # Salah format
    count = peringatan_user.get(user_id, 0)
    if count == 0:
        bot.reply_to(message, "⚠️ Format izin salah. Gunakan perintah seperti:\n/Toilet\n/Bab\n/Smoke")
        peringatan_user[user_id] = 1
    elif count == 1:
        bot.reply_to(message, f"❌ Izin ditolak. Anda melanggar dua kali.\nSanksi: ${DENDA_PERINGATAN}")
        peringatan_user[user_id] = 2

bot.polling()
