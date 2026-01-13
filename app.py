import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd

# 页面配置
st.set_page_config(page_title="Kira 的碎片内化助手", layout="centered")

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
    st.success("✅ 模型：Gemini 3 Flash (ADHD 模式已开启)")
    st.info(" Eagle Analytical 专属版")

st.title("🧠 深度知识内化系统")
st.caption("AI 自动拆解任务 | ADHD 友好型清单")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书或网页复制内容粘贴到这里：", height=150)

if st.button("✨ 启动深度思考与任务拆解"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 专家级 ADHD Prompt 升级 🌟
            prompt = f"""
            你是一个针对 ADHD 人群设计的“微习惯”导师和知识整理专家。
            请对以下内容进行深度解析：

            1. **自动分类**：必须从以下 6 类中选一个：
               [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影]
            
            2. **核心总结**：提炼 3 点核心内容。

            3. **⚡️ ADHD 友好型 Action Items (原子级拆解)**：
               - 请生成 3-5 条具体的练习步骤。
               - **规则**：每一步必须极其简单，能够在 1-5 分钟内完成。
               - **示例**：不要说“练习发音”，要说“1. 模仿文中第一个单词读 3 遍；2. 对着镜子看口型。”
            
            内容如下：
            {content}
            """
            
            with st.spinner("正在进行原子级任务拆解..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.raw_source = content 
                
                # 智能分类逻辑 (适配你要求的 6 类)
                res_text = response.text
                if "英语" in res_text: st.session_state.temp_tag = "英语学习"
                elif "跳舞" in res_text or "舞蹈" in res_text: st.session_state.temp_tag = "舞蹈练习"
                elif "处事" in res_text or "职场" in res_text: st.session_state.temp_tag = "为人处事/职场"
                elif "专业" in res_text or "微生物" in res_text or "sterility" in res_text.lower(): st.session_state.temp_tag = "专业知识"
                elif "AI" in res_text or "编程" in res_text: st.session_state.temp_tag = "AI/编程"
                elif "视频" in res_text or "摄影" in res_text or "构图" in res_text: st.session_state.temp_tag = "视频/摄影"
                else: st.session_state.temp_tag = "其他"

                # --- 核心：提取 AI 生成的任务，放入可编辑表格 ---
                # 这里简单提取带有序号的行作为初始任务
                lines = response.text.split('\n')
                ai_tasks = [l.strip() for l in lines if l.strip().startswith(('1.', '2.', '3.', '4.', '5.')) and 'Action' not in l]
                if not ai_tasks: ai_tasks = ["开始第一步练习", "复习核心要点"]
                
                st.session_state.todo_df = pd.DataFrame([
                    {"Done": False, "Task": task.split('. ', 1)[-1] if '. ' in task else task} 
                    for task in ai_tasks[:5] # 最多取前5条
                ])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 确认并微调行动项", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 AI 专家分析")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的笔记与修正")
        user_thought = st.text_area("心得总结 (一句即可)：", placeholder="例如：原来在美国职场可以这么说话...", height=100)
        
        st.write("🎯 **任务拆解 (你可以手动修改、添加或直接打勾标记已完成)**")
        # 🌟 用户可以随意修改 AI 建议的任务
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        if st.button("💾 将所有内容同步到 Google Sheets"):
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
                        
                        # 存入：Category, Note, Action Item, Summary, Source
                        sheet.append_row([
                            st.session_state.temp_tag, 
                            user_thought, 
                            action_string,
                            st.session_state.temp_res, 
                            st.session_state.raw_source
                        ])
                        st.success("✅ 存入成功！记得去 Sheets 划掉它们！")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("写点心得吧，它是防止遗忘的锚点。")

# --- 5. 历史 ---
st.divider()
if st.checkbox("📚 查看我的历史成长记录"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data, use_container_width=True)
        except:
            st.write("表格读取中...")
