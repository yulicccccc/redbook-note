import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="知识内化助手", layout="centered")

with st.sidebar:
    st.title("⚙️ 设置")
    # 建议手动粘贴，或在此处填入你的 Key: AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM
    api_key_input = st.text_input("粘贴你的 Gemini Key", type="password")
    st.info("分类：AI应用 | 跳舞 | 英语")

st.title("🧠 知识内化系统")

# 1. 收集阶段
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150)

if st.button("✨ 让 AI 预总结"):
    if not api_key_input:
        st.error("请先输入 API Key！")
    elif not content:
        st.warning("内容为空")
    else:
        try:
            genai.configure(api_key=api_key_input)
            
            # 尝试直接列出可用模型进行诊断
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(f"调试信息：可用模型 {available_models}") # 帮你诊断模型权限
            
            # 优先使用 flash
            model_to_use = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else 'models/gemini-pro'
            
            model = genai.GenerativeModel(model_to_use)
            
            prompt = f"""
            你是一个知识整理专家。请阅读内容并完成：
            1. 自动分类：[AI应用, 跳舞, 职场英语, 其他]
            2. 提炼核心大纲。
            3. 给出1个行动建议。
            内容：{content}
            """
            
            with st.spinner(f"正在使用 {model_to_use} 解析..."):
                response = model.generate_content(prompt)
                st.session_state.temp_res = response.text
                st.session_state.temp_tag = "已分类" 
        except Exception as e:
            st.error(f"❌ 调用彻底失败: {str(e)}")
            st.info("排查建议：1. 检查 Google Cloud 是否开启了 Generative Language API。2. 确认 Key 是否有误。")

# 2. 内化阶段 (保持不变)
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    st.markdown(st.session_state.temp_res)
    user_thought = st.text_area("✍️ 我的内化笔记：", placeholder="写下你的理解...")
    
    if st.button("💾 确认入库"):
        if user_thought:
            if 'db' not in st.session_state: st.session_state.db = []
            st.session_state.db.append({"note": user_thought, "source": st.session_state.temp_res})
            st.success("入库成功！")
            del st.session_state.temp_res
            st.rerun()

# 3. 库预览 (保持不变)
if 'db' in st.session_state and len(st.session_state.db) > 0:
    st.divider()
    for item in reversed(st.session_state.db):
        with st.expander(f"已存：{item['note'][:15]}..."):
            st.write(item['note'])
