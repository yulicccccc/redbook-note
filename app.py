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
    # 🌟 建议在这里手动输入，或者留空从 Secrets 读取
    api_key_input = st.text_input("粘贴新的 Gemini API Key", type="password")
    st.success("✅ 深度洞察模式")
    st.info("Eagle Analytical 专属版")

st.title("🧠 深度知识内化系统")
st.caption("左侧深度思考 | 右侧原子执行 (ADHD 友好)")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书或网页复制内容粘贴到这里：", height=150)

if st.button("✨ 启动深度解析"):
    if not api_key_input:
        st.error("请先输入新的 API Key！旧的已被 Google 封禁。")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 分隔式 Prompt，确保深度与琐碎任务分离
            prompt = f"""
            你是一个顶级知识管理专家，擅长为 ADHD 患者设计极简执行路径。
            请对以下内容进行深度解析，并严格按照格式输出。

            【第一部分：深度分析】
            1. **自动分类**：从[英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影]中选一个。
            2. **核心逻辑总结**：提炼 3 点底层逻辑，文字精炼且有深度。
            3. **💡 专业实操建议**：提供一个能优化流程或思维的专家级建议。

            ---ACTION_START---
            1. 练习步骤一（原子级，1分钟内可开始）
            2. 练习步骤二（原子级）
            3. 练习步骤三（原子级）
            4. 练习步骤四（原子级）
            ---ACTION_END---
            
            内容如下：
            {content}
            """
            
            with st.spinner("Gemini 正在提取深度逻辑..."):
                full_response = model.generate_content(prompt).text
                
                # 分割内容
                main_analysis = full_response.split("---ACTION_START---")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_response, re.DOTALL)
                
                st.session_state.temp_res = main_analysis
                st.session_state.raw_source = content 
                
                # 智能分类标记
                if "英语" in main_analysis: st.session_state.temp_tag = "英语学习"
                elif "跳舞" in main_analysis or "舞蹈" in main_analysis: st.session_state.temp_tag = "舞蹈练习"
                elif "处事" in main_analysis or "职场" in main_analysis: st.session_state.temp_tag = "为人处事/职场"
                elif "专业" in main_analysis or "sterility" in main_analysis.lower(): st.session_state.temp_tag = "专业知识"
                elif "AI" in main_analysis or "编程" in main_analysis: st.session_state.temp_tag = "AI/编程"
                elif "视频" in main_analysis or "摄影" in main_analysis: st.session_state.temp_tag = "视频/摄影"
                else: st.session_state.temp_tag = "其他"

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
    st.header("2. 确认并入库", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 专家深度分析")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的笔记与行动")
        user_thought = st.text_area("心得总结：", placeholder="用你的话记录这一刻的启发...", height=100)
        
        st.write("🎯 **Action Items (原子拆解，可修改)**")
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 永久同步至 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
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
                        st.success("✅ 存入成功！记得去 Sheets 划掉已完成项。")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("心得是内化的第一步，请写下一句感悟。")

# --- 5. 历史 ---
st.divider()
if st.checkbox("📚 查看历史成长库"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data, use_container_width=True)
        except:
            st.write("表格读取中...")
