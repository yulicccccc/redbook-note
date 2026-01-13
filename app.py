import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 1. 连接 Google Sheets ---
@st.cache_resource
def connect_to_sheet():
    try:
        json_str = st.secrets["gcp_json"]
        creds_dict = json.loads(json_str)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("My_Knowledge_Base")
        return sh.sheet1
    except Exception as e:
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    # 🌟 这里的提示变了
    st.info("🔥 已启用最强大脑：Gemini 2.5 Pro")

st.title("🧠 深度知识内化系统 (Pro版)")
st.caption("启用深度推理模式，提供流程优化与风控建议")

# --- 3. 收集阶段 ---
st.header("1. 深度解析", divider="blue")
content = st.text_area("请从小红书复制文案（特别是涉及流程/方法的）：", height=150)

if st.button("✨ 启动深度思考"):
    if not api_key:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # 🌟 关键改动 1：换用 Pro 模型，思考更深
            model = genai.GenerativeModel('models/gemini-2.5-pro')
            
            # 🌟 关键改动 2：Prompt 专门针对你的需求进行了“咨询顾问化”改造
            prompt = f"""
            你是一个资深的流程优化专家和技能导师。请深入分析以下内容，不要只做简单的总结。
            
            请按以下结构输出：
            1. **核心逻辑拆解**：用简练的语言概括内容的核心机制。
            2. **关键控制点 (Checkpoints)**：(重要) 指出在这个流程或方法中，最容易出错的地方在哪里？应该在哪里设置“检查点”或“确认环节”来确保结果符合预期？
            3. **实操落地建议**：给出一个具体的、可执行的下一步动作。
            4. **自动分类**：[AI应用, 跳舞, 职场英语, 其他]
            
            内容如下：
            {content}
            """
            
            with st.spinner("Gemini Pro 正在进行逻辑推演与风控分析..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                
                # 分类标记
                if "AI" in response.text: st.session_state.temp_tag = "AI应用"
                elif "跳舞" in response.text: st.session_state.temp_tag = "跳舞"
                elif "英语" in response.text: st.session_state.temp_tag = "职场英语"
                else: st.session_state.temp_tag = "其他"

        except Exception as e:
            st.error(f"调用失败: {e}")
            st.info("如果 Pro 模型报错，请尝试改回 'models/gemini-2.5-flash'")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    st.info(f"🏷️ 分类：{st.session_state.temp_tag}")
    st.markdown(st.session_state.temp_res)
    
    user_thought = st.text_area("✍️ 我的内化笔记：", 
                              placeholder="针对 AI 提出的 Checkpoint，你打算怎么优化你的习惯？",
                              height=200)
    
    if st.button("💾 永久存入 Google Sheets"):
        if user_thought:
            sheet = connect_to_sheet()
            if sheet:
                try:
                    sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                    st.success("✅ 深度笔记已保存！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")
            else:
                st.error("表格连接失败")
        else:
            st.warning("写点心得吧，深度思考的结果值得记录。")

# --- 5. 历史 ---
st.divider()
if st.checkbox("📚 查看历史笔记"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                st.dataframe(data)
        except:
            st.write("暂无数据")
