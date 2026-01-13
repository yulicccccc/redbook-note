import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd

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
    api_key_input = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.info("Model: Gemini 3 Flash Preview")

st.title("🧠 碎片知识内化系统")
st.caption("Expert Analysis + Interactive Task List")

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
            
            prompt = f"""
            你是一个高级知识整理专家。请针对以下内容进行深度解析：
            1. 自动分类：从[AI应用, 跳舞, 职场英语, 其他]中选一个。
            2. 提炼核心知识点大纲（采用结构化列表）。
            3. 提供一个基于你角色的专业实操建议。
            
            内容如下：
            {content}
            """
            
            with st.spinner("AI 正在解析并构思练习方案..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.raw_source = content 
                
                # 分类映射
                st.session_state.temp_tag = "Others"
                if "AI" in response.text: st.session_state.temp_tag = "AI"
                elif "跳舞" in response.text: st.session_state.temp_tag = "Dance"
                elif "英语" in response.text: st.session_state.temp_tag = "English"
                
                # 初始化一个空的待办清单表格
                st.session_state.todo_df = pd.DataFrame([
                    {"Done": False, "Task": "练习建议 1"},
                    {"Done": False, "Task": "练习建议 2"}
                ])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 AI 总结")
        st.info(f"Tag: {st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的笔记与行动")
        user_thought = st.text_area("心得总结：", placeholder="写下你的理解...", height=100)
        
        st.write("🎯 **Action Items (可自行添加/打勾)**")
        # 🌟 核心：使用 data_editor 让用户像在 Excel 里一样添加 1,2,3,4
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic", # 允许用户点击 "+" 增加行
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 永久存入 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # 🌟 处理 Action Item：如果打勾了，就加上中划线 ~~Task~~
                        final_actions = []
                        for index, row in edited_df.iterrows():
                            task_text = row['Task']
                            if row['Done']:
                                # 使用 Unicode 的中划线效果，这样在 Google Sheets 纯文字里也能看出划掉的效果
                                # 也可以使用标准的 Markdown ~~ 格式
                                task_text = "".join([u'\u0336' + char for char in task_text]) + " ✅"
                            final_actions.append(f"{index+1}. {task_text}")
                        
                        action_string = "\n".join(final_actions)
                        
                        # 存入 5 列：Category, Note, Action Item, Summary, Source
                        sheet.append_row([
                            st.session_state.temp_tag, 
                            user_thought, 
                            action_string,
                            st.session_state.temp_res, 
                            st.session_state.raw_source
                        ])
                        st.success("✅ 存入成功！已完成项已自动标记。")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("心得是内化的灵魂，写一句吧！")

# --- 5. 历史回顾 ---
st.divider()
if st.checkbox("📚 查看我的知识库"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                st.dataframe(data, use_container_width=True)
            else:
                st.info("目前还没有笔记哦。")
        except:
            st.write("读取失败，请检查表格表头。")
