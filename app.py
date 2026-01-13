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
    api_key_input = st.text_input("粘贴你的 Gemini Key", type="password")
    st.info("🧠 Model: Gemini 3 Flash")
    st.caption("PhD Microbiologist | 舞蹈教师 | ADHD 优化模式")

st.title("🧠 碎片知识深度内化系统")
st.caption("专家深度解析 + 原子级任务自动拆解")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书、网页或工作笔记中复制内容：", height=150)

if st.button("✨ 启动深度思考"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 针对 Kira 背景定制的专家 Prompt
            prompt = f"""
            你是一个高级知识内化专家。你的用户 Kira 拥有以下背景，请务必结合这些背景进行解析：
            - **背景**：Microbiology PhD，就职于 Eagle Analytical (Houston)，负责 parenteral drug 的 sterility testing。
            - **特质**：有 ADHD，需要极低门槛、极其具体的行动指令。
            - **兴趣**：跳舞（舞蹈老师）、学英语（美国职场环境）、AI/编程、视频摄影。

            请严格按照以下 4 个部分解析内容，不要合并：

            1. **自动分类**：只从这 6 个中选一个：
               [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影]
            
            2. **核心总结**：提炼 3 点最核心的逻辑。

            3. **💡 专业实操建议 (专家视角)**：
               - 请基于你的专家角色，提供一个具有深度的、能够优化流程或思维的专业建议。

            4. **⚡️ ADHD 原子级 Action Items (清单)**：
               - 将上述建议拆解为 3-5 条具体的练习步骤。
               - 使用数字列表 (1., 2.) 格式。
               - 要求：每一步必须简单到 1 分钟内就能开始，没有任何心理负担。
            
            内容如下：
            {content}
            """
            
            with st.spinner("Gemini 正在为博士级大脑构思方案..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.raw_source = content 
                
                # --- 智能分类映射 ---
                res_text = response.text
                if "英语" in res_text: st.session_state.temp_tag = "英语学习"
                elif "跳舞" in res_text or "舞蹈" in res_text: st.session_state.temp_tag = "舞蹈练习"
                elif "处事" in res_text or "职场" in res_text: st.session_state.temp_tag = "为人处事/职场"
                elif "专业" in res_text or "sterility" in res_text.lower(): st.session_state.temp_tag = "专业知识"
                elif "AI" in res_text or "编程" in res_text: st.session_state.temp_tag = "AI/编程"
                elif "视频" in res_text or "摄影" in res_text: st.session_state.temp_tag = "视频/摄影"
                else: st.session_state.temp_tag = "其他"
                
                # --- 自动抓取 Action Items 到交互表格 ---
                ai_tasks = []
                lines = response.text.split('\n')
                capture_mode = False 
                for line in lines:
                    line = line.strip()
                    if "4." in line and "Action" in line:
                        capture_mode = True
                        continue 
                    if capture_mode:
                        match = re.match(r'^(\d+\.|-|\*)\s*(.*)', line)
                        if match:
                            task_content = match.group(2).strip()
                            if len(task_content) > 2:
                                ai_tasks.append(task_content)

                if not ai_tasks: ai_tasks = ["开始微量复习", "记录第一个感受"]
                
                st.session_state.todo_df = pd.DataFrame([
                    {"Done": False, "Task": t} for t in ai_tasks
                ])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解、修正与同步", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 AI 专家报告")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的行动清单")
        user_thought = st.text_area("心得总结 (一句即可)：", placeholder="写下你的 PhD 思考或感悟...", height=100)
        
        st.write("🎯 **ADHD 原子任务 (已自动从 AI 内容中提取)**")
        # 🌟 这里的表格现在会自动显示第 4 点拆解出的任务
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 永久存入 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # 生成带 ✅ 的任务文本
                        final_actions = []
                        for index, row in edited_df.iterrows():
                            t = row['Task']
                            if row['Done']:
                                t = "".join([u'\u0336' + char for char in t]) + " ✅"
                            final_actions.append(f"{index+1}. {t}")
                        
                        action_string = "\n".join(final_actions)
                        
                        # 按 Category, Note, Action Item, Summary, Source 存入
                        sheet.append_row([
                            st.session_state.temp_tag, 
                            user_thought, 
                            action_string,
                            st.session_state.temp_res, 
                            st.session_state.raw_source
                        ])
                        st.success("✅ 存入成功！知识已归库。")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("请至少写一句心得，它是防止 ADHD 遗忘的钩子。")

# --- 5. 历史回顾 ---
st.divider()
if st.checkbox("📚 查看我的历史成长库"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data, use_container_width=True)
        except:
            st.write("表格读取中...")
