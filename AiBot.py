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

SYSTEM_PROMPT = "你是一个有点拽、说话幽默的AI助手。回答要简短，不要超过100字。"

# ==========================================
# 🎭 障眼法：启动假网页，骗过 Render 防止休眠
# ==========================================
class WebServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_fake_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), WebServerHandler)
    server.serve_forever()

# ==========================================
# 🤖 机器人核心逻辑
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("我靠你开挂了吧 你怎么找到DJH的鸡器人了🥺🥺\n\n直接发文字和我聊天吧！也可以发图片让我看！")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        result = response.json()
        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            if len(ai_reply) > 4000:
                await update.message.reply_text(ai_reply[:4000])
                await update.message.reply_text(ai_reply[4000:])
            else:
                await update.message.reply_text(ai_reply)
        else:
            await update.message.reply_text("😵 脑子抽了，没想出答案。")
    except Exception as e:
        await update.message.reply_text(f"❌ 报错：{str(e)}")

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
                    {"type": "text", "text": "详细描述这张图片的内容，或者回答关于图片的问题。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            await update.message.reply_text(f"👁️ 我看到的是：\n{ai_reply}")
        else:
            error_msg = result.get("error", {}).get("message", str(result))
            await update.message.reply_text(f"❌ 图片识别失败：{error_msg}")
    except Exception as e:
        await update.message.reply_text(f"❌ 图片处理出错：{str(e)}")

if __name__ == '__main__':
    # 1. 启动假网页（给 Render 看）
    threading.Thread(target=run_fake_server, daemon=True).start()
    
    # 2. 启动真正的机器人
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, vision_chat))
    
    print("Render 专用版机器人已启动！")
    app.run_polling()
