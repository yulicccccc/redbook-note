import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re
from datetime import datetime
from PIL import Image

# --- 1. 页面配置 ---
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

# --- 2. 初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# --- 3. 连接 Google Sheets ---
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

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    # 简单的复习文本生成
    if st.button("📚 生成本周复习文本"):
        sheet = connect_to_sheet()
        if sheet:
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty:
                text = "# 本周知识汇总\n\n" + df.tail(15).to_string()
                st.code(text, language="markdown")

# --- 5. 主程序 ---
st.title("🧠 Kira's Brain Extension")
st.caption("V10.0 自检版 | 1.5 Flash 优先")

if not api_key:
    st.warning("👈 请先输入 API Key")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 核心功能区
# ==========================================
st.header("1. 喂入素材", divider="rainbow")

content_text = st.text_area("📝 粘贴内容：", height=100)
uploaded_file = st.file_uploader("📸 上传截图", type=["jpg", "png", "webp"])

if st.button("✨ 启动大脑解析", type="primary", use_container_width=True):
    if not content_text and not uploaded_file:
        st.warning("请提供内容！")
    else:
        status_box = st.empty()
        with status_box.status("🧠 正在连接大脑...", expanded=True) as s:
            try:
                # 1. 准备输入
                inputs = []
                display_content = content_text if content_text else ""
                if content_text: inputs.append(content_text)
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    inputs.append(img)
                    display_content += " [图片]"
                
                st.session_state.raw_content = display_content

                # 2. 核心 Prompt
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

                # 3. 尝试调用 1.5 Flash (因为你的环境已经是新的了，理论上应该用这个)
                s.write("正在尝试连接 gemini-1.5-flash ...")
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(inputs)
                
                s.update(label="✅ 分析成功！", state="complete", expanded=False)
                full_res = response.text

                # --- 成功后的处理逻辑 ---
                main_analysis = full_res.split("---ACTION_START---")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_res, re.DOTALL)
                
                st.session_state.analysis_result = main_analysis
                
                st.session_state.temp_tag = "其他灵感"
                for tag in ["跳舞", "创意摄像", "英语", "AI应用", "人情世故", "学习与个人成长"]:
                    if tag in main_analysis:
                        st.session_state.temp_tag = tag
                        break

                if action_part:
                    tasks = [t.strip() for t in action_part.group(1).strip().split('\n') if t.strip()]
                    clean_tasks = [re.sub(r'^\d+\.\s*', '', t).replace('- [ ]', '').strip() for t in tasks]
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": t} for t in clean_tasks])
                else:
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": "阅后即焚"}])
                
                st.session_state.messages = []
                st.session_state.messages.append({"role": "user", "content": f"素材：{display_content}"})
                st.session_state.messages.append({"role": "assistant", "content": full_res})

            except Exception as e:
                s.update(label="❌ 出错啦", state="error", expanded=True)
                st.error(f"主要模型调用失败: {e}")
                
                # ==============================
                # 🕵️‍♀️ 自动侦探模式：查询可用模型
                # ==============================
                st.divider()
                st.warning("正在诊断你的 API Key 支持哪些模型...")
                try:
                    available_models = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                    
                    if available_models:
                        st.success(f"✅ 你的 Key 可以访问这些模型: {available_models}")
                        st.info("请把上面那个列表截图发给 AI，我们就能立刻知道该用哪个名字了！")
                    else:
                        st.error("❌ 你的 API Key 似乎无法访问任何内容生成模型。请检查 Key 是否有效，或是否开通了权限。")
                except Exception as debug_e:
                    st.error(f"诊断也失败了 (可能是网络或Key的问题): {debug_e}")

# ==========================================
# 结果与存档
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
    # 聊天挂件
    # ==========================================
    st.divider()
    with st.expander("💬 追问 (纯文本)", expanded=False):
        for i, msg in enumerate(st.session_state.messages):
            if i > 0:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if chat_input := st.chat_input("追问..."):
            with st.chat_message("user"): st.markdown(chat_input)
            st.session_state.messages.append({"role": "user", "content": chat_input})
            
            # 使用 1.5 Flash 进行对话
            model = genai.GenerativeModel('gemini-1.5-flash')
            history_text = [{"role": "user" if m["role"]=="user" else "model", "parts": [str(m["content"])]} for m in st.session_state.messages]

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        chat = model.start_chat(history=history_text[:-1])
                        response = chat.send_message(chat_input)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"聊天出错: {e}")
