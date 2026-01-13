import streamlit as st
import google.generativeai as genai

# 页面配置：让它在手机上看起来也舒服
st.set_page_config(page_title="小红书内化助手", layout="centered")

# 侧边栏：输入 API Key
with st.sidebar:
    st.title("⚙️ 配置中心")
    api_key = st.text_input("在这里粘贴你的 Gemini Key", type="password")
    st.divider()
    st.write("分类：AI应用 | 跳舞 | 职场英语")

st.title("🧠 碎片知识内化系统")
st.caption("第一阶段：收集 & 管理 ➡️ 第二阶段：理解 & 吸收")

# 第一阶段：收集
st.header("1. 粘贴内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("AI 预处理"):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    elif not content:
        st.warning("内容不能为空")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"你是一个学习教练。请对以下内容提取3个核心点，给出1个实操建议，并将其分类（AI应用/跳舞/职场英语/其他）：\n\n{content}"
        
        with st.spinner("AI 正在解析中..."):
            res = model.generate_content(prompt)
            st.session_state.temp_res = res.text

# 第二阶段：内化
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    st.subheader("🤖 AI 提取的骨架")
    st.markdown(st.session_state.temp_res)
    
    st.subheader("✍️ 我的内化笔记")
    user_thought = st.text_area("练习总结：你会怎么用这个知识？", placeholder="用你自己的话写下来，这步最重要！")
    
    if st.button("完成并存入数据库"):
        if 'db' not in st.session_state: st.session_state.db = []
        st.session_state.db.append({"note": user_thought, "source": st.session_state.temp_res})
        st.success("入库成功！明天记得复习。")
        del st.session_state.temp_res

# 预览已存内容
if 'db' in st.session_state:
    st.divider()
    st.write("📚 已内化的知识点：")
    for item in reversed(st.session_state.db):
        with st.expander(item['note'][:20] + "..."):
            st.write(item['note'])
