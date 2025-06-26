from datetime import datetime, timedelta, time
import os
import telebot
import threading
import time as t

API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

IZIN_BATAS = {
    "toilet": 4.5,
    "bab": 16,
    "smoking": 11,
    "smoke": 11,
    "smoking2": 11,
    "smoke2": 11,
    "smoking3": 11,
    "smoke3": 11,
    "smoking4": 11,
    "smoke4": 11
}
BATAS_HARIAN = 75
DENDA_MELEBIHI_BATAS = 100
DENDA_PERINGATAN = 10
jam_rekap = "00:00"

izin_log = {}
harian_durasi = {}
peringatan_user = {}
rekap_data = {}
denda_otomatis = set()
aktif_smoke = {}
aktif_pimpinan = {}

MAX_PIMPINAN_IZIN = 4

def dilarang_smoke_now():
    sekarang = datetime.now().time()
    larangan = [
        (time(8, 0), time(8, 20)),
        (time(8, 55), time(9, 25)),
        (time(10, 30), time(11, 0)),
        (time(13, 0), time(13, 30)),
        (time(14, 30), time(14, 45)),
        (time(15, 30), time(16, 0)),
        (time(17, 0), time(17, 30)),
        (time(20, 0), time(20, 15)),
        (time(20, 30), time(21, 0)),
        (time(21, 30), time(22, 0)),
        (time(22, 30), time(23, 0))
    ]
    return any(start <= sekarang < end for start, end in larangan)

def now():
    return datetime.now()

def reset_harian():
    global harian_durasi, peringatan_user, rekap_data, denda_otomatis, aktif_smoke, aktif_pimpinan
    harian_durasi = {}
    peringatan_user = {}
    rekap_data = {}
    denda_otomatis = set()
    aktif_smoke = {}
    aktif_pimpinan = {}

def kirim_rekap():
    for group_id, user_data in rekap_data.items():
        if not user_data:
            continue
        pesan = "\U0001F4CA Rekap Harian Izin:\n"
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
        t.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

def reminder_and_sanksi(chat_id, msg_id, user_id, jenis, waktu_mulai, batas):
    reminder_delay = (waktu_mulai + timedelta(minutes=batas - 1)) - now()
    if reminder_delay.total_seconds() > 0:
        t.sleep(reminder_delay.total_seconds())
        if msg_id in izin_log:
            mention = f"@{izin_log[msg_id]['username']}" if izin_log[msg_id]['username'] else izin_log[msg_id]['nama']
            bot.send_message(chat_id, f"⏰ {mention} belum kembali dari {jenis.title()}\nBatas waktu {batas} menit segera habis!")

    sanksi_delay = (waktu_mulai + timedelta(minutes=batas + 5)) - now()
    if sanksi_delay.total_seconds() > 0:
        t.sleep(sanksi_delay.total_seconds())
        if msg_id in izin_log:
            mention = f"@{izin_log[msg_id]['username']}" if izin_log[msg_id]['username'] else izin_log[msg_id]['nama']
            bot.send_message(chat_id, f"⛔ {mention} tidak membalas izin {jenis.title()} dalam {batas + 5} menit.\nSanksi: ${DENDA_PERINGATAN}")
            denda_otomatis.add((chat_id, msg_id))

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip().lower()
    username = message.from_user.username
    nama = message.from_user.first_name
    mention = f"@{username}" if username else nama

    if message.reply_to_message:
        ref_id = message.reply_to_message.message_id
        if ref_id not in izin_log:
            return

        data = izin_log.pop(ref_id)
        jenis = data['jenis']
        mulai = data['timestamp']
        durasi = round((now() - mulai).total_seconds() / 60, 2)
        batas = IZIN_BATAS[jenis]

        harian_durasi[user_id] = harian_durasi.get(user_id, 0) + durasi
        rekap_data.setdefault(chat_id, {})
        rekap_data[chat_id][user_id] = rekap_data[chat_id].get(user_id, 0) + durasi

        if jenis in ["smoke", "smoking"] and chat_id in aktif_smoke:
            aktif_smoke.pop(chat_id, None)
        elif jenis in ["smoke2", "smoking2", "smoke3", "smoking3", "smoke4", "smoking4"]:
            aktif_pimpinan[chat_id].discard(user_id)

        if durasi <= batas:
            bot.reply_to(message, f"✅ {jenis.title()} oleh {mention} selesai dalam {durasi} menit. Tepat waktu.")
        elif durasi <= batas + 5:
            bot.reply_to(message, f"⚠️ {mention} terlambat kembali ({durasi} menit). Batas {batas} menit untuk {jenis.title()}\nTerima kasih, Anda tetap terlambat.")
        else:
            bot.reply_to(message, f"⛔ {mention} membalas setelah lebih dari {batas + 5} menit.\nSanksi sudah diberikan sebelumnya. Terima kasih.")

        if harian_durasi[user_id] > BATAS_HARIAN:
            bot.send_message(chat_id, f"⚠️ Total izin harian melebihi {BATAS_HARIAN} menit.\nSanksi: ${DENDA_MELEBIHI_BATAS}")
        return

    perintah = text.replace("/", "").split("@")[0]
    if perintah in IZIN_BATAS:
        if perintah in ["smoking", "smoke"]:
            if dilarang_smoke_now():
                bot.reply_to(message, "❌ Kamu tidak diizinkan /Smoke sekarang.\n\nDilarang mengajukan /Smoke di:\n• 08:00-08:20\n• 08:55-09:25\n• 10:30-11:00\n• 13:00-13:30\n• 14:30-14:45\n• 15:30-16:00\n• 17:00-17:30\n• 20:00-20:15\n• 20:30-21:00\n• 21:30-22:00\n• 22:30-23:00")
                return
            if chat_id in aktif_smoke:
                bot.reply_to(message, "❌ Sudah ada yang izin merokok. Silakan tunggu giliran.")
                return
            aktif_smoke[chat_id] = user_id

        elif perintah in ["smoke2", "smoking2", "smoke3", "smoking3", "smoke4", "smoking4"]:
            aktif_pimpinan.setdefault(chat_id, set())
            if len(aktif_pimpinan[chat_id]) >= MAX_PIMPINAN_IZIN:
                bot.reply_to(message, "❌ Jumlah maksimal pimpinan yang izin telah tercapai. Mohon tunggu.")
                return
            aktif_pimpinan[chat_id].add(user_id)
            bot.reply_to(message, "✅ Pimpinan, diizinkan.")
        else:
            bot.reply_to(message, f"✅ Izin {perintah.title()} dicatat. Balas pesan ini saat kembali.")

        izin_log[message.message_id] = {
            "user_id": user_id,
            "timestamp": now(),
            "jenis": perintah,
            "nama": nama,
            "username": username
        }
        batas = IZIN_BATAS[perintah]
        threading.Thread(target=reminder_and_sanksi, args=(chat_id, message.message_id, user_id, perintah, now(), batas), daemon=True).start()
        return

    count = peringatan_user.get(user_id, 0)
    if count == 0:
        bot.reply_to(message, "⚠️ Format izin salah. Gunakan perintah seperti:\n/Toilet\n/Bab\n/Smoke\n/Smoking")
        peringatan_user[user_id] = 1
    elif count == 1:
        bot.reply_to(message, f"❌ Izin ditolak. Anda melanggar dua kali.\nSanksi: ${DENDA_PERINGATAN}")
        peringatan_user[user_id] = 2

bot.infinity_polling(allowed_updates=["message", "edited_message"])
