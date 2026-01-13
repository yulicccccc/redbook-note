import streamlit as st
import google.generativeai as genai
import gspread
import json

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# --- 连接 Google Sheets 的函数 (只连一次，节省资源) ---
@st.cache_resource
def connect_to_sheet():
    try:
        # 从 Secrets 保险箱里读取身份证
        json_str = st.secrets["gcp_json"]
        creds_dict = json.loads(json_str)
        
        # 登录 Google Sheets
        gc = gspread.service_account_from_dict(creds_dict)
        # 打开你的表格 (请确保表格名字叫 My_Knowledge_Base，且已分享给机器人邮箱)
        sh = gc.open("My_Knowledge_Base")
        return sh.sheet1
    except Exception as e:
        st.error(f"连接表格失败: {e}")
        st.info("请检查：1. Secrets是否配置正确？ 2. 表格是否分享给了机器人邮箱？ 3. 表格名称是否完全一致？")
        return None

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.info("数据将自动同步到 Google Sheets")

st.title("🧠 碎片知识内化系统 (云同步版)")

# 1. 收集阶段
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案：", height=150)

if st.button("✨ 让 AI 深度解析"):
    if not api_key:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash') 
            
            prompt = f"""
            你是一个学习专家。请对以下内容：
            1. 自动分类(AI应用/跳舞/职场英语/其他)
            2. 提炼核心大纲
            3. 给1个实操建议
            
            内容：{content}
            """
            with st.spinner("AI 正在解析..."):
                res = model.generate_content(prompt)
                st.session_state.temp_res = res.text
                
                # 简单分类逻辑
                if "AI" in res.text: st.session_state.temp_tag = "AI应用"
                elif "跳舞" in res.text: st.session_state.temp_tag = "跳舞"
                elif "英语" in res.text: st.session_state.temp_tag = "职场英语"
                else: st.session_state.temp_tag = "其他"

        except Exception as e:
            st.error(f"AI调用失败: {e}")

# 2. 内化阶段
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    st.caption(f"自动分类：{st.session_state.temp_tag}")
    st.markdown(st.session_state.temp_res)
    
    user_thought = st.text_area("✍️ 我的心得 (必填)：", placeholder="写下你的理解，这步最重要...")
    
    if st.button("💾 永久存入 Google Sheets"):
        if user_thought:
            sheet = connect_to_sheet()
            if sheet:
                try:
                    # 准备要存的数据：时间 (用Python生成太麻烦，交给表格自动生成吧)、分类、心得、原始总结
                    # 这里我们直接存：[分类, 心得, AI总结]
                    sheet.append_row([st.session_state.temp_tag, user_thought, st.session_state.temp_res])
                    st.success("✅ 成功！笔记已飞入你的 Google 表格！")
                    del st.session_state.temp_res
                    st.rerun()
                except Exception as e:
                    st.error(f"写入失败: {e}")
        else:
            st.warning("写点心得吧，不然过两天就忘了。")

# 3. 实时预览 (直接从表格读取)
st.divider()
st.header("📚 我的云端知识库")
if st.checkbox("加载历史笔记 (从 Google Sheets)"):
    sheet = connect_to_sheet()
    if sheet:
        # 获取所有记录
        data = sheet.get_all_records() 
        # 如果表格第一行是表头：分类, 我的心得, AI原始总结
        # get_all_records 会自动识别
        if data:
            st.dataframe(data)
        else:
            st.info("表格是空的，快去添加第一条笔记吧！")
