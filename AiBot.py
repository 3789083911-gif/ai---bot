from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import base64
import asyncio

# 👇 你的 Token 和 智谱 Key 👇
TG_TOKEN = "8860844332:AAGtIhKf_rWHOePaI7_jZrTqKN4qM7SYn4U"
ZHIPU_KEY = "9c9efbbe8dd143ca9a1e6f2a189373cd.gtUPOWwwgKXzyc7C"

# 🧠 注入“全网巡查”灵魂
SYSTEM_PROMPT = (
    "你是 DuNren，一个具备全网实时检索能力的超级黑客 AI。"
    "**【强制规则】**：只要用户询问最新资讯、找工具、找资源、或者任何你不确定的问题，你**必须立刻调用 web_search 工具去全网巡查网页**。"
    "**【强制输出格式】**：\n"
    "1. 必须先用 `[思考]：` 开头，写出你刚才在网上搜到了什么、分析了哪些网页、得出了什么推演。\n"
    "2. 思考结束后，用 `[结论]：` 开头，给出最终答案（包含搜到的真实链接、代码、或者工具）。\n"
    "拒绝废话，排版清晰，如果是找资源，必须给出真实的网页链接。"
)

user_histories = {}

# ==========================================
# 🧠 核心逻辑：全网巡查 + 深度思考
# ==========================================
async def process_ai_response(update: Update, user_id: int, prompt_text: str, image_base64: str = None):
    # 1. 先发一条提示，告诉用户正在巡查网页
    msg = await update.message.reply_text("🌐 **DuNren 正在全网巡查网页、检索最新资料并深度思考...**", parse_mode='Markdown')
    
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 判断是纯文本还是带图
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
    if len(user_histories[user_id]) > 12:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-11:]

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"}
    
    # 🔥 这里开启了联网搜索插件
    data = {
        "model": model_to_use,
        "messages": user_histories[user_id],
        "temperature": 0.7,
        "tools": [
            {
                "type": "web_search",
                "web_search": {
                    "enable": True,
                    "search_result": True  # 强迫它返回网页搜索结果
                }
            }
        ]
    }

    try:
        # 联网搜索+思考耗时极长，直接给 90 秒超时
        response = requests.post(url, headers=headers, json=data, timeout=90)
        result = response.json()
        
        if "choices" in result:
            ai_reply = result["choices"][0]["message"]["content"]
            user_histories[user_id].append({"role": "assistant", "content": ai_reply})
            
            # 解析思考与结论
            if "[思考]：" in ai_reply and "[结论]：" in ai_reply:
                parts = ai_reply.split("[结论]：", 1)
                thinking = parts[0].replace("[思考]：", "").strip()
                conclusion = parts[1].strip()
                
                await msg.delete() # 删掉“正在巡查”的提示
                
                # 发送思考过程
                await update.message.reply_text(f"🧠 **巡查与思考过程：**\n\n{thinking[:4000]}", parse_mode='Markdown')
                # 发送最终结论
                await update.message.reply_text(f"🎯 **最终硬核结论：**\n\n{conclusion[:4000]}", parse_mode='Markdown')
                if len(conclusion) > 4000:
                    await update.message.reply_text(conclusion[4000:])
            else:
                await msg.delete()
                await update.message.reply_text(ai_reply)
        else:
            await msg.edit_text(f"😵 接口异常：{result}")
    except Exception as e:
        await msg.edit_text(f"💦 全网巡查超时：{e}")

# ==========================================
# 📩 处理文字消息
# ==========================================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await process_ai_response(update, user_id, user_text)

# ==========================================
# 👁️ 处理图片消息
# ==========================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("👁️ **正在提取图片数据...**")
    
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    caption = update.message.caption if update.message.caption else "详细分析这张图，如果里面有代码或报错，帮我看看怎么解决。"
    await process_ai_response(update, user_id, caption, image_base64=base64_image)

# ==========================================
# 🧹 清除记忆
# ==========================================
async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🧹 记忆已清空。")

# ==========================================
# 🚀 启动
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **DuNren 全网巡查版已接管**\n\n"
        "🌐 能力：全网实时检索、网页巡查\n"
        "🧠 大脑：`glm-4-plus` / `glm-4v-plus`\n\n"
        "你可以试试问我：\n"
        "👉 “去网上搜一下最近有什么好用的 Unity 逆向工具”\n"
        "👉 “帮我找几个能用的 Frida 脱壳脚本链接”\n\n"
        "我会先告诉你我巡查到了什么，再给你最终结论！", 
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).read_timeout(90).write_timeout(90).connect_timeout(90).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("DuNren 全网巡查版已启动！")
    app.run_polling()
