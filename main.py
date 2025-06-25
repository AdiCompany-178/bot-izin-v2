from datetime import datetime
import os
import telebot
import threading
import time

API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Konfigurasi
IZIN_BATAS = {
    "toilet": 4,
    "bab": 16,
    "smoking": 10.5
}
BATAS_HARIAN = 75  # menit
DENDA_MELEBIHI_BATAS = 100  # USD
DENDA_PERINGATAN = 10  # USD
jam_rekap = "00:00"

izin_log = {}
harian_durasi = {}
peringatan_user = {}
rekap_data = {}
rekap_nama = {}
user_kena_denda = set()

# Utilitas
def now():
    return datetime.now()

def mention_user(user):
    if user.username:
        return f"@{user.username}"
    else:
        return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

def reset_harian():
    global harian_durasi, peringatan_user, rekap_data, user_kena_denda
    harian_durasi = {}
    peringatan_user = {}
    rekap_data = {}
    user_kena_denda = set()

def kirim_rekap():
    for group_id, user_data in rekap_data.items():
        if not user_data:
            continue
        pesan = "📊 Rekap Harian Izin:\n"
        for user_id, total in user_data.items():
            nama = rekap_nama.get(user_id, f"<a href='tg://user?id={user_id}'>User</a>")
            pesan += f"• {nama}: {round(total, 2)} menit\n"
            if total > BATAS_HARIAN:
                pesan += f"  ⚠️ Melebihi batas. Sanksi: ${DENDA_MELEBIHI_BATAS}\n"
        try:
            bot.send_message(group_id, pesan, parse_mode="HTML")
        except Exception as e:
            print(f"❌ Gagal kirim rekap: {e}")

def scheduler():
    while True:
        now_time = datetime.now().strftime("%H:%M")
        if now_time == jam_rekap:
            kirim_rekap()
            reset_harian()
        time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

# Handler utama
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user = message.from_user
    user_id = user.id
    chat_id = message.chat.id
    text = message.text.lower().strip()
    rekap_nama[user_id] = mention_user(user)

    if message.reply_to_message:
        izin_data = izin_log.get(message.reply_to_message.message_id)
        if not izin_data:
            bot.reply_to(message, "⛔ Izin ini sudah diproses atau tidak ditemukan.")
            return

        data = izin_log.pop(message.reply_to_message.message_id)
        durasi = round((now() - data["timestamp"]).total_seconds() / 60, 2)
        jenis = data["jenis"]
        batas = IZIN_BATAS[jenis]
        nama = data["nama"]

        harian_durasi[user_id] = harian_durasi.get(user_id, 0) + durasi
        rekap_data.setdefault(chat_id, {})
        rekap_data[chat_id][user_id] = rekap_data[chat_id].get(user_id, 0) + durasi

        if durasi <= batas:
            bot.reply_to(message, f"✅ {jenis.title()} oleh {nama} selesai dalam {durasi} menit. Tepat waktu.")
        else:
            bot.reply_to(message, f"⚠️ Terlambat kembali ({durasi} menit). Batas {batas} menit untuk {jenis.title()}.\nSanksi: ${DENDA_PERINGATAN}")

        if harian_durasi[user_id] > BATAS_HARIAN and user_id not in user_kena_denda:
            bot.send_message(chat_id, f"⚠️ {rekap_nama[user_id]} melebihi batas izin harian {BATAS_HARIAN} menit.\nSanksi: ${DENDA_MELEBIHI_BATAS}", parse_mode="HTML")
            user_kena_denda.add(user_id)

    elif text.startswith("/izin "):
        jenis = text.replace("/izin ", "")
        if jenis not in IZIN_BATAS:
            bot.reply_to(message, "❌ Jenis izin tidak valid. Gunakan: /izin toilet, /izin bab, atau /izin smoking.")
            return
        izin_log[message.message_id] = {
            "user_id": user_id,
            "timestamp": now(),
            "jenis": jenis,
            "nama": mention_user(user)
        }
        bot.reply_to(message, f"✅ Izin {jenis.title()} dicatat. Balas pesan ini saat kembali.")

    else:
        count = peringatan_user.get(user_id, 0)
        if count == 0:
            bot.reply_to(message, "⚠️ Format izin salah. Gunakan perintah seperti: /izin toilet, /izin bab, /izin smoking.\nPeringatan pertama!")
            peringatan_user[user_id] = 1
        elif count == 1:
            bot.reply_to(message, f"❌ Izin ditolak. Anda melanggar dua kali.\nSanksi: ${DENDA_PERINGATAN}")
            peringatan_user[user_id] = 2

bot.polling()
