import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re  # 👈 必须加这个，用来提取文字

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
st.caption("专家深度解析 + 自动生成任务清单")

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
            
            # 🌟 修复点 1：换回高级 Prompt，强制 AI 生成 Action Items
            prompt = f"""
            你是一个针对 ADHD 人群设计的“微习惯”导师和高级知识整理专家。
            请对以下内容进行深度解析：

            1. **自动分类**：必须从以下 6 类中选一个：
               [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影]
            
            2. **核心总结**：提炼 3 点最核心的逻辑。

            3. **💡 专业实操建议 (专家视角)**：
               - 请基于你的专家角色，提供一个具有深度的、能够优化流程或思维的专业建议。

            4. **⚡️ ADHD 原子级 Action Items**：
               - 将上述建议拆解为 3-5 条极其具体的练习步骤。
               - 要求：每一步必须简单到 1 分钟内就能开始，没有任何心理负担。
               - 格式必须是：1. 动作... 或 - 动作...
            
            内容如下：
            {content}
            """
            
            with st.spinner("AI 正在深度解析并拆解任务..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.raw_source = content 
                
                # --- 智能分类逻辑 (适配你的 6 大需求) ---
                res_text = response.text
                if "英语" in res_text: st.session_state.temp_tag = "英语学习"
                elif "跳舞" in res_text or "舞蹈" in res_text: st.session_state.temp_tag = "舞蹈练习"
                elif "处事" in res_text or "职场" in res_text: st.session_state.temp_tag = "为人处事/职场"
                elif "专业" in res_text or "sterility" in res_text.lower(): st.session_state.temp_tag = "专业知识"
                elif "AI" in res_text or "编程" in res_text: st.session_state.temp_tag = "AI/编程"
                elif "视频" in res_text or "摄影" in res_text: st.session_state.temp_tag = "视频/摄影"
                else: st.session_state.temp_tag = "其他"
                
                # 🌟 修复点 2：增加“抓取逻辑”，自动把 Action Items 填进去
                ai_tasks = []
                lines = response.text.split('\n')
                capture_mode = False # 开关
                
                for line in lines:
                    line = line.strip()
                    # 当看到 "4." 和 "Action" 时，开始抓取
                    if "4." in line and "Action" in line:
                        capture_mode = True
                        continue 
                    
                    if capture_mode:
                        # 抓取以数字或横杠开头的行
                        match = re.match(r'^(\d+\.|-|\*)\s*(.*)', line)
                        if match:
                            task_content = match.group(2).strip()
                            if len(task_content) > 2:
                                ai_tasks.append(task_content)

                # 如果没抓到，给个默认值
                if not ai_tasks: 
                    ai_tasks = ["第一步...", "第二步..."]
                
                # 把抓到的任务填入表格
                st.session_state.todo_df = pd.DataFrame([
                    {"Done": False, "Task": t} for t in ai_tasks
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
        
        st.write("🎯 **Action Items (AI 自动生成 + 可修改)**")
        # 🌟 这里的表格现在会自动填入 AI 的建议了！
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
                                # 使用 Unicode 中划线效果
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
