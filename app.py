import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re
from datetime import datetime
from PIL import Image

# 页面配置
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

# --- 1. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

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
    if st.button("📚 生成本周复习文本"):
        sheet = connect_to_sheet()
        if sheet:
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty:
                text = "# 本周知识汇总\n\n" + df.tail(15).to_string()
                st.code(text, language="markdown")
                st.caption("👆 全选复制 -> 喂给 NotebookLM")

# --- 3. 主界面 ---
st.title("🧠 Kira's Brain Extension")
st.caption("深度解析 (V3) + 可选深聊 (V5)")

if not api_key:
    st.warning("👈 请先输入 API Key")
    st.stop()

# 🌟 修正：只用最标准的名字，不加 latest，不搞 try-except 🌟
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 第一部分：分析区
# ==========================================
st.header("1. 喂入素材", divider="rainbow")

content_text = st.text_area("📝 粘贴内容：", height=100)
uploaded_file = st.file_uploader("📸 上传截图", type=["jpg", "png", "webp"])

if st.button("✨ 启动大脑解析", type="primary", use_container_width=True):
    if not content_text and not uploaded_file:
        st.warning("请提供内容！")
    else:
        with st.spinner("🧠 正在连接 Gemini 1.5 Flash..."):
            try:
                inputs = []
                display_content = ""
                if content_text: 
                    inputs.append(content_text)
                    display_content += content_text
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    inputs.append(img)
                    display_content += " [图片内容]"
                
                st.session_state.raw_content = display_content

                # Prompt
                prompt = """
                你是一个懂 ADHD 的高级知识伙伴。请对输入内容解析：
                【Part 1: 深度卡片】(专家视角，保持 PhD 级的深度)
                1. **自动分类**：必须从 [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感] 选一。
                2. **核心逻辑**：3 个 bullet points 提炼最有价值信息。
                3. **专家建议**：深度、长远视角的洞察。

                【Part 2: 极简行动】(ADHD 教练视角)
                生成 **最多 3 个** 原子级 Action Items (1分钟能开始)。
                格式：请严格把任务放在 ---ACTION_START--- 和 ---ACTION_END--- 之间，每行一个。
                """
                inputs.append(prompt)

                response = model.generate_content(inputs)
                full_res = response.text
                
                # 解析
                main_analysis = full_res.split("---ACTION_START---")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_res, re.DOTALL)
                
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
                
                # 重置聊天
                st.session_state.messages = []
                st.session_state.messages.append({"role": "user", "content": f"素材：{display_content}"})
                st.session_state.messages.append({"role": "assistant", "content": full_res})

            except Exception as e:
                st.error(f"解析失败: {e}\n\n💡 如果提示 404 Not Found，请检查 requirements.txt 是否已添加！")

# ==========================================
# 第二部分：结果与存档
# ==========================================
if st.session_state.analysis_result:
    st.divider()
    st.header("2. 确认与行动", divider="violet")
    
    st.info(f"📂 分类：{st.session_state.get('temp_tag', '未分类')}")
    st.markdown(st.session_state.analysis_result)
    
    st.subheader("✅ 极简清单")
    edited_df = st.data_editor(st.session_state.todo_df, num_rows="dynamic", use_container_width=True)
    
    user_thought = st.text_area("💭 此时的想法:", height=80)
    
    if st.button("💾 存入知识库", type="primary", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet:
            try:
                final_actions = []
                for index, row in edited_df.iterrows():
                    t = row['Task']
                    if row['Done']: t = "".join([u'\u0336' + char for char in t]) + " ✅"
                    final_actions.append(f"{index+1}. {t}")
                action_str = "\n".join(final_actions)
                date_str = datetime.now().strftime("%Y-%m-%d")
                
                sheet.append_row([
                    date_str, st.session_state.temp_tag, user_thought, 
                    action_str, st.session_state.analysis_result, 
                    st.session_state.get("raw_content", "")
                ])
                st.success("🎉 已存入！")
            except Exception as e:
                st.error(f"写入失败: {e}")

    # ==========================================
    # 第三部分：深聊挂件
    # ==========================================
    st.divider()
    with st.expander("💬 没看懂？想深挖？点这里展开聊天", expanded=False):
        for i, msg in enumerate(st.session_state.messages):
            if i > 1:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        if chat_input := st.chat_input("追问..."):
            with st.chat_message("user"): st.markdown(chat_input)
            st.session_state.messages.append({"role": "user", "content": chat_input})
            
            # 这里的 history 简单处理，只传文本
            history_text = []
            for m in st.session_state.messages:
                 history_text.append({"role": "user" if m["role"]=="user" else "model", "parts": [str(m["content"])]})

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        chat = model.start_chat(history=history_text[:-1])
                        response = chat.send_message(chat_input)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"聊天出错: {e}")
