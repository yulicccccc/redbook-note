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
        if "gcp_json" in st.secrets:
            json_str = st.secrets["gcp_json"]
            creds_dict = json.loads(json_str)
            gc = gspread.service_account_from_dict(creds_dict)
            sh = gc.open("My_Knowledge_Base")
            return sh.sheet1
        return None
    except Exception as e:
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key_input = st.text_input("粘贴 Gemini API Key", type="password")
    st.info("模式：API 极速分析 -> 网页版深度陪聊")

st.title("🧠 碎片知识内化系统")
st.caption("专家深度分析 + 原子级任务拆解")

# --- 3. 录入阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("✨ 启动专家解析"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 你的最爱 Prompt：深度专家 + 原子执行 🌟
            prompt = f"""
            你是一个顶级知识管理专家。请对以下内容进行深度解析，严格遵守以下结构：

            【第一部分：深度分析】
            1. 自动分类：必须从 [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影] 中选一个。
            2. 提炼核心知识点大纲：用专业、严谨的结构化列表提炼内容的底层逻辑。
            3. 专业实操建议：基于专家角色，提供一个能启发深度思考或优化长远流程的建议。

            【第二部分：任务拆解】
            请针对有 ADHD 倾向的执行者，将上述建议拆解为 3-5 条原子级 Action Items。
            规则：每一步必须简单到 1 分钟内即可开始（例如：不要说“练习发音”，要说“对着镜子朗读文中第一句话 3 遍”）。
            格式：请将任务放在 ---ACTION_START--- 和 ---ACTION_END--- 标记之间。

            内容如下：
            {content}
            """
            
            with st.spinner("Gemini 正在构建思维模型..."):
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

                # 提取任务
                if action_part:
                    tasks = [t.strip() for t in action_part.group(1).strip().split('\n') if t.strip()]
                    clean_tasks = [re.sub(r'^\d+\.\s*', '', t) for t in tasks]
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": t} for t in clean_tasks])
                else:
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": "开始微量练习"}])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化与接力 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 确认与接力", divider="green")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🤖 专家分析")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("🎯 原子任务")
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        # 🌟🌟🌟 新增功能：转战 Gemini 深聊 🌟🌟🌟
        st.write("---")
        st.subheader("🚀 转战 Gemini 深聊")
        
        # 1. 自动生成“接力暗号”
        # 把所有的上下文（原文 + 刚才的分析 + 任务）打包
        current_tasks = "\n".join([f"- {row['Task']}" for i, row in edited_df.iterrows()])
        relay_prompt = f"""我正在学习这段内容：
{st.session_state.raw_source}

你刚才已经帮我分析过了，这是你的分析结果：
{st.session_state.temp_res}

这是你帮我拆解的原子任务：
{current_tasks}

请基于以上所有信息，继续跟我深入讨论。我有几个具体问题想请教你：..."""

        # 2. 显示复制框
        st.code(relay_prompt, language="text")
        st.caption("👆 点击右上角复制图标，这就带上了所有记忆！")
        
        # 3. 跳转按钮
        st.link_button("👉 前往 Gemini 网页版粘贴", "https://gemini.google.com/", use_container_width=True)

    # --- 存档功能放最后 ---
    st.divider()
    user_thought = st.text_area("心得总结 (存入表格用)：", height=100)
    
    if st.button("💾 存档至 Google Sheets"):
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
                    st.success("✅ 存档成功！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")
        else:
            st.warning("写句心得再存吧！")

# --- 5. 历史 ---
if st.checkbox("📚 查看历史"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            st.dataframe(sheet.get_all_records(), use_container_width=True)
        except:
            st.write("读取中...")
