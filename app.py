import streamlit as st
import google.generativeai as genai

# 配置页面
st.set_page_config(page_title="知识内化助手", layout="centered")

# 侧边栏：配置 API Key
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.info("分类：AI应用 | 跳舞 | 职场英语")

st.title("🧠 碎片知识内化系统")
st.caption("把小红书的碎片，通过 AI 提炼和自我总结，变成长期记忆。")

# 第一阶段：收集
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150, placeholder="粘贴文案...")

if st.button("✨ 让 AI 预总结"):
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    elif not content:
        st.warning("内容不能为空")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            你是一个学习专家。请针对以下内容：
            1. 自动归类（AI应用/跳舞/职场英语/其他）。
            2. 提炼核心大纲（3-5点）。
            3. 给出1个实操建议。
            
            内容如下：
            {content}
            """
            
            with st.spinner("AI 正在解析..."):
                res = model.generate_content(prompt)
                st.session_state.temp_res = res.text
        except Exception as e:
            st.error(f"出错啦: {e}")

# 第二阶段：内化
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    st.subheader("🤖 AI 的预整理")
    st.markdown(st.session_state.temp_res)
    
    st.subheader("✍️ 我的思考笔记")
    user_thought = st.text_area("【核心环节】用你自己的话总结一下：", placeholder="写下你对这个知识的理解或应用计划...")
    
    if st.button("💾 确认存入知识库"):
        if user_thought:
            if 'db' not in st.session_state: st.session_state.db = []
            st.session_state.db.append({"note": user_thought, "source": st.session_state.temp_res})
            st.success("入库成功！多复习才能不忘。")
            del st.session_state.temp_res
            st.rerun()
        else:
            st.warning("请至少写下一句你的总结。")

# 预览库
if 'db' in st.session_state and len(st.session_state.db) > 0:
    st.divider()
    st.write("📚 我的知识库 (预览)：")
    for item in reversed(st.session_state.db):
        with st.expander(item['note'][:20] + "..."):
            st.write(f"**我的笔记：**\n{item['note']}")
            st.write("---")
            st.write("**AI 原始参考：**")
            st.markdown(item['source'])
