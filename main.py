from datetime import datetime
import os
import telebot
import threading
import time
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Google Sheets Setup
SHEET_ID = "1MmOTBBSTjaQNsewdzl_7T6PIBLBnEcVIinP0Utzjqoo"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open_by_key(SHEET_ID).sheet1

# Konfigurasi
IZIN_BATAS = {"toilet": 4, "bab": 16, "smoking": 10.5}
BATAS_HARIAN = 75
DENDA_MELEBIHI_BATAS = 100
DENDA_PERINGATAN = 10
jam_rekap = "00:00"
user_kena_denda = set()

# Fungsi Sheet
def catat_izin(user_id, nama, jenis):
    SHEET.append_row([
        str(user_id), nama, jenis,
        datetime.now().isoformat(), "", "", "aktif"
    ])

def selesaikan_izin(user_id):
    records = SHEET.get_all_records()
    for i, row in enumerate(records, start=2):
        if row["user_id"] == str(user_id) and row["status"] == "aktif":
            start = datetime.fromisoformat(row["waktu_mulai"])
            now_time = datetime.now()
            durasi = round((now_time - start).total_seconds() / 60, 2)
            SHEET.update(f"E{i}", now_time.isoformat())
            SHEET.update(f"F{i}", durasi)
            SHEET.update(f"G{i}", "selesai")
            return row["jenis"], durasi
    return None, None

def hitung_total_harian(user_id):
    records = SHEET.get_all_records()
    total = 0
    hari_ini = datetime.now().date()
    for row in records:
        if row["user_id"] == str(user_id) and row["status"] == "selesai":
            tgl = datetime.fromisoformat(row["waktu_mulai"]).date()
            if tgl == hari_ini:
                total += float(row["durasi"] or 0)
    return round(total, 2)

def kirim_rekap():
    records = SHEET.get_all_records()
    grup_user = {}
    for row in records:
        if row["status"] != "selesai":
            continue
        user_id = row["user_id"]
        nama = row["nama"]
        durasi = float(row["durasi"] or 0)
        waktu = datetime.fromisoformat(row["waktu_mulai"])
        if waktu.date() != datetime.now().date():
            continue
        grup_user.setdefault(user_id, {"nama": nama, "durasi": 0})
        grup_user[user_id]["durasi"] += durasi

    if not grup_user:
        return

    pesan = "\U0001F4CA Rekap Harian Izin:\n"
    for user_id, info in grup_user.items():
        pesan += f"• {info['nama']}: {round(info['durasi'], 2)} menit\n"
        if info['durasi'] > BATAS_HARIAN:
            pesan += f"  ⚠️ Melebihi batas. Sanksi: ${DENDA_MELEBIHI_BATAS}\n"

    try:
        bot.send_message(-1001234567890, pesan)  # Ganti dengan ID grup Telegram kamu
    except Exception as e:
        print("Gagal kirim rekap:", e)

def scheduler():
    while True:
        if datetime.now().strftime("%H:%M") == jam_rekap:
            kirim_rekap()
        time.sleep(60)

threading.Thread(target=scheduler, daemon=True).start()

@bot.message_handler(func=lambda m: True)
def handle(message):
    user = message.from_user
    user_id = user.id
    chat_id = message.chat.id
    text = message.text.lower().strip()

    if message.reply_to_message:
        jenis, durasi = selesaikan_izin(user_id)
        if not jenis:
            bot.reply_to(message, "⛔ Izin tidak ditemukan atau sudah selesai.")
            return

        batas = IZIN_BATAS[jenis]
        total = hitung_total_harian(user_id)

        if durasi <= batas:
            bot.reply_to(message, f"✅ {jenis.title()} selesai dalam {durasi} menit. Tepat waktu.")
        else:
            bot.reply_to(message, f"⚠️ Terlambat ({durasi} menit). Batas {batas} menit.\nSanksi: ${DENDA_PERINGATAN}")

        if total > BATAS_HARIAN and user_id not in user_kena_denda:
            bot.send_message(chat_id, f"⚠️ Total izin harian kamu {total} menit.\nSanksi: ${DENDA_MELEBIHI_BATAS}")
            user_kena_denda.add(user_id)

    elif text.startswith("/izin "):
        jenis = text.replace("/izin ", "")
        if jenis not in IZIN_BATAS:
            bot.reply_to(message, "❌ Jenis izin tidak valid.")
            return
        catat_izin(user_id, user.first_name, jenis)
        bot.reply_to(message, f"✅ Izin {jenis.title()} dicatat. Balas pesan ini saat kembali.")

    else:
        bot.reply_to(message, "⚠️ Format salah. Gunakan perintah seperti: /izin toilet")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
