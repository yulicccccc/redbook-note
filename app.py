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

# --- 3. 连接 Google Sheets (V14.0 诊断版) ---
@st.cache_resource
def connect_to_sheet():
    # 1. 检查 Secrets 格式
    if "gcp_json" not in st.secrets:
        return None, "❌ 错误：Secrets 里找不到 'gcp_json'。请检查是否漏了 gcp_json = \"\"\" 这行头。"

    try:
        # 2. 读取密钥
        secret_val = st.secrets["gcp_json"]
        if isinstance(secret_val, str):
            creds = json.loads(secret_val)
        else:
            creds = dict(secret_val) # 兼容某些自动转换情况
            
        # 3. 尝试连接
        gc = gspread.service_account_from_dict(creds)
        # ⚠️ 注意：这里必须是你表格的真实名称，不能错一个字
        sh = gc.open("My_Knowledge_Base").sheet1 
        return sh, "Success"
        
    except json.JSONDecodeError:
        return None, "❌ 错误：JSON 格式不对。请确保你完整复制了 key.json 的内容，没有少括号。"
    except gspread.SpreadsheetNotFound:
        return None, "❌ 错误：找不到表格。请确保你的 Google Sheet 名字叫 'My_Knowledge_Base'，并且已经把 Service Account 邮箱加为 Editor。"
    except Exception as e:
        return None, f"❌ 其他错误: {str(e)}"

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    
    # 🌟 实时连接诊断
    sheet, status_msg = connect_to_sheet()
    
    if sheet:
        st.success("✅ 知识库连接成功！")
        st.link_button("📂 打开表格", "https://docs.google.com/spreadsheets/u/0/")
    else:
        st.error("⚠️ 连接断开")
        st.info(f"诊断信息：\n{status_msg}")

    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    model_options = [
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]
    selected_model = st.selectbox("当前模型：", model_options)

    st.divider()
    if st.button("📚 生成复习文本"):
        if sheet:
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty:
                text = "# 本周知识汇总\n\n" + df.tail(15).to_string()
                st.code(text, language="markdown")

# --- 5. 主程序 ---
st.title("🧠 Kira's Brain Extension")
st.caption(f"🚀 引擎: {selected_model}")

if not api_key:
    st.warning("👈 请先输入 API Key")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel(selected_model)

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
        with st.spinner(f"🧠 {selected_model} 正在思考..."):
            try:
                inputs = []
                display_content = content_text if content_text else ""
                if content_text: inputs.append(content_text)
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    inputs.append(img)
                    display_content += " [图片]"
                
                st.session_state.raw_content = display_content

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
                st.error(f"解析出错: {e}")

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
        if sheet:
            try:
                final_actions = []
                for index, row in edited_df.iterrows():
                    t = row['Task']
                    if row['Done']: t = "".join([u'\u0336' + char for char in t]) + " ✅"
                    final_actions.append(f"{index+1}. {t}")
                action_str = "\n".join(final_actions)
                date_str = datetime.now().strftime("%Y-%m-%d")
                
                # V14 写入逻辑：适配你的 6 列表格
                sheet.append_row([
                    date_str, 
                    st.session_state.temp_tag, 
                    user_thought, 
                    action_str, 
                    st.session_state.analysis_result, 
                    st.session_state.get("raw_content", "")
                ])
                
                st.balloons()
                st.success("🎉 写入成功！")
                st.link_button("👀 去表格查岗", "https://docs.google.com/spreadsheets/u/0/")
                
            except Exception as e:
                st.error(f"写入失败: {e}")
        else:
            st.error("❌ 无法连接。请看侧边栏的诊断信息！")

    st.divider()
    with st.expander("💬 追问", expanded=False):
        for i, msg in enumerate(st.session_state.messages):
            if i > 0:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if chat_input := st.chat_input("追问..."):
            with st.chat_message("user"): st.markdown(chat_input)
            st.session_state.messages.append({"role": "user", "content": chat_input})
            
            model = genai.GenerativeModel(selected_model)
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
