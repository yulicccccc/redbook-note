import streamlit as st
import google.generativeai as genai

# 页面配置
st.set_page_config(page_title="知识内化助手", layout="centered")

# 侧边栏：配置 API Key
with st.sidebar:
    st.title("⚙️ 设置")
    # 为了保护隐私，建议你在网页侧边栏手动粘贴 API Key
    api_key_input = "AIzaSyAaA3gvPJMHb_DKk4Dew7Jj9PwrU0hBlcM"
    st.info("分类标签：AI应用 | 跳舞 | 职场英语")

st.title("🧠 碎片知识内化系统")
st.caption("把碎片化的内容，通过 AI 提炼和自我总结，变成长期记忆。")

# 第一阶段：收集
st.header("1. 录入内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150, placeholder="粘贴文案...")

if st.button("✨ 让 AI 预总结"):
    if not api_key_input:
        st.error("请先在左侧输入 API Key！")
    elif not content:
        st.warning("内容不能为空")
    else:
        try:
            # 1. 配置 API
            genai.configure(api_key=api_key_input)
            
            # 2. 尝试使用多种模型别名，增加兼容性
            model_names = ['gemini-1.5-flash', 'gemini-pro']
            success = False
            
            with st.spinner("AI 正在解析中..."):
                for name in model_names:
                    try:
                        model = genai.GenerativeModel(name)
                        
                        prompt = f"""
                        你是一个知识内化专家。请阅读以下内容，并完成：
                        1. 自动分类：从[AI应用, 跳舞, 职场英语, 其他]中选一个。
                        2. 提炼核心知识点大纲（3-5点）。
                        3. 写出一个'行动建议'：告诉用户明天可以怎么用这个知识。
                        
                        内容如下：
                        {content}
                        """
                        
                        response = model.generate_content(prompt)
                        st.session_state.temp_res = response.text
                        
                        # 简单的分类逻辑
                        if "AI" in response.text: st.session_state.temp_tag = "AI应用"
                        elif "跳舞" in response.text: st.session_state.temp_tag = "跳舞"
                        elif "英语" in response.text: st.session_state.temp_tag = "职场英语"
                        else: st.session_state.temp_tag = "其他"
                        
                        success = True
                        break # 如果成功就跳出循环
                    except Exception:
                        continue
                
                if not success:
                    st.error("所有模型调用均失败，请检查 API Key 权限或稍后再试。")

        except Exception as e:
            st.error(f"发生错误: {str(e)}")

# 第二阶段：理解 & 吸收
if "temp_res" in st.session_state:
    st.divider()
    st.header("2. 理解与吸收", divider="green")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🤖 AI 预总结")
        st.info(f"分类：{st.session_state.temp_tag}")
        st.markdown(st.session_state.temp_res)
    
    with col2:
        st.subheader("✍️ 我的内化笔记")
        user_thought = st.text_area("【核心环节】用你自己的话总结一下：", 
                                  placeholder="写下你对这个知识的理解，或者你打算怎么用它...",
                                  height=250)
        
        if st.button("💾 确认入库保存"):
            if user_thought:
                if 'db' not in st.session_state: st.session_state.db = []
                st.session_state.db.append({
                    "tag": st.session_state.temp_tag,
                    "note": user_thought,
                    "source": st.session_state.temp_res
                })
                st.success("入库成功！多复习才能不忘。")
                del st.session_state.temp_res
                st.rerun()
            else:
                st.warning("请写下一句你的总结。")

# 预览库
if 'db' in st.session_state and len(st.session_state.db) > 0:
    st.divider()
    st.header("📚 我的知识库 (预览)")
    for item in reversed(st.session_state.db):
        with st.expander(f"[{item['tag']}] {item['note'][:15]}..."):
            st.write(f"**我的心得：**\n{item['note']}")
            st.divider()
            st.write("**原始 AI 总结：**")
            st.markdown(item['source'])
