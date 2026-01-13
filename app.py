import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 1. 连接 Google Sheets (诊断版) ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 1. 尝试读取 Secrets
        if "gcp_json" not in st.secrets:
            st.error("❌ 错误：在 Secrets 里找不到 'gcp_json' 这个名字。请检查 Secrets 格式。")
            return None
            
        json_str = st.secrets["gcp_json"]
        creds_dict = json.loads(json_str)
        gc = gspread.service_account_from_dict(creds_dict)
        
        # 2. 尝试打开表格
        sh = gc.open("My_Knowledge_Base")
        return sh.sheet1
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("❌ 错误：找不到表格！请检查：1.表格名字是不是严格叫 'My_Knowledge_Base'？ 2.是否点击 Share 把表格分享给了机器人邮箱？")
        return None
    except json.JSONDecodeError:
        st.error("❌ 错误：Secrets 里的 JSON 格式不对。是不是少复制了括号，或者没有用三个单引号包裹？")
        return None
    except Exception as e:
        # 打印其他所有未知错误
        st.error(f"❌ 连接失败，详细报错: {e}")
        return None

# --- 2. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key_input = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.info("当前可用模型：Gemini 3 Flash Preview")

st.title("🧠 碎片知识内化系统")
st.caption("诊断模式：正在检查 Google Sheets 连接...")

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
            model_name = 'models/gemini-3-flash-preview' 
            model = genai.GenerativeModel(model_name)
            
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

# --- 4. 内化阶段 ---
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
        
        # 👇 这里会触发连接检查
        if st.button("💾 永久存入 Google Sheets"):
            if user_thought:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                        st.success("✅ 成功！连接正常，笔记已保存！")
                        del st.session_state.temp_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
            else:
                st.warning("请至少写一句你的想法。")

# --- 5. 历史回顾 ---
st.divider()
if st.checkbox("📚 查看 Google Sheets 里的历史笔记"):
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            st.dataframe(data)
        except:
            st.write("暂无数据")
