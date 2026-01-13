import streamlit as st
import google.generativeai as genai

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# 侧边栏
with st.sidebar:
    st.title("⚙️ 设置")
    # 建议手动粘贴 API Key
    api_key_input = st.text_input("粘贴你的 Gemini Key", type="password")
    st.info("当前可用模型：Gemini 3 / 2.5 系列")

st.title("🧠 碎片知识内化系统")
st.caption("基于最新的 Gemini 3 模型构建")

# 1. 收集阶段
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
            
            # 直接使用你列表里最先进的模型：Gemini 3 Flash
            # 如果想用最稳健的，可以换成 'gemini-2.5-flash'
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
            st.info("调试建议：尝试将代码中的 model_name 更改为 'models/gemini-2.5-flash'")

# 2. 内化阶段
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
        
        if st.button("💾 确认入库保存"):
            if user_thought:
                if 'db' not in st.session_state: st.session_state.db = []
                st.session_state.db.append({
                    "tag": st.session_state.temp_tag,
                    "note": user_thought,
                    "source": st.session_state.temp_res
                })
                st.success("入库成功！明天记得在'我的知识库'复习。")
                del st.session_state.temp_res
                st.rerun()
            else:
                st.warning("请至少写一句你的想法。")

# 3. 库预览
if 'db' in st.session_state and len(st.session_state.db) > 0:
    st.divider()
    st.header("📚 我的知识库")
    for item in reversed(st.session_state.db):
        with st.expander(f"[{item['tag']}] {item['note'][:15]}..."):
            st.write(f"**我的心得：**\n{item['note']}")
            st.divider()
            st.markdown(item['source'])
