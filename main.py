from datetime import datetime, timedelta
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
    "smoking": 10
}
BATAS_HARIAN = 75
DENDA_MELEBIHI_BATAS = 100
DENDA_PERINGATAN = 10
jam_rekap = "00:00"

izin_log = {}
harian_durasi = {}
peringatan_user = {}
rekap_data = {}

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
        pesan = "\U0001F4CA Rekap Harian Izin:\n"
        for user_id, total in user_data.items():
            nama = f"<a href='tg://user?id={user_id}'>User</a>"
            pesan += f"• {nama}: {round(total, 2)} menit\n"
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

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower().strip()

    if message.reply_to_message and message.reply_to_message.message_id in izin_log:
        data = izin_log.pop(message.reply_to_message.message_id)
        durasi = round((now() - data["timestamp"]).total_seconds() / 60, 2)
        jenis = data["jenis"]
        batas = IZIN_BATAS[jenis]
        nama = data["nama"]

        harian_durasi[user_id] = harian_durasi.get(user_id, 0) + durasi
        rekap_data.setdefault(chat_id, {})
        rekap_data[chat_id][user_id] = rekap_data[chat_id].get(user_id, 0) + durasi

        if durasi <= batas:
            bot.reply_to(message, f"✅ @{message.from_user.username or nama} selesai {jenis.title()} dalam {durasi} menit. Tepat waktu.")
        else:
            bot.reply_to(message, f"⚠️ @{message.from_user.username or nama} terlambat kembali ({durasi} menit). Batas {batas} menit untuk {jenis.title()}. Sanksi: ${DENDA_PERINGATAN}")

        if harian_durasi[user_id] > BATAS_HARIAN:
            bot.send_message(chat_id, f"⚠️ @{message.from_user.username or nama} total izin harian melebihi {BATAS_HARIAN} menit. Sanksi: ${DENDA_MELEBIHI_BATAS}")

    elif text.startswith("/toilet") or text.startswith("/bab") or text.startswith("/smoke") or text.startswith("/smoking"):
        jenis = text.replace("/", "").strip()
        if jenis == "smoke":
            jenis = "smoking"
        if jenis not in IZIN_BATAS:
            bot.reply_to(message, "❌ Jenis izin tidak valid. Gunakan: /Toilet, /Bab, /Smoke, atau /Smoking.")
            return
        izin_log[message.message_id] = {
            "user_id": user_id,
            "timestamp": now(),
            "jenis": jenis,
            "nama": message.from_user.first_name
        }
        bot.reply_to(message, f"✅ Izin {jenis.title()} dicatat. Balas pesan ini saat kembali.")

    else:
        count = peringatan_user.get(user_id, 0)
        if count == 0:
            bot.reply_to(message, "⚠️ Format izin salah. Gunakan perintah seperti:\n/Toilet\n/Bab\n/Smoke\nPeringatan pertama!")
            peringatan_user[user_id] = 1
        elif count == 1:
            bot.reply_to(message, f"❌ Izin ditolak. Anda melanggar dua kali.\nSanksi: ${DENDA_PERINGATAN}")
            peringatan_user[user_id] = 2

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=20)
