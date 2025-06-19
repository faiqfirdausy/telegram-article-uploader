# telegram-article-uploader
Telegram bot to create framed news images, collages, and auto-post to Facebook, Twitter, and Joomla CMS.
A Telegram bot for automating the creation and cross-platform publishing of news articles.

This bot allows users to:
1. Upload an image with a title → framed automatically
2. Send 4 images → auto-generate a 2x2 collage
3. Submit article narration → content is published to **Facebook**, **Twitter**, and **Joomla CMS**

---

## 🚀 Features

- 🖼️ Auto-add frame and title to uploaded image
- 🧩 Create a 2x2 collage with predefined header
- 📤 Post article to:
  - Facebook Page
  - Twitter (with media upload)
  - Joomla CMS (intro text + images)
- 💬 Telegram chat-based interface
- 🧠 Automatic formatting of hashtags & caption

---

## 📸 Example Workflow

1. **Send one photo + caption**  
   → Bot returns framed image  
2. **Send four photos**  
   → Bot builds collage  
3. **Send news narration**  
   → Bot publishes full article to all platforms  
   → Bot replies with links to Facebook, Twitter, and Joomla post

---

## 🔧 Tech Stack

- **Python 3.x**
- `python-telegram-bot`
- `Pillow` for image processing
- `Tweepy` for Twitter API
- `requests` for Facebook & Joomla integration

---

## 🛠️ How to Run

1. Clone the repository:
     ```bash
     git clone https://github.com/yourusername/telegram-article-uploader.git
     cd telegram-article-uploader

2. Install Dependencies:
     ```bash
     pip install -r requirements.txt

3. Configure your tokens:

      Telegram: BOT_TOKEN
      
      Twitter: TWITTER_API_KEY, TWITTER_ACCESS_TOKEN, etc.
      
      Facebook: USER_ACCESS_TOKEN, FACEBOOK_PAGE_ID
      
      Joomla: JOOMLA_API_TOKEN

4. Run the bot:
      ```bash
      python bot.py
