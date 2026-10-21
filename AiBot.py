from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import base64
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# 👇 你的 Token 和 智谱 Key 👇
TG_TOKEN = "8860844332:AAGtIhKf_rWHOePaI7_jZrTqKN4qM7SYn4U"
ZHIPU_KEY = "9c9efbbe8dd143ca9a1e6f2a189373cd.gtUPOWwwgKXzyc7C"

SYSTEM_PROMPT = "你是一个名叫DuNren的超级AI助手。你幽默、聪明、有点拽，精通各种网络热梗。回答要详细且有趣，字数不超过200字。"
user_histories = {}

# ==========================================
# 🎭 假网页：防止 Render 休眠
# ==========================================
class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
def run_fake_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), WebServerHandler).serve_forever()

# ==========================================
# 🔍 专属复读机：搜索功能 (指令改为了 /search)
# ==========================================
async def search_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("用法：`/search 关键词`\n比如：`/search 软件`", parse_mode='Markdown')
    
    keyword = " ".join(context.args)
    
    # 第一步：先发那个搞笑的固定开头
    await update.message.reply_text(f"/search {keyword}是搜索频道哦嘿嘿 👇")
    
    # 第二步：生成搜索链接发给他
    search_url = f"https://t.me/s/{requests.utils.quote(keyword)}"
    reply_text = (
        f"🔍 **关于【{keyword}】的搜索结果：**\n\n"
        f"👉 [点击这里直接查看搜索结果]({search_url})\n"
    )
    await update.message.reply_text(reply_text, parse_mode='Markdown', disable_web_page_preview=True)

# ==========================================
# 🧠 智能 AI 聊天
# ==========================================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[user_id].append({"role": "user", "content": user_text})
    
    if len(user_histories[user_id]) > 16:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-15:]

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"}
    data = {"model": "glm-4-flash", "messages": user_histories[user_id]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        result = response.json()
        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            user_histories[user_id].append({"role": "assistant", "content": ai_reply})
            
            if len(ai_reply) > 4000:
                await update.message.reply_text(ai_reply[:4000])
                await update.message.reply_text(ai_reply[4000:])
            else:
                await update.message.reply_text(ai_reply)
        else:
            await update.message.reply_text("😵 AI 暂时短路。")
    except Exception as e:
        await update.message.reply_text(f"❌ 报错：{str(e)}")

# ==========================================
# 👁️ 图片识别
# ==========================================
async def vision_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "glm-4v-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "详细描述这张图片的内容。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        if "choices" in result:
            await update.message.reply_text(f"👁️ 我看到的是：\n{result['choices'][0]['message']['content']}")
        else:
            await update.message.reply_text("❌ 图片识别失败。")
    except Exception as e:
        await update.message.reply_text(f"❌ 处理出错：{str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **超级 AI 已上线**\n\n✅ 聊天记忆功能\n✅ 发送 `/search 关键词` 触发特殊搜索\n✅ 发图片让我看图", parse_mode='Markdown')

if __name__ == '__main__':
    threading.Thread(target=run_fake_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # 这里改成了纯英文 search
    app.add_handler(CommandHandler("search", search_channel)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, vision_chat))
    
    print("强化版 AI 已启动！")
    app.run_polling()
