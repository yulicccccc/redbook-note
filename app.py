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
    api_key_input = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.success("✅ 专家模式 + ADHD 友好模式")
    st.info(" Eagle Analytical 专属定制")

st.title("🧠 深度知识内化系统")
st.caption("专家深度建议 + 原子级任务拆解")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书或网页复制内容粘贴到这里：", height=150)

if st.button("✨ 启动深度思考"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 强化版 Prompt：包含你最爱的“专家建议” 🌟
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
            
            内容如下：
            {content}
            """
            
            with st.spinner("Gemini 正在进行专家级推演..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.raw_source = content 
                
                # 精准分类逻辑
                res_text = response.text
                if "英语" in res_text: st.session_state.temp_tag = "英语学习"
                elif "跳舞" in res_text or "舞蹈" in res_text: st.session_state.temp_tag = "舞蹈练习"
                elif "处事" in res_text or "职场" in res_text: st.session_state.temp_tag = "为人处事/职场"
                elif "专业" in res_text or "sterility" in res_text.lower(): st.session_state.temp_tag = "专业知识"
                elif "AI" in res_text or "编程" in res_text: st.session_state.temp_tag = "AI/编程"
                elif "视频" in res_text or "摄影" in res_text: st.session_state.temp_tag = "视频/摄影"
                else: st.session_state.temp_tag = "其他"

                # 提取 AI 生成的 Action Items
                lines = response.text.split('\n')
                # 寻找带数字序号的行，过滤掉标题行
                ai_tasks = []
                for l in lines:
                    match = re.match(r'^(\d+)\.\s*(.*)', l.strip())
                    if match and "Action" not in l and "分类" not in l:
                        ai_tasks.append(match.group(2))
                
                if not ai_tasks: ai_tasks = ["开始微量练习", "记录反馈"]
                
                st.session_state.todo_df = pd.DataFrame([
                    {"Done": False, "Task": t} for t in ai_tasks[:5]
                ])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解、修正与吸收", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 AI 专家分析报告")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的笔记与行动")
        user_thought = st.text_area("心得总结 (必填)：", placeholder="写下一句你的感悟...", height=100)
        
        st.write("🎯 **ADHD 任务清单 (可双击修改)**")
        # 用户可以在这里微调 AI 生成的任务
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 将深度洞察与任务存入 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # 处理完成项的划掉效果
                        final_actions = []
                        for index, row in edited_df.iterrows():
                            t = row['Task']
                            if row['Done']:
                                t = "".join([u'\u0336' + char for char in t]) + " ✅"
                            final_actions.append(f"{index+1}. {t}")
                        
                        action_string = "\n".join(final_actions)
                        
                        # 存入表格
                        sheet.append_row([
                            st.session_state.temp_tag, 
                            user_thought, 
                            action_string,
                            st.session_state.temp_res, 
                            st.session_state.raw_source
                        ])
                        st.success("✅ 存入成功！知识已归库，行动已就位。")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("请至少写一句你的想法，这是内化的第一步。")

# --- 5. 历史 ---
st.divider()
if st.checkbox("📚 查看我的历史成长库"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data, use_container_width=True)
        except:
            st.write("表格读取中...")
