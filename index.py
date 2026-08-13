import os
import tempfile
import requests
from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

# আপনার টেলিগ্রাম বট টোকেন
BOT_TOKEN = "8629377419:AAHzAP_4FIpz-xaANBuQNH3LkhkPAhNbziA"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------------------------------------------------------
# ১. বহুবাসিক মেসেজ (Bangla & English)
# ---------------------------------------------------------
STRINGS = {
    'bn': {
        'welcome': "👋 **হ্যালো {name}!**\n\nআমি আপনার **Universal Downloader Bot** 🤖\n\n👇 **আপনি কোন প্ল্যাটফর্মের ভিডিও ডাউনলোড করতে চান?**",
        'select_platform': "✅ **আপনি {platform} সিলেক্ট করেছেন!**\n\n📥 এখন আপনার **{platform}** ভিডিওর লিংকটি এখানে পেস্ট করে পাঠান:",
        'invalid_url': "⚠️ অনুগ্রহ করে একটি সঠিক ভিডিও লিংক (URL) পাঠান!\n\nবাটন আবার পেতে /start লিখুন।",
        'downloading': "⏳ ভিডিও প্রসেস ও ডাউনলোড করা হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।",
        'uploading': "📤 ফাইলটি টেলিগ্রামে আপলোড করা হচ্ছে...",
        'download_more': "🔄 অন্য ভিডিও ডাউনলোড করুন",
        'change_lang_btn': "🌐 ভাষা পরিবর্তন (Language)",
        'choose_lang': "🌐 আপনার পছন্দের ভাষা নির্বাচন করুন:",
        'lang_updated': "✅ ভাষা বাংলায় পরিবর্তন করা হয়েছে!",
        'file_too_large': "❌ **দুঃখিত!** ভিডিওটির ফাইল সাইজ ৫০MB-এর বেশি বা Vercel-এর ১০ সেকেণ্ডের লিমিট পার হয়ে গেছে।",
        'download_error': "❌ **ডাউনলোড সম্ভব হয়নি!** ভিডিও লিংকটি সঠিক কি না বা প্রাইভেট কি না চেক করুন।"
    },
    'en': {
        'welcome': "👋 **Hello {name}!**\n\nI am your **Universal Downloader Bot** 🤖\n\n👇 **Select the platform you want to download from:**",
        'select_platform': "✅ **You selected {platform}!**\n\n📥 Now paste and send your **{platform}** video link here:",
        'invalid_url': "⚠️ Please send a valid video URL!\n\nType /start to get the menu.",
        'downloading': "⏳ Processing & downloading video... Please wait a moment.",
        'uploading': "📤 Uploading file to Telegram...",
        'download_more': "🔄 Download Another Video",
        'change_lang_btn': "🌐 Change Language",
        'choose_lang': "🌐 Select your preferred language:",
        'lang_updated': "✅ Language set to English!",
        'file_too_large': "❌ **Sorry!** File size is larger than 50MB or operation timed out.",
        'download_error': "❌ **Download Failed!** Please check if the video link is valid or public."
    }
}

# ---------------------------------------------------------
# ২. টেলিগ্রাম এপিআই হেলপার ফাংশন
# ---------------------------------------------------------
def send_telegram_request(method, data=None, files=None):
    url = f"{TELEGRAM_API}/{method}"
    if files:
        return requests.post(url, data=data, files=files).json()
    return requests.post(url, json=data).json()

def get_main_keyboard(lang='bn'):
    return {
        "inline_keyboard": [
            [
                {"text": "🎵 TikTok", "callback_data": f"platform_TikTok_{lang}"},
                {"text": "📘 Facebook", "callback_data": f"platform_Facebook_{lang}"}
            ],
            [
                {"text": "▶️ YouTube", "callback_data": f"platform_YouTube_{lang}"},
                {"text": "📷 Instagram", "callback_data": f"platform_Instagram_{lang}"}
            ],
            [
                {"text": "🌐 Custom Link", "callback_data": f"platform_Custom_{lang}"}
            ],
            [
                {"text": STRINGS[lang]['change_lang_btn'], "callback_data": "open_lang_menu"}
            ]
        ]
    }

def get_lang_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🇧🇩 বাংলা (Bangla)", "callback_data": "setlang_bn"},
                {"text": "🇺🇸 English", "callback_data": "setlang_en"}
            ]
        ]
    }

# ---------------------------------------------------------
# ৩. yt-dlp ভিডিও ডাউনলোডার
# ---------------------------------------------------------
def download_video(video_url, chat_id):
    temp_dir = tempfile.gettempdir()
    out_tmpl = os.path.join(temp_dir, f"v_{chat_id}_%(id)s.%(ext)s")

    ydl_opts = {
        'format': 'best[filesize<=45M][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 45 * 1024 * 1024, # 45MB max limit for Vercel upload
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info)
        title = info.get('title', 'Video File')
        return file_path, title

# ---------------------------------------------------------
# ৪. Flask ওয়েবহুক রাউট
# ---------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "Bot Webhook Server is Online!"

    update = request.get_json()
    if not update:
        return jsonify({"status": "error"}), 400

    # ১. ইউজার মেসেজ হ্যান্ডলার
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        first_name = msg["from"].get("first_name", "User")

        if text == "/start":
            welcome_msg = STRINGS['bn']['welcome'].format(name=first_name)
            send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": welcome_msg,
                "reply_markup": get_main_keyboard('bn'),
                "parse_mode": "Markdown"
            })

        elif text.startswith("http://") or text.startswith("https://"):
            status_res = send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": STRINGS['bn']['downloading'],
                "parse_mode": "Markdown"
            })
            status_msg_id = status_res.get("result", {}).get("message_id")

            file_path = None
            try:
                file_path, title = download_video(text, chat_id)

                if file_path and os.path.exists(file_path):
                    send_telegram_request("editMessageText", {
                        "chat_id": chat_id,
                        "message_id": status_msg_id,
                        "text": STRINGS['bn']['uploading']
                    })

                    with open(file_path, 'rb') as video_file:
                        send_telegram_request("sendVideo", data={
                            "chat_id": chat_id,
                            "caption": f"✅ **{title[:60]}**\n\n🤖 *Downloaded via Universal Bot*",
                            "parse_mode": "Markdown",
                            "reply_markup": json_keyboard_reset('bn')
                        }, files={"video": video_file})

                    # স্ট্যাটাস মেসেজ ডিলিট
                    send_telegram_request("deleteMessage", {
                        "chat_id": chat_id,
                        "message_id": status_msg_id
                    })

            except Exception as e:
                err = str(e)
                error_txt = STRINGS['bn']['file_too_large'] if "filesize" in err else STRINGS['bn']['download_error']
                send_telegram_request("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": status_msg_id,
                    "text": error_txt,
                    "parse_mode": "Markdown"
                })

            finally:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass

    # ২. ইনলাইন বাটন হ্যান্ডলার (Callback Query)
    elif "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb.get("data", "")

        # অ্যানসার কলব্যাক
        send_telegram_request("answerCallbackQuery", {"callback_query_id": cb_id})

        if data == "open_lang_menu":
            send_telegram_request("editMessageText", {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": STRINGS['bn']['choose_lang'],
                "reply_markup": get_lang_keyboard(),
                "parse_mode": "Markdown"
            })

        elif data.startswith("setlang_"):
            lang = data.split("_")[1]
            first_name = cb["from"].get("first_name", "User")
            welcome_text = f"{STRINGS[lang]['lang_updated']}\n\n" + STRINGS[lang]['welcome'].format(name=first_name)

            send_telegram_request("editMessageText", {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": welcome_text,
                "reply_markup": get_main_keyboard(lang),
                "parse_mode": "Markdown"
            })

        elif data.startswith("platform_"):
            parts = data.split("_")
            platform = parts[1]
            lang = parts[2] if len(parts) > 2 else 'bn'

            msg_text = STRINGS[lang]['select_platform'].format(platform=platform)
            send_telegram_request("editMessageText", {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": msg_text,
                "parse_mode": "Markdown"
            })

        elif data.startswith("reset_menu_"):
            lang = data.split("_")[2] if len(data.split("_")) > 2 else 'bn'
            first_name = cb["from"].get("first_name", "User")
            welcome_text = STRINGS[lang]['welcome'].format(name=first_name)
            send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": welcome_text,
                "reply_markup": get_main_keyboard(lang),
                "parse_mode": "Markdown"
            })

    return jsonify({"status": "ok"}), 200

def json_keyboard_reset(lang='bn'):
    return {
        "inline_keyboard": [
            [{"text": STRINGS[lang]['download_more'], "callback_data": f"reset_menu_{lang}"}]
        ]
    }
    