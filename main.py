import os
import telebot

API_TOKEN = os.getenv("API_TOKEN")
print(f"API_TOKEN = {API_TOKEN}")  # 👈 debug print

bot = telebot.TeleBot(API_TOKEN)

# Aturan waktu maksimum (dalam menit)
IZIN_BATAS = {
    "izin toilet": 4,
    "izin bab": 15,
    "izin smoking": 10
}

# Menyimpan log izin sementara
izin_log = {}

def detect_izin(text):
    text = text.lower()
    for key in IZIN_BATAS:
        if key in text:
            return key
    return None

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.lower()

    # Jika ini izin baru
    jenis_izin = detect_izin(text)
    if jenis_izin:
        izin_log[message.message_id] = {
            "user_id": user_id,
            "timestamp": datetime.now(),
            "jenis": jenis_izin,
            "nama": message.from_user.first_name
        }
        bot.reply_to(message, f"{jenis_izin.title()} dicatat. Silakan kembali tepat waktu.")

    # Jika ini balasan ke pesan izin
    elif message.reply_to_message and message.reply_to_message.message_id in izin_log:
        izin_data = izin_log[message.reply_to_message.message_id]
        waktu_mulai = izin_data["timestamp"]
        jenis = izin_data["jenis"]
        batas = IZIN_BATAS[jenis]

        durasi = (datetime.now() - waktu_mulai).total_seconds() / 60  # dalam menit
        durasi = round(durasi, 2)
        nama = izin_data["nama"]

        if durasi <= batas:
            bot.reply_to(message, f"✅ {jenis.title()} oleh {nama} selesai dalam {durasi} menit. Tepat waktu.")
        else:
            bot.reply_to(message, f"⚠️ Terlambat kembali ({durasi} menit). Batas {batas} menit untuk {jenis.title()}. Sanksi: $20")

        del izin_log[message.reply_to_message.message_id]
