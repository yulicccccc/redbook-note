import streamlit as st
import google.generativeai as genai
import gspread
import json
import pandas as pd
import re
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

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
    st.title("⚙️ 控制台")
    api_key_input = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.header("📅 周报中心")
    if st.button("生成本周思维导图素材"):
        st.session_state.show_weekly = True

# 标题区
st.title("🧠 Kira 的碎片知识内化系统")
st.caption("📷 支持截图 | ⚡️ ADHD 极简执行 | 📊 NotebookLM 联动")

# --- 3. 录入阶段 (支持文本 + 图片) ---
st.header("1. 喂入素材", divider="rainbow")

# 文本输入
content_text = st.text_area("📝 粘贴文字/链接：", height=100)

# 图片输入 (新增功能!)
uploaded_file = st.file_uploader("📸 或者上传截图/照片", type=["jpg", "jpeg", "png", "webp"])

# 启动按钮
if st.button("✨ 启动大脑解析"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content_text and not uploaded_file:
        st.warning("请至少提供文字或图片！")
    else:
        try:
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-2.0-flash-exp') # 推荐用 2.0 Flash 处理图片，速度快
            
            # 准备输入内容
            inputs = []
            if content_text:
                inputs.append(content_text)
            if uploaded_file:
                # 处理图片数据
                from PIL import Image
                img = Image.open(uploaded_file)
                inputs.append(img)
                st.session_state.has_image = True
            else:
                st.session_state.has_image = False

            # 🌟 你的 7 大分类 + 极简 Prompt 🌟
            prompt = """
            你是一个懂 ADHD 的高级知识伙伴。请对输入内容（文字或图片）进行解析：

            【第一部分：深度卡片】
            1. **自动分类**：必须从以下 7 类中选一个：
               [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感]
            2. **核心逻辑**：用 3 个 bullet points 提炼最有价值的信息（如果是图，请分析构图/色彩/动作）。
            3. **专家建议**：给出一个深度的、长远视角的洞察。

            【第二部分：极简行动】
            请针对 ADHD，生成 **最多 3 个** 原子级 Action Items。
            规则：
            1. 极其简单（1分钟能开始）。
            2. 必须具体（例如：“存下这张图到‘构图’相册”）。
            3. 语气要像朋友一样轻松。
            
            格式：将任务放在 ---ACTION_START--- 和 ---ACTION_END--- 之间。
            """
            inputs.append(prompt)

            with st.spinner("正在扫描截图并提取灵感..."):
                response = model.generate_content(inputs)
                full_response = response.text
                
                # 分割内容
                main_analysis = full_response.split("【第二部分：极简行动】")[0].strip()
                action_part = re.search(r"---ACTION_START---(.*)---ACTION_END---", full_response, re.DOTALL)
                
                st.session_state.temp_res = main_analysis
                # 保存原始素材（如果是图片，存个标记）
                st.session_state.raw_source = content_text if content_text else "[图片上传]"
                
                # 智能分类提取
                st.session_state.temp_tag = "其他灵感"
                categories = ["跳舞", "创意摄像", "英语", "AI应用", "人情世故", "学习与个人成长", "其他灵感"]
                for tag in categories:
                    if tag in main_analysis:
                        st.session_state.temp_tag = tag
                        break

                # 提取极简任务
                if action_part:
                    tasks = [t.strip() for t in action_part.group(1).strip().split('\n') if t.strip()]
                    clean_tasks = [re.sub(r'^\d+\.\s*', '', t) for t in tasks]
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": t} for t in clean_tasks])
                else:
                    st.session_state.todo_df = pd.DataFrame([{"Done": False, "Task": "深呼吸，看一遍就好"}])

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")

# --- 4. 内化与确认 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 确认与行动", divider="violet")
    
    col1, col2 = st.columns([1, 1.2])
    with col1:
        st.subheader("🧐 深度分析")
        st.info(f"📂 分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✅ 极简清单 (Max 3)")
        st.caption("Check Point: 这些任务看起来累吗？如果不顺眼，直接改掉！")
        edited_df = st.data_editor(
            st.session_state.todo_df,
            num_rows="dynamic",
            use_container_width=True,
            key="action_editor"
        )
        
        # 存档区
        st.write("---")
        user_thought = st.text_area("💭 此时此刻的想法 (选填):", height=80)
        
        if st.button("💾 存入知识库"):
            sheet = connect_to_sheet()
            if sheet:
                try:
                    # 处理任务格式
                    final_actions = []
                    for index, row in edited_df.iterrows():
                        t = row['Task']
                        if row['Done']:
                            t = "".join([u'\u0336' + char for char in t]) + " ✅"
                        final_actions.append(f"{index+1}. {t}")
                    action_string = "\n".join(final_actions)
                    
                    # 获取当前日期
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # 存入: Date, Category, Note, Actions, Analysis, Source
                    sheet.append_row([
                        date_str,
                        st.session_state.temp_tag, 
                        user_thought, 
                        action_string,
                        st.session_state.temp_res, 
                        st.session_state.raw_source
                    ])
                    st.success("🎉 存入成功！去忙别的吧！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")

# --- 5. 周报生成器 (NotebookLM 联动) ---
if st.session_state.get("show_weekly"):
    st.divider()
    st.header("📊 本周知识整合 (For NotebookLM)", divider="orange")
    sheet = connect_to_sheet()
    if sheet and api_key_input:
        with st.spinner("正在把这一周的碎片缝合成知识体系..."):
            # 1. 读取数据
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 2. 简单转成文本供 AI 分析
            # 假设第一列是日期，如果不是，请确保表格里有日期列
            # 这里简单处理：直接把所有数据丢给 AI 整理
            raw_data_str = df.tail(20).to_string() # 取最近 20 条，防止 token 爆炸
            
            genai.configure(api_key=api_key_input)
            model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
            
            weekly_prompt = f"""
            你是一个知识整合专家。以下是我最近记录的碎片知识笔记（表格数据）。
            
            请帮我按以下 7 个分类进行归纳总结：
            [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感]
            
            要求：
            1. 请输出一个 **Markdown 格式的思维导图大纲**。
            2. 找出这些碎片知识之间的**潜在联系**（比如：跳舞的节奏感是否对英语语调有帮助？）。
            3. 输出格式要非常清晰，适合我直接复制到 NotebookLM 里生成音频解读。
            
            数据如下：
            {raw_data_str}
            """
            
            report = model.generate_content(weekly_prompt).text
            st.markdown(report)
            st.info("💡 提示：点击右上角复制，把这段话发给 NotebookLM，让它给你讲一遍！")
            
            if st.button("关闭周报"):
                st.session_state.show_weekly = False
                st.rerun()
    else:
        st.warning("需要连接表格且输入 API Key 才能生成周报哦。")
