#!/usr/bin/env python3
"""
Telegram Bot untuk Monitoring Drone 1 (GCS) - Versi Integrasi Penuh
==================================================================
Mendukung perintah:
- /start  : Status otorisasi dan daftar bantuan perintah
- /status : Ringkasan konektivitas dan kesehatan sinyal Drone 1
- /gps    : Lokasi GPS terkini, Google Maps link, dan usia data
- /photo  : Snapshot kamera Drone 1 terkini + caption telemetri GPS
- Background Alert: Notifikasi otomatis saat sinyal Drone 1 terputus / pulih
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ============================================================
# KONFIGURASI FILE & PATH
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "bot_config.json")
LATEST_GPS_FILE = os.path.join(BASE_DIR, "receiver", "latest_gps.json")
LATEST_FRAME_FILE = os.path.join(BASE_DIR, "receiver", "latest_frame.jpg")
STALE_THRESHOLD_SECONDS = 5.0  # Data > 5 detik dianggap basi

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Drone1TelegramBot")

def load_config():
    """Memuat konfigurasi token dan whitelist chat_id."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed_ids = []

    env_ids = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
    if env_ids:
        try:
            allowed_ids = [int(x.strip()) for x in env_ids.split(",") if x.strip()]
        except ValueError:
            logger.warning("Format ALLOWED_CHAT_IDS di environment tidak valid.")

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                file_token = cfg.get("bot_token", "").strip()
                if file_token and file_token != "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE":
                    bot_token = file_token
                file_ids = cfg.get("allowed_chat_ids", [])
                if isinstance(file_ids, list):
                    allowed_ids.extend([int(x) for x in file_ids if isinstance(x, (int, str)) and str(x).isdigit()])
        except Exception as e:
            logger.error(f"Gagal membaca {CONFIG_FILE}: {e}")

    allowed_ids = list(set(allowed_ids))
    return bot_token, allowed_ids

def get_current_gps_status():
    """Membaca data GPS terakhir dari file cache."""
    if not os.path.exists(LATEST_GPS_FILE):
        return None, "NO_DATA"

    try:
        with open(LATEST_GPS_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        return None, f"READ_ERROR: {e}"

    local_received_at = data.get("local_received_at", 0)
    age = time.time() - local_received_at

    is_stale = data.get("is_stale", False) or (age > STALE_THRESHOLD_SECONDS)
    status_str = "STALE" if is_stale else "FRESH"

    return {
        "device": data.get("device", "unknown"),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "accuracy_m": data.get("accuracy_m"),
        "device_timestamp": data.get("device_timestamp"),
        "local_received_at": local_received_at,
        "age_seconds": max(0.0, age),
        "sender_ip": data.get("sender_ip", "N/A"),
        "sender_port": data.get("sender_port", "N/A"),
        "is_stale": is_stale
    }, status_str

def is_authorized(user_id: int, allowed_ids: list) -> bool:
    if not allowed_ids:
        return False
    return user_id in allowed_ids

# ============================================================
# TELEGRAM HANDLERS
# ============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    allowed_ids = context.bot_data.get("allowed_ids", [])

    if not is_authorized(user.id, allowed_ids):
        logger.warning(f"Akses tidak sah dari User ID {user.id}")
        await update.message.reply_text(
            f"⛔ *Akses Ditolak*\nID Telegram Anda (`{user.id}`) tidak terdaftar dalam whitelist Drone 1 GCS.",
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        f"👋 Halo, *{user.first_name}*!\n"
        f"Selamat datang di sistem monitoring *Drone 1 (GCS)*.\n\n"
        f"📋 *Perintah yang tersedia:*\n"
        f"🔹 `/status` - Cek konektivitas dan kesehatan sinyal Drone 1\n"
        f"🔹 `/gps` - Ambil koordinat lokasi terkini & link Google Maps\n"
        f"🔹 `/photo` - Ambil foto snapshot kamera Drone 1 terkini\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    allowed_ids = context.bot_data.get("allowed_ids", [])

    if not is_authorized(user.id, allowed_ids):
        await update.message.reply_text("⛔ *Akses Ditolak*", parse_mode="Markdown")
        return

    gps_info, status = get_current_gps_status()

    if status == "NO_DATA":
        msg = (
            "🛰️ *STATUS SISTEM DRONE 1*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 *Status Koneksi:* OFFLINE / BELUM ADA DATA\n"
            "Receiver GPS belum menerima paket apa pun dari pengirim."
        )
    elif status.startswith("READ_ERROR"):
        msg = f"⚠️ *Error pembacaan cache GPS:* {status}"
    else:
        if gps_info["is_stale"]:
            stat_icon = "⚠️ *DISCONNECTED / DATA BASI*"
            note = f"⚠️ _Sinyal terputus atau tidak ada update selama {gps_info['age_seconds']:.1f} detik._"
        else:
            stat_icon = "🟢 *ONLINE (REALTIME)*"
            note = f"✅ _Data segar diterima {gps_info['age_seconds']:.1f} detik lalu._"

        acc_str = f"{gps_info['accuracy_m']:.1f} m" if gps_info['accuracy_m'] is not None else "N/A"
        waktu_lokal = time.strftime('%H:%M:%S', time.localtime(gps_info['local_received_at']))

        msg = (
            "🛰️ *STATUS SISTEM DRONE 1*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 *Kondisi:* {stat_icon}\n"
            f"📱 *Device:* `{gps_info['device']}`\n"
            f"🌐 *IP Sender:* `{gps_info['sender_ip']}:{gps_info['sender_port']}`\n"
            f"🎯 *Akurasi Sensor:* `{acc_str}`\n"
            f"⏱️ *Update Terakhir:* `{waktu_lokal}`\n\n"
            f"{note}"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    allowed_ids = context.bot_data.get("allowed_ids", [])

    if not is_authorized(user.id, allowed_ids):
        await update.message.reply_text("⛔ *Akses Ditolak*", parse_mode="Markdown")
        return

    gps_info, status = get_current_gps_status()

    if status == "NO_DATA":
        await update.message.reply_text(
            "📍 *Lokasi GPS Drone 1*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ *Belum ada data lokasi.* Receiver GCS belum menerima data GPS dari HP.",
            parse_mode="Markdown"
        )
        return

    if status.startswith("READ_ERROR"):
        await update.message.reply_text(f"⚠️ Gagal membaca data GPS: {status}")
        return

    lat = gps_info["lat"]
    lon = gps_info["lon"]
    acc_str = f"{gps_info['accuracy_m']:.1f} m" if gps_info['accuracy_m'] is not None else "N/A"
    waktu_lokal = time.strftime('%H:%M:%S', time.localtime(gps_info['local_received_at']))
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    if gps_info["is_stale"]:
        kondisi_tag = f"⚠️ *DATA BASI* (Terakhir update {gps_info['age_seconds']:.1f}s lalu)"
    else:
        kondisi_tag = f"🟢 *LOKASI TERKINI (SEGAR)* (Update {gps_info['age_seconds']:.1f}s lalu)"

    msg = (
        "📍 *LOKASI GPS DRONE 1*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {kondisi_tag}\n"
        f"📱 Device: `{gps_info['device']}`\n"
        f"🌐 Latitude: `{lat:.6f}`\n"
        f"🌐 Longitude: `{lon:.6f}`\n"
        f"🎯 Akurasi: `{acc_str}`\n"
        f"⏱️ Diterima GCS: `{waktu_lokal}`\n\n"
        f"🗺️ [Buka di Google Maps]({maps_link})"
    )

    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=False)

async def cmd_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengambil snapshot kamera Drone 1 terkini dan mengirimkannya ke chat."""
    user = update.effective_user
    allowed_ids = context.bot_data.get("allowed_ids", [])

    if not is_authorized(user.id, allowed_ids):
        await update.message.reply_text("⛔ *Akses Ditolak*", parse_mode="Markdown")
        return

    if not os.path.exists(LATEST_FRAME_FILE):
        await update.message.reply_text(
            "❌ *Belum ada foto/video dari Drone 1.*\n"
            "Pastikan receiver video GCS (`udp_video_receiver.py`) sedang aktif dan menerima stream kamera.",
            parse_mode="Markdown"
        )
        return

    file_age = time.time() - os.path.getmtime(LATEST_FRAME_FILE)
    gps_info, status = get_current_gps_status()

    stat_tag = "🟢 *STREAM AKTIF*" if file_age <= 3.0 else f"⚠️ *STREAM TERHENTI* ({file_age:.1f}s lalu)"

    caption_lines = [
        "📸 *SNAPSHOT KAMERA DRONE 1*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📡 Video Status: {stat_tag}"
    ]

    if gps_info and "lat" in gps_info and "lon" in gps_info:
        lat = gps_info["lat"]
        lon = gps_info["lon"]
        acc = f"{gps_info['accuracy_m']:.1f}m" if gps_info['accuracy_m'] is not None else "N/A"
        gps_tag = "🟢 Segar" if not gps_info["is_stale"] else "⚠️ Basi"
        caption_lines.append(f"📍 GPS ({gps_tag}): `{lat:.6f}, {lon:.6f}` (±{acc})")
        caption_lines.append(f"🗺️ [Google Maps](https://www.google.com/maps?q={lat},{lon})")

    caption_lines.append(f"⏱️ Waktu Ambil: `{time.strftime('%H:%M:%S')}`")
    caption = "\n".join(caption_lines)

    try:
        with open(LATEST_FRAME_FILE, "rb") as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=caption,
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Gagal mengirim foto: {e}")

# ============================================================
# BACKGROUND ALERT MONITOR (Notifikasi Terputus & Pulih)
# ============================================================
async def background_monitor_loop(app):
    """
    Task loop berkala yang memonitor status drone setiap 5 detik.
    Mengirim peringatan otomatis saat sinyal putus (dengan cooldown 60 detik)
    dan notifikasi pemulihan saat sinyal kembali normal.
    """
    last_state = "UNKNOWN"
    last_alert_time = 0.0

    while True:
        try:
            await asyncio.sleep(5)
            gps_info, status = get_current_gps_status()
            allowed_ids = app.bot_data.get("allowed_ids", [])
            now = time.time()

            current_state = "ONLINE" if (status == "FRESH") else "DISCONNECTED"

            # 1. Transisi: Online -> Disconnected
            if last_state == "ONLINE" and current_state == "DISCONNECTED":
                if (now - last_alert_time) > 60.0:  # Cooldown 60 detik
                    last_alert_time = now
                    last_state = "DISCONNECTED"

                    alert_msg = (
                        "🚨 *[PERINGATAN GCS] SINYAL DRONE 1 TERPUTUS!*\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "⚠️ Data telemetri GPS tidak diperbarui lebih dari 5 detik.\n"
                    )
                    if gps_info and "lat" in gps_info and "lon" in gps_info:
                        alert_msg += f"📍 *Posisi Terakhir:* `{gps_info['lat']:.6f}, {gps_info['lon']:.6f}`\n"
                        alert_msg += f"🗺️ [Buka di Google Maps](https://www.google.com/maps?q={gps_info['lat']},{gps_info['lon']})\n"

                    for cid in allowed_ids:
                        try:
                            await app.bot.send_message(chat_id=cid, text=alert_msg, parse_mode="Markdown")
                        except Exception:
                            pass

            # 2. Transisi: Disconnected -> Online (Pulih)
            elif last_state == "DISCONNECTED" and current_state == "ONLINE":
                last_state = "ONLINE"
                recovery_msg = (
                    "🟢 *[INFO GCS] SINYAL DRONE 1 PULIH KEMBALI!*\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ Koneksi telemetri GPS telah kembali realtime."
                )
                for cid in allowed_ids:
                    try:
                        await app.bot.send_message(chat_id=cid, text=recovery_msg, parse_mode="Markdown")
                    except Exception:
                        pass

            elif last_state == "UNKNOWN":
                last_state = current_state

        except Exception as e:
            logger.error(f"Error pada background monitor: {e}")

# ============================================================
# MAIN APPLICATION
# ============================================================
async def post_init(application):
    """Inisialisasi background task otomatis saat bot start."""
    asyncio.create_task(background_monitor_loop(application))

def main():
    bot_token, allowed_ids = load_config()

    if not bot_token or bot_token == "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print(" [!] ERROR: Token Bot Telegram Belum Dikonfigurasi!")
        print("=" * 60)
        print(f"Silakan isi token Anda ke dalam file:\n  {CONFIG_FILE}")
        return

    if not allowed_ids:
        print("\n" + "=" * 60)
        print(" [!] PERINGATAN: 'allowed_chat_ids' masih kosong!")
        print(f"Masukkan ID Telegram Anda ke dalam {CONFIG_FILE}")
        print("=" * 60 + "\n")
        return

    print("==================================================")
    print("      TELEGRAM MONITORING BOT (DRONE 1 GCS)       ")
    print("==================================================")
    print(f"[*] Whitelist Chat ID diizinkan : {allowed_ids}")
    print(f"[*] Snapshot Frame dibaca dari  : {LATEST_FRAME_FILE}")
    print("[*] Perintah aktif: /start, /status, /gps, /photo")
    print("[*] Background Alert monitor aktif (cooldown 60s).")
    print("[*] Bot siap melayani. Tekan CTRL+C untuk berhenti.\n")

    app = ApplicationBuilder().token(bot_token).post_init(post_init).build()

    app.bot_data["allowed_ids"] = allowed_ids

    # Registrasi handler
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("gps", cmd_gps))
    app.add_handler(CommandHandler("photo", cmd_photo))

    app.run_polling()

if __name__ == "__main__":
    main()
