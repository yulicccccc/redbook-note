import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re
from datetime import datetime
from PIL import Image

# 页面配置 (手机优化)
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

# --- 1. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "raw_content" not in st.session_state:
    st.session_state.raw_content = ""

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
st.caption("先分析 (V3) -> 可选深聊 (V5)")

if not api_key:
    st.warning("👈 请先输入 API Key")
    st.stop()

genai.configure(api_key=api_key)
# 使用稳定版模型
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

# ==========================================
# 第一部分：经典分析流程 (还原 V3.2)
# ==========================================
st.header("1. 喂入素材", divider="rainbow")

content_text = st.text_area("📝 粘贴链接/文字：", height=100, key="input_text")
uploaded_file = st.file_uploader("📸 上传截图 (可选)", type=["jpg", "png", "webp"], key="input_img")

# 启动按钮
if st.button("✨ 启动大脑解析", type="primary", use_container_width=True):
    if not content_text and not uploaded_file:
        st.warning("请提供内容！")
    else:
        with st.spinner("🧠 深度分析中 (PhD + ADHD 模式)..."):
            try:
                # 准备输入
                inputs = []
                display_content = ""
                if content_text: 
                    inputs.append(content_text)
                    display_content += content_text
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    inputs.append(img)
                    display_content += " [图片内容]"
                
                # 存原始素材供后续使用
                st.session_state.raw_content = display_content
                st.session_state.has_image = True if uploaded_file else False

                # 核心 Prompt
                prompt = """
                你是一个懂 ADHD 的高级知识伙伴。请对输入内容解析：
                【Part 1: 深度卡片】(专家视角，保持 PhD 级的深度)
                1. **自动分类**：必须从 [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感] 选一。
                2. **核心逻辑**：3 个 bullet points 提炼最有价值信息（如果是图，分析细节）。
                3. **专家建议**：深度、长远视角的洞察。

                【Part 2: 极简行动】(ADHD 教练视角)
                生成 **最多 3 个** 原子级 Action Items (1分钟能开始)。
                格式：请严格把任务放在 ---ACTION_START--- 和 ---ACTION_END--- 之间，每行一个。
                """
                inputs.append(prompt)

                response = model.generate_content(inputs)
                full_res = response.text
                
                # 解析结果
                main_analysis = full_res.split("---ACTION_START---")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_res, re.DOTALL)
                
                # 存入 State
                st.session_state.analysis_result = main_analysis
                
                # 提取分类
                st.session_state.temp_tag = "其他灵感"
                for tag in ["跳舞", "创意摄像", "英语", "AI应用", "人情世故", "学习与个人成长"]:
                    if tag in main_analysis:
                        st.session_state.temp_tag = tag
                        break

                # 提取任务
                if action_part:
                    tasks = [t.strip() for t in action_part.group(1).strip().split('\n') if t.strip()]
                    clean_tasks = [re.sub(r'^\d+\.\s*', '', t).replace('- [ ]', '').strip() for t in tasks]
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": t} for t in clean_tasks])
                else:
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": "阅后即焚"}])
                
                # 初始化聊天记录 (把分析结果作为第一轮对话的上下文)
                st.session_state.messages = []
                st.session_state.messages.append({"role": "user", "content": f"素材内容：{display_content}"})
                st.session_state.messages.append({"role": "assistant", "content": full_res})

            except Exception as e:
                st.error(f"解析失败: {e}")

# ==========================================
# 第二部分：结果展示 & 快速存档 (V3.2)
# ==========================================
if st.session_state.analysis_result:
    st.divider()
    st.header("2. 确认与行动", divider="violet")
    
    # 结果展示区
    st.info(f"📂 分类：{st.session_state.get('temp_tag', '未分类')}")
    st.markdown(st.session_state.analysis_result)
    
    st.subheader("✅ 极简清单 (可修改)")
    edited_df = st.data_editor(st.session_state.todo_df, num_rows="dynamic", use_container_width=True)
    
    user_thought = st.text_area("💭 此时此刻的想法 (存库用):", height=80)
    
    # 🌟 快速存档按钮 (高频使用) 🌟
    if st.button("💾 存入知识库 (完成)", type="primary", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet:
            try:
                # 整理 Action Items
                final_actions = []
                for index, row in edited_df.iterrows():
                    t = row['Task']
                    if row['Done']: t = "".join([u'\u0336' + char for char in t]) + " ✅"
                    final_actions.append(f"{index+1}. {t}")
                action_str = "\n".join(final_actions)
                
                date_str = datetime.now().strftime("%Y-%m-%d")
                
                sheet.append_row([
                    date_str,
                    st.session_state.temp_tag, 
                    user_thought, 
                    action_str,
                    st.session_state.analysis_result, 
                    st.session_state.raw_content
                ])
                st.success("🎉 已存入！(如果不聊天，现在就可以关掉网页了)")
            except Exception as e:
                st.error(f"写入失败: {e}")

    # ==========================================
    # 第三部分：深聊扩展 (V5.0 挂件) - 放在最后
    # ==========================================
    st.divider()
    with st.expander("💬 没看懂？想深挖？点这里展开聊天 (可选)", expanded=False):
        st.caption("这里是基于上方分析结果的追问区。")
        
        # 显示聊天记录 (从第二轮开始显示，因为第一轮是上面的分析报告)
        # 这里只显示追加的问答，避免重复
        for i, msg in enumerate(st.session_state.messages):
            if i > 1: # 跳过初始的 Context 和 Analysis
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 聊天输入框
        if chat_input := st.chat_input("追问：这个建议具体怎么做？"):
            # 显示用户输入
            with st.chat_message("user"):
                st.markdown(chat_input)
            st.session_state.messages.append({"role": "user", "content": chat_input})
            
            # 这里的 history 要包含最初的分析结果
            history_for_api = []
            for m in st.session_state.messages:
                # 简单映射，忽略图片防止报错（1.5 Flash 对多轮图片支持有限）
                role = "user" if m["role"] == "user" else "model"
                history_for_api.append({"role": role, "parts": [m["content"]]})

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        chat = model.start_chat(history=history_for_api[:-1])
                        response = chat.send_message(chat_input)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"聊天出错: {e}")
        
        # 聊天存档按钮
        if len(st.session_state.messages) > 2:
            if st.button("✨ 把刚才聊的补充进知识库"):
                sheet = connect_to_sheet()
                if sheet:
                    # 简单拼接聊天记录
                    chat_log = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[2:]])
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    sheet.append_row([
                        date_str,
                        st.session_state.temp_tag,
                        "聊天补充存档",
                        "见详情",
                        chat_log,
                        "基于: " + st.session_state.raw_content[:20] + "..."
                    ])
                    st.success("补充对话已存档！")
