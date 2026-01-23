import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
from datetime import datetime

# 页面配置 (手机优化)
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

# --- 1. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False

@st.cache_resource
def connect_to_sheet():
    try:
        if "gcp_json" in st.secrets:
            creds = json.loads(st.secrets["gcp_json"])
            gc = gspread.service_account_from_dict(creds)
            return gc.open("My_Knowledge_Base").sheet1
        return None
    except:
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("📚 复习区")
    if st.button("生成本周复习文本"):
        sheet = connect_to_sheet()
        if sheet:
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty:
                text = "# 本周知识汇总\n\n" + df.tail(15).to_string()
                st.code(text, language="markdown")
                st.caption("👆 全选复制 -> 喂给 NotebookLM App")

# --- 3. 主界面 ---
st.title("🧠 Kira's Brain Extension")
st.caption("一站式深聊 | 智能总结入库 | 1.5 Flash")

if not api_key:
    st.warning("👈 请先在侧边栏输入 API Key")
    st.stop()

# 🌟 修复核心：改回最标准的模型名称 🌟
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 4. 聊天展示区 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. 聊天输入区 ---
# 第一轮：启动对话 (带 Prompt)
if not st.session_state.chat_active:
    uploaded_file = st.file_uploader("📸 上传图片 (可选)", type=["jpg", "png", "webp"])
    user_input = st.chat_input("在此粘贴小红书链接/文案...")

    if user_input or uploaded_file:
        st.session_state.chat_active = True
        
        # 显示用户输入
        display_text = user_input if user_input else "[图片上传]"
        if uploaded_file: display_text += " 📷"
        
        with st.chat_message("user"):
            if uploaded_file: st.image(uploaded_file, width=200)
            st.markdown(user_input if user_input else "")
        
        st.session_state.messages.append({"role": "user", "content": display_text})

        # 准备发送给 AI 的内容
        content_parts = []
        if user_input: content_parts.append(user_input)
        if uploaded_file:
            from PIL import Image
            img = Image.open(uploaded_file)
            content_parts.append(img)

        # 核心 System Prompt
        system_prompt = """
        你是一个懂 ADHD 的高级知识伙伴。请对输入内容解析：
        【Part 1: 深度卡片】(专家视角，保持 PhD 级的深度)
        1. **自动分类**：从 [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感] 选一。
        2. **核心逻辑**：3 个 bullet points 提炼最有价值信息。
        3. **专家建议**：深度、长远视角的洞察。
        【Part 2: 极简行动】(ADHD 教练视角)
        生成 **最多 3 个** 原子级 Action Items (1分钟能开始)。
        格式：使用 `- [ ]` 列表。
        """
        content_parts.append(system_prompt)

        with st.chat_message("assistant"):
            with st.spinner("🧠 深度分析中..."):
                try:
                    response = model.generate_content(content_parts)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"出错: {e}")

# 后续轮次：自由深聊
else:
    if user_input := st.chat_input("继续追问 (例如：给个例子 / 这一步怎么做？)"):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 构建历史上下文
        chat_history = []
        for msg in st.session_state.messages:
            role = "user" if msg["role"] == "user" else "model"
            if "📷" not in msg["content"]: 
                chat_history.append({"role": role, "parts": [msg["content"]]})
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    chat = model.start_chat(history=chat_history[:-1])
                    response = chat.send_message(user_input)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"出错: {e}")

# --- 6. 一键总结与存档区 ---
if st.session_state.chat_active and len(st.session_state.messages) > 1:
    st.divider()
    st.info("聊完了？点击下方按钮，AI 会自动帮你把刚才的所有对话精华提取出来存入表格。")
    
    if st.button("✨ 一键总结并入库 (Auto-Save)", type="primary", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet:
            with st.spinner("正在回顾刚才的聊天记录并提取精华..."):
                try:
                    # 1. 总结
                    full_conversation = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    
                    summary_prompt = f"""
                    请回顾以下对话记录，帮我提取关键信息以便存档到 Google Sheets。
                    对话记录：
                    {full_conversation}
                    
                    请严格按照以下格式输出 4 行内容：
                    Line 1: [最终分类] (从跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感 中选一个)
                    Line 2: [核心心得] (一句话总结)
                    Line 3: [最终行动] (Action Items，逗号分隔)
                    Line 4: [深度摘要] (200字以内)
                    """
                    
                    summary_res = model.generate_content(summary_prompt).text
                    
                    # 2. 解析
                    lines = summary_res.strip().split('\n')
                    category = lines[0].split(':')[-1].strip() if len(lines) > 0 else "未分类"
                    note = lines[1].split(':')[-1].strip() if len(lines) > 1 else "无"
                    actions = lines[2].split(':')[-1].strip() if len(lines) > 2 else "无"
                    analysis = lines[3].split(':')[-1].strip() if len(lines) > 3 else "见详情"
                    
                    # 3. 存入
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    original_source = st.session_state.messages[0]['content'] 
                    
                    sheet.append_row([
                        date_str, category, note, actions, analysis, original_source
                    ])
                    
                    st.success("🎉 存档成功！")
                    if st.button("开启新话题"):
                        st.session_state.messages = []
                        st.session_state.chat_active = False
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"总结或存档失败: {e}")
