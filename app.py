import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 1. 连接 Google Sheets (保留云存储) ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 从 Secrets 读取配置
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
    # 🌟 这里的状态栏更新了
    st.info("🚀 已启用：Gemini 3.0 Flash (最新一代)")

st.title("🧠 碎片知识内化系统 (V3版)")
st.caption("由 Gemini 3.0 驱动 | 专家级风控建议")

# --- 3. 收集阶段 ---
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("✨ 让 Gemini 3 深度解析"):
    if not api_key:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # 🌟 核心修改：切换到你列表里的 Gemini 3 Flash Preview
            # 这是目前理论上最强且免费的模型
            model = genai.GenerativeModel('models/gemini-3-flash-preview')
            
            # 🌟 灵魂提示词 (Prompt)：
            # 保留了你最喜欢的 "Checkpoints" 和 "审批点" 逻辑
            prompt = f"""
            你是一个拥有 20 年经验的资深技能导师和流程优化专家。请深度解析以下内容。
            
            请严格按以下结构输出（不要说废话）：
            
            1. **自动分类**：从 [AI应用, 跳舞, 职场英语, 其他] 中选一个。
            
            2. **核心逻辑拆解**：用结构化列表还原内容骨架。
            
            3. **⚡️ 关键控制点 (Critical Checkpoints)**：
               * (这是最重要的一点) 请指出在这个流程/动作中，**最容易出错的环节**在哪里？
               * 我们需要在哪里设置一个**“自我检查点”**或**“审批确认点”**，以确保结果不走样？
            
            4. **✅ 下一步实操建议**：基于你的专家视角，给出一个马上能做的行动指令。
            
            内容如下：
            {content}
            """
            
            with st.spinner("Gemini 3 正在进行深度推理..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                
                # 智能分类逻辑
                if "AI" in response.text: st.session_state.temp_tag = "AI应用"
                elif "跳舞" in response.text: st.session_state.temp_tag = "跳舞"
                elif "英语" in response.text: st.session_state.temp_tag = "职场英语"
                else: st.session_state.temp_tag = "其他"

        except Exception as e:
            st.error(f"调用失败: {e}")
            st.info("如果 Gemini 3 也不稳定，请把代码里的模型名改回 'models/gemini-2.5-flash'")

# --- 4. 内化阶段 ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    st.info(f"🏷️ 分类：{st.session_state.temp_tag}")
    st.markdown(st.session_state.temp_res)
    
    user_thought = st.text_area("✍️ 我的内化笔记：", 
                              placeholder="针对 AI 提出的'关键控制点'，你打算怎么调整你的习惯？",
                              height=200)
    
    if st.button("💾 永久存入 Google Sheets"):
        if user_thought:
            sheet = connect_to_sheet()
            if sheet:
                try:
                    # 存入表格
                    sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                    st.success("✅ 笔记已飞入云端表格！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")
            else:
                st.error("表格连接失败，请检查 Secrets 配置。")
        else:
            st.warning("写点心得吧，哪怕只有一句。")

# --- 5. 历史回顾 ---
st.divider()
if st.checkbox("📚 查看历史笔记"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                st.dataframe(data)
            else:
                st.info("暂无数据")
        except:
            st.write("暂无数据")
