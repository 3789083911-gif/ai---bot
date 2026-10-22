import requests
import base64
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 👇 你的 Token 和 智谱 Key 👇
TG_TOKEN = "8860844332:AAGtIhKf_rWHOePaI7_jZrTqKN4qM7SYn4U"
ZHIPU_KEY = "9c9efbbe8dd143ca9a1e6f2a189373cd.gtUPOWwwgKXzyc7C"

# 🧠 AI 核心设定
SYSTEM_PROMPT = (
    "你是 DuNren，一个由顶级极客打造的最强全能 AI。你精通代码、逆向、底层逻辑和全网检索。"
    "**【思维与行事准则】**：\n"
    "1. 直接给出最硬核、最底层的解决方案，绝不使用“作为AI...”、“建议您...”等废话。\n"
    "2. 遇到代码，先分析逻辑，再给出可运行代码。遇到需要最新资料的问题，调用 `web_search` 巡查。\n"
    "**【强制输出格式】**：\n"
    "先用 `[思考]：` 开头，写出你的推演逻辑。\n"
    "再用 `[结论]：` 开头，给出最终的硬核结果（附上代码或参考链接）。"
)

user_histories = {}

async def process_ai_response(update: Update, user_id: int, prompt_text: str, image_base64: str = None):
    start_time = time.time()
    # 这里改成了你要求的文案
    msg = await update.message.reply_text("🧠 DuNren 正在思考...\n\n🔄 状态：知识检索 ➡️ 逻辑推演 ➡️ 输出结论")
    
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if image_base64:
        content = [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        user_msg = {"role": "user", "content": content}
        model_to_use = "glm-4v-plus" 
    else:
        user_msg = {"role": "user", "content": prompt_text}
        model_to_use = "glm-4-plus" 

    user_histories[user_id].append(user_msg)
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-19:]

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"}
    
    data = {
        "model": model_to_use,
        "messages": user_histories[user_id],
        "temperature": 0.3, 
        "tools": [
            {
                "type": "web_search",
                "web_search": {"enable": True, "search_result": True}
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        result = response.json()
        
        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            user_histories[user_id].append({"role": "assistant", "content": ai_reply})
            
            cost_time = round(time.time() - start_time, 1)
            
            if "[思考]：" in ai_reply and "[结论]：" in ai_reply:
                parts = ai_reply.split("[结论]：", 1)
                thinking = parts[0].replace("[思考]：", "").strip()
                conclusion = parts[1].strip()
                
                # 纯文本发送，去掉了所有加粗符号，防止解析报错
                await update.message.reply_text(f"🧠 深度推演报告 (耗时 {cost_time}s)：\n\n{thinking[:4000]}")
                await update.message.reply_text(f"📝 最终回答：\n\n{conclusion[:4000]}")
                if len(conclusion) > 4000:
                    await update.message.reply_text(conclusion[4000:])
            else:
                await update.message.reply_text(ai_reply)
                
            try:
                await msg.delete()
            except:
                pass
        else:
            await update.message.reply_text(f"😵 接口异常：{result}")
    except Exception as e:
        await update.message.reply_text(f"💦 请求超时或崩溃：{e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if "http" in user_text and " " not in user_text:
        prompt_text = f"帮我深度阅读并提取这个网页的核心技术与信息：{user_text}"
    else:
        prompt_text = user_text
        
    await process_ai_response(update, user_id, prompt_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("👁️ 正在扫描图像特征...")
    
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    caption = update.message.caption if update.message.caption else "分析这张图片，给出硬核结论。"
    await process_ai_response(update, user_id, caption, image_base64=base64_image)

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🧹 记忆已清空，重启完毕。")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 DuNren 终极觉醒版\n\n"
        "🧠 引擎：glm-4-plus (旗舰级)\n"
        "🌐 技能：全网实时搜索阅读\n\n"
        "去测试吧，把最难的代码、最复杂的网页丢给我！"
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).read_timeout(120).write_timeout(120).connect_timeout(120).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("DuNren 终极觉醒版已启动！")
    app.run_polling()
