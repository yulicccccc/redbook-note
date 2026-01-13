import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 1. 连接 Google Sheets 的函数 ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 从 Secrets 读取配置
        json_str = st.secrets["gcp_json"]
        creds_dict = json.loads(json_str)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("My_Knowledge_Base")
        return sh.sheet1
    except Exception as e:
        st.warning(f"表格连接提示: {e}")
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.success("已启用：Gemini 2.5 (高性能版)")

st.title("🧠 碎片知识内化系统")
st.caption("基于 Gemini 2.5 + Google Sheets 云存储")

# --- 3. 收集阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("✨ 让 AI 深度解析"):
    if not api_key:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # 使用你账号里可用的最新模型
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # 👇 这里就是你最喜欢的那个“灵魂 Prompt”！我把它找回来了 👇
            prompt = f"""
            你是一个高级知识整理专家。请针对以下内容进行深度解析：
            1. 自动分类：从[AI应用, 跳舞, 职场英语, 其他]中选一个。
            2. 提炼核心知识点大纲（采用结构化列表）。
            3. 提供一个基于你角色的专业实操建议。 (重点)
            
            内容如下：
            {content}
            """
            
            with st.spinner("AI 正在思考专业建议..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                
                # 智能分类标记
                if "AI" in response.text: st.session_state.temp_tag = "AI应用"
                elif "跳舞" in response.text: st.session_state.temp_tag = "跳舞"
                elif "英语" in response.text: st.session_state.temp_tag = "职场英语"
                else: st.session_state.temp_tag = "其他"

        except Exception as e:
            st.error(f"❌ 解析失败: {e}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    # 显示 AI 的结果
    st.info(f"🏷️ 分类：{st.session_state.temp_tag}")
    st.markdown(st.session_state.temp_res)
    
    # 你的笔记区
    user_thought = st.text_area("✍️ 我的内化笔记 (必填)：", 
                              placeholder="比如：这个建议我明天上课可以用...",
                              height=200)
    
    if st.button("💾 永久存入 Google Sheets"):
        if user_thought:
            sheet = connect_to_sheet()
            if sheet:
                try:
                    # 存入表格：[分类, 心得, AI原话]
                    sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                    st.success("✅ 成功！笔记已飞入你的 Google 表格！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")
            else:
                st.error("表格连接失败，请检查 Secrets。")
        else:
            st.warning("请写下一句你的心得再保存。")

# --- 5. 历史回顾 ---
st.divider()
if st.checkbox("📚 查看 Google Sheets 里的历史笔记"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                st.dataframe(data)
            else:
                st.info("表格还没数据，快去存第一条！")
        except:
            st.write("暂无数据")
