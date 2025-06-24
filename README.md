# bot-izin-v2

Bot Telegram untuk mencatat izin (toilet, bab, smoking) dan mengevaluasi durasi kembali. Jika melebihi batas waktu, bot memberi peringatan dan sanksi.

## Jenis Izin dan Batas Waktu
- Izin Toilet: 4 menit
- Izin Bab: 15 menit
- Izin Smoking: 10 menit

## Cara Kerja
1. Kirim pesan seperti "Izin Toilet".
2. Bot mencatat waktu mulai.
3. Saat kembali, balas pesannya dengan "1" atau apapun.
4. Bot menghitung durasi dan memberikan evaluasi.

## Deploy
- Gunakan Railway atau server Python.
- Tambahkan API_TOKEN ke environment variable.
