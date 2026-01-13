import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 1. 连接 Google Sheets 的函数 (新增) ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 从 Secrets 读取配置
        json_str = st.secrets["gcp_json"]
        creds_dict = json.loads(json_str)
        gc = gspread.service_account_from_dict(creds_dict)
        # ⚠️ 确保你的表格名字叫 My_Knowledge_Base
        sh = gc.open("My_Knowledge_Base")
        return sh.sheet1
    except Exception as e:
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key_input = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    # 这里保留你喜欢的提示
    st.info("当前可用模型：Gemini 3 Flash Preview")

st.title("🧠 碎片知识内化系统")
st.caption("基于最新的 Gemini 3 模型构建 + 云端存储")

# --- 3. 收集阶段 ---
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
            
            # ✅ 锁定你最喜欢的模型：Gemini 3 Flash Preview
            model_name = 'models/gemini-3-flash-preview' 
            model = genai.GenerativeModel(model_name)
            
            # ✅ 锁定你最喜欢的提示词 (原封不动)
            prompt = f"""
            你是一个高级知识整理专家。请针对以下内容进行深度解析：
            1. 自动分类：从[AI应用, 跳舞, 职场英语, 其他]中选一个。
            2. 提炼核心知识点大纲（采用结构化列表）。
            3. 提供一个基于你角色的专业实操建议。
            
            内容如下：
            {content}
            """
            
            with st.spinner(f"正在调用 {model_name} 进行思考..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                
                # 简单逻辑标记
                st.session_state.temp_tag = "智能分类中"
                if "AI" in response.text: st.session_state.temp_tag = "AI应用"
                elif "跳舞" in response.text: st.session_state.temp_tag = "跳舞"
                elif "英语" in response.text: st.session_state.temp_tag = "职场英语"

        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")
            st.info("调试建议：尝试将代码中的 model_name 更改为 'models/gemini-2.5-flash'")

# --- 4. 内化阶段 (已增加存储功能) ---
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🤖 AI 提炼")
        st.info(f"标签预测：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的内化笔记")
        user_thought = st.text_area("用你自己的话总结（必填）：", 
                                  placeholder="作为舞蹈老师/AI学习者，你打算怎么用这个？",
                                  height=250)
        
        # 👇 这里改成了存入 Google Sheets
        if st.button("💾 永久存入 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # 写入：[分类, 心得, AI原文]
                        sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                        st.success("✅ 成功！笔记已飞入 Google 表格！")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
                else:
                    st.error("无法连接表格，请检查 Secrets 配置。")
            else:
                st.warning("请至少写一句你的想法。")

# --- 5. 历史回顾 (从表格读取) ---
st.divider()
if st.checkbox("📚 查看 Google Sheets 里的历史笔记"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                st.dataframe(data)
            else:
                st.info("表格还没数据，快去存第一条！")
        except:
            st.write("暂无数据")
