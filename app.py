import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re

# 页面配置
st.set_page_config(page_title="Kira's Brain Partner", layout="centered")

# --- 1. 连接 Google Sheets ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 确保你在 Streamlit Secrets 中配置了 gcp_json
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
    api_key_input = st.text_input("粘贴你的 Gemini Key", type="password")
    st.info("模型：Gemini 3 Flash Preview")

st.title("🧠 碎片知识内化系统")
st.caption("深度专家分析 + 原子级任务拆解 (仅限清单)")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("✨ 让 AI 深度解析"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 严格指令：前 3 点保持深度，仅清单部分原子化 🌟
            prompt = f"""
            你是一个高级知识整理专家。请针对以下内容进行深度解析：

            【第一部分：深度分析】
            1. 自动分类：必须从 [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影] 中选一个。
            2. 提炼核心知识点大纲（采用结构化列表）。
            3. 提供一个基于你角色的专业实操建议。

            【第二部分：任务拆解】
            请将上述建议拆解为 3-5 条针对 ADHD 友好的原子级 Action Items。
            规则：每步必须极简具体（例如：不要说“练习发音”，要说“对着镜子朗读文中第一句话 3 遍”）。
            格式：请将任务放在 ---ACTION_START--- 和 ---ACTION_END--- 标记之间。

            内容如下：
            {content}
            """
            
            with st.spinner("正在进行深度思考与原子拆解..."):
                full_response = model.generate_content(prompt).text
                
                # 分割内容
                main_analysis = full_response.split("【第二部分：任务拆解】")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_response, re.DOTALL)
                
                st.session_state.temp_res = main_analysis
                st.session_state.raw_source = content 
                
                # 智能分类
                st.session_state.temp_tag = "其他"
                for tag in ["英语学习", "舞蹈练习", "为人处事/职场", "专业知识", "AI/编程", "视频/摄影"]:
                    if tag in main_analysis:
                        st.session_state.temp_tag = tag
                        break

                # 提取原子任务
                if action_part:
                    tasks = [t.strip() for t in action_part.group(1).strip().split('\n') if t.strip()]
                    clean_tasks = [re.sub(r'^\d+\.\s*', '', t) for t in tasks]
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": t} for t in clean_tasks])
                else:
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": "开始微量练习"}])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 专家深度分析")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的内化笔记")
        user_thought = st.text_area("我的心得感悟：", placeholder="一句话总结背后的逻辑...", height=100)
        
        st.write("🎯 **Action Items (原子级拆解，可修改)**")
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 确认入库并同步至 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # 处理划掉效果
                        final_actions = []
                        for index, row in edited_df.iterrows():
                            t = row['Task']
                            if row['Done']:
                                t = "".join([u'\u0336' + char for char in t]) + " ✅"
                            final_actions.append(f"{index+1}. {t}")
                        
                        action_string = "\n".join(final_actions)
                        
                        sheet.append_row([
                            st.session_state.temp_tag, 
                            user_thought, 
                            action_string,
                            st.session_state.temp_res, 
                            st.session_state.raw_source
                        ])
                        st.success("入库成功！")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("写下一句心得吧。")

# --- 5. 库预览 ---
st.divider()
if st.checkbox("📚 查看我的历史知识库"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data, use_container_width=True)
        except:
            st.write("读取历史记录中...")
