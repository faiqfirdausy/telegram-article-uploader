
import os
import io
import base64
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tweepy

# === Konfigurasi Token dan API ===
BOT_TOKEN = ""
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_SECRET = ""
JOOMLA_API_TOKEN = ""
USER_ACCESS_TOKEN = ""
FACEBOOK_PAGE_ID = ""

# === Variabel Global ===
user_kolase_progress = {}
user_title = {}
user_news_narasi = {}

# === Fungsi Utilitas ===
def post_to_facebook_with_images(user_access_token, page_id, image_paths, message):
    version = 'v20.0'
    token_url = f'https://graph.facebook.com/{version}/{page_id}?fields=access_token&access_token={user_access_token}'
    try:
        token_res = requests.get(token_url)
        token_res.raise_for_status()
        page_access_token = token_res.json()['access_token']
    except requests.exceptions.RequestException as e:
        raise Exception(f"Gagal mengambil Page Access Token: {e}")

    media_ids = []
    for path in image_paths:
        try:
            with open(path, 'rb') as image_file:
                upload_url = f'https://graph.facebook.com/{version}/{page_id}/photos'
                files = {'source': image_file}
                payload = {
                    'published': 'false',
                    'access_token': page_access_token
                }
                upload_res = requests.post(upload_url, files=files, data=payload)
                upload_res.raise_for_status()
                img_id = upload_res.json().get('id')
                media_ids.append({'media_fbid': img_id})
        except Exception as e:
            raise Exception(f"Gagal upload gambar {path}: {e}")

    feed_url = f'https://graph.facebook.com/{version}/{page_id}/feed'
    post_payload = {
        'message': message,
        'access_token': page_access_token,
        'attached_media': media_ids
    }
    post_res = requests.post(feed_url, json=post_payload)
    post_res.raise_for_status()

    post_id_full = post_res.json().get('id')
    if '_' in post_id_full:
        _, post_id = post_id_full.split('_', 1)
        fb_link = f"https://www.facebook.com/{page_id}/posts/{post_id}"
    else:
        fb_link = f"https://www.facebook.com/{post_id_full}"
    return fb_link



def crop_center_ratio(image, target_ratio=3/2):
    width, height = image.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Terlalu lebar, potong sisi kiri dan kanan
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        top, bottom = 0, height
    else:
        # Terlalu tinggi, potong atas dan bawah
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        left, right = 0, width

    return image.crop((left, top, right, bottom))


def wrap_text_by_pixel(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            test_line = f"{line} {word}".strip()
            if draw.textlength(test_line, font=font) <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
    line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    return "\n".join(lines), len(lines), line_height

def draw_autofit_text_bottom_adjusted(image, text, font_path, margin_bottom=0.1, text_color=(255,255,255), start_font_size=100, min_font_size=20):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    margin_bottom_px = int(height * margin_bottom)
    aspect = width / height
    max_width = int(width * (0.75 if aspect >= 1.7 else 0.6 if aspect >= 1.3 else 0.8))
    margin_x = int(width * 0.07) if aspect >= 1.3 else (width - max_width) // 2

    for size in range(start_font_size, min_font_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        wrapped, lines, lh = wrap_text_by_pixel(draw, text, font, max_width)
        total_h = lines * lh
        if total_h <= height * 0.2:
            y = height - margin_bottom_px - total_h
            draw.text((margin_x, y), wrapped, font=font, fill=text_color)
            return image

    font = ImageFont.truetype(font_path, min_font_size)
    wrapped, lines, lh = wrap_text_by_pixel(draw, text, font, max_width)
    total_h = lines * lh
    y = height - margin_bottom_px - total_h
    draw.text((margin_x, y), wrapped, font=font, fill=text_color)
    return image

def save_kolase_image(user_id, image):
    folder = f"temp/{user_id}"
    os.makedirs(folder, exist_ok=True)
    idx = len([f for f in os.listdir(folder) if f.endswith('.jpg') and f != 'framed.jpg']) + 1
    path = os.path.join(folder, f"{idx}.jpg")
    image.save(path)
    return idx

def clear_user_folder(user_id):
    folder = f"temp/{user_id}"
    if os.path.exists(folder):
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
    else:
        os.makedirs(folder)

def buat_kolase(user_id):
    folder = f"temp/{user_id}"
    output_path = os.path.join(folder, "kolase_output.jpg")
    imgs = []
    for i in range(1,5):
        p = os.path.join(folder, f"{i}.jpg")
        if not os.path.exists(p): return None
        imgs.append(Image.open(p))

    ratios = [im.width/im.height for im in imgs]
    dom = max(set(ratios), key=ratios.count)
    if abs(dom - 16/9) < 0.1:
        overlay = "header_169.png"; fw, fh = 1023,576
    elif abs(dom - 3/2) < 0.1:
        overlay = "header_32.png"; fw, fh = 960,640
    elif abs(dom - 4/3) < 0.1:
        overlay = "header_43.png"; fw, fh = 912,684
    else:
        overlay = "header.png"; fw, fh = 1023,682

    imgs = [im.resize((fw,fh), Image.Resampling.LANCZOS) for im in imgs]
    collage = Image.new("RGB", (fw*2, fh*2), "white")
    coords = [(0,0),(fw,0),(0,fh),(fw,fh)]
    for im, c in zip(imgs,coords): collage.paste(im, c)
    ov = Image.open(overlay).convert("RGBA").resize(collage.size)
    out = collage.convert("RGBA"); out.alpha_composite(ov); out = out.convert("RGB")
    out.save(output_path)
    return output_path

def upload_image_to_joomla(image_path, api_token):
    url = "https://yourjoomlapage.com/api/index.php/v1/media/files"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"foto_{timestamp}.jpg"
    upload_path = f"local-images:/gambarpost2/{filename}"
    image_url = f"/images/gambarpost/{filename}"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    payload = {
        "path": upload_path,
        "content": encoded,
        "overwrite": True
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code in [200, 201]: return image_url
    else: raise Exception(f"Gagal upload gambar: {response.json()}")

def post_article_to_joomla(title, intro_html, api_token):
    url = "https://yourjoomlapage.com/api/index.php/v1/content/articles"
    alias = title.lower().replace(" ", "-") + "-" + datetime.now().strftime("%H%M%S")
    payload = {"title": title, "alias": alias, "catid": 19, "state": 1, "language": "*", "introtext": intro_html}
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        alias = response.json()["data"]["attributes"]["alias"]
        return f"https://yourjoomlapage.com/yourcategory/{alias}"
    else: raise Exception(f"Gagal buat artikel: {response.text}")

# === Setup Twitter ===
auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
twitter_api = tweepy.API(auth)
twitter_client = tweepy.Client(
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirim satu foto dengan caption judul untuk diberi frame.")
    uid = update.effective_user.id
    clear_user_folder(uid)
    user_kolase_progress.pop(uid, None)
    user_news_narasi.pop(uid, None)
    user_title.pop(uid, None)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    caption = update.message.caption

    if caption and uid not in user_title:
        title = caption.replace(";", "\n")
        user_title[uid] = title
        clear_user_folder(uid)

        photo = await update.message.photo[-1].get_file()
        data = await photo.download_as_bytearray()
        img = Image.open(io.BytesIO(data))
        img = crop_center_ratio(img)  # Crop sebelum resize & frame
        aspect = img.width / img.height
        frm = "bingkai_169.png" if aspect >= 1.7 else ("bingkai_32.png" if aspect >= 1.3 else "bingkai.png")
        frame = Image.open(frm)
        img = img.resize(frame.size)
        img.paste(frame, (0,0), frame.convert("RGBA"))
        img = draw_autofit_text_bottom_adjusted(img, title, font_path="font/Barlow-Medium.ttf")

        folder = f"temp/{uid}"
        framed_path = os.path.join(folder, "framed.jpg")
        img.save(framed_path)

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        await update.message.reply_photo(photo=buf, caption="Gambar dengan frame selesai.")
        await update.message.reply_text("Sekarang kirim 4 gambar untuk kolase.")
        user_kolase_progress[uid] = 0
        return

    if uid in user_title and user_kolase_progress.get(uid, 0) < 4:
        photo = await update.message.photo[-1].get_file()
        data = await photo.download_as_bytearray()
        img = Image.open(io.BytesIO(data))
        img = crop_center_ratio(img)  # Crop sebelum resize & frame

        idx = save_kolase_image(uid, img)
        user_kolase_progress[uid] = idx
        await update.message.reply_text(f"Gambar ke-{idx} untuk kolase diterima.")
        if idx == 4:
            await update.message.reply_text("Membuat kolase, tunggu...")
            kolase_path = buat_kolase(uid)
            if kolase_path:
                await update.message.reply_photo(photo=open(kolase_path, 'rb'), caption="Berikut hasil kolasenya.")
                await update.message.reply_text("Sekarang kirim narasi berita untuk tweet dan artikel.")
            else:
                await update.message.reply_text("Gagal membuat kolase.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if user_kolase_progress.get(uid, 0) == 4 and uid in user_title:
        user_news_narasi[uid] = text
        folder = f"temp/{uid}"
        framed_path = os.path.join(folder, "framed.jpg")
        kolase_path = os.path.join(folder, "kolase_output.jpg")
        try:
            # Define the hashtags
            hashtags = (
                "#KementerianHukum\n"
                "#LayananHukumMakinMudah\n"
                "#AksiNyataSejahtera\n"
                "#KerjaTerlaksana"
            )


            text_with_hashtags = f"{text}\n\n{hashtags}"

            # Twitter
            m1 = twitter_api.media_upload(filename=framed_path)
            m2 = twitter_api.media_upload(filename=kolase_path)
            tweet = twitter_client.create_tweet(text=text_with_hashtags, media_ids=[m1.media_id, m2.media_id])
            twitter_link = f"https://twitter.com/user/status/{tweet.data['id']}"

            # Facebook menggunakan requests
            fb_link = post_to_facebook_with_images(
                USER_ACCESS_TOKEN,
                FACEBOOK_PAGE_ID,
                [framed_path, kolase_path],
                text_with_hashtags
            )
            # Joomla
            img1_url = upload_image_to_joomla(framed_path, JOOMLA_API_TOKEN)
            img2_url = upload_image_to_joomla(kolase_path, JOOMLA_API_TOKEN)
            title = user_title[uid].split("\n")[0]
            narasi_html = text_with_hashtags.replace("\n", "<br>")
            content_html = f"<p><img src='{img1_url}'></p><p>{narasi_html}</p><p><img src='{img2_url}'></p>"
            joomla_link = post_article_to_joomla(title, content_html, JOOMLA_API_TOKEN)
            judul = user_title[uid].split("\n")[0]
            # --- MODIFIED PART TO GET THE FIRST NON-EMPTY PARAGRAPH ---
            lines = [line.strip() for line in user_news_narasi[uid].split('\n')]
            paragraf_pertama = next((line for line in lines[1:] if line), "")
            # --- END OF MODIFIED PART ---

            formatted_message = (
                f"_*{judul}*_\n\n"
                f"{paragraf_pertama}\n\n"
                f"_*selengkapnya klik tautan dibawah ini*_\n\n"
                f"_*LINK FACEBOOK*_\n"
                f"*{fb_link}*\n\n"
                f"_*LINK TWITTER*_\n"
                f"*{twitter_link}*\n\n"
                f"_*LINK WEBSITE*_\n"
                f"*{joomla_link}*"
            )
            await update.message.reply_text(formatted_message, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal unggah: {e}")
        clear_user_folder(uid)
        user_kolase_progress.pop(uid, None)
        user_title.pop(uid, None)
        user_news_narasi.pop(uid, None)
    else:
        await update.message.reply_text("Perintah tidak dikenali. Gunakan /start untuk memulai lagi.")

# === Main ===
if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot berjalan...")
    app.run_polling()
