import streamlit as st
import pandas as pd
import urllib.parse

# 页面配置
st.set_page_config(page_title="Kira's Prompt Factory", layout="centered")

st.title("🧠 碎片知识内化工厂")
st.caption("专家提示词自动缝合 | 免 API 模式")

# --- 1. 录入阶段 ---
st.header("1. 录入原始内容", divider="blue")
content = st.text_area("请从小红书复制文案粘贴到这里：", height=150, placeholder="粘贴内容后，下方会自动生成提示词...")

# --- 2. 提示词自动缝合 (严格遵守你的深度与原子化分离要求) ---
expert_prompt = f"""你是一个高级知识整理专家。请针对以下内容进行深度解析：

【第一部分：深度解析】
1. 自动分类：必须从 [英语学习, 舞蹈练习, 为人处事/职场, 专业知识, AI/编程, 视频/摄影] 中选一个。
2. 提炼核心知识点大纲：采用结构化列表，保持 PhD 级别的专业度与深度。
3. 专业实操建议：提供一个基于专家角色的、能优化长远思维的深度建议。

【第二部分：任务拆解】
请针对 ADHD 执行者，将上述建议拆解为 3-5 条原子级 Action Items。
规则：每一步必须极简具体（例如：对着镜子朗读文中第一句话 3 遍），确保没有任何启动阻力。

内容如下：
{content}
"""

if content:
    st.divider()
    st.header("2. 复制提示词并跳转", divider="green")
    
    st.info("💡 提示：点击下方代码框右上角的复制图标，然后点击蓝色按钮前往 Gemini。")
    
    # 🌟 显示生成的提示词，方便一键复制
    st.code(expert_prompt, language="markdown")
    
    # 🌟 增加一个跳转按键
    # 我们把链接编码，方便以后如果想直接把内容塞进 URL（虽然 Gemini 官网目前支持较复杂）
    gemini_url = "https://gemini.google.com/"
    
    col1, col2 = st.columns([1, 1])
    with col1:
        # 直接打开官网的按钮
        st.link_button("🚀 前往 Gemini 官网粘贴", gemini_url, use_container_width=True)
    
    with col2:
        st.caption("复制后在 Gemini 窗口按 Ctrl+V 即可。")

# --- 3. 手动存档区 (保留 Google Sheets 功能) ---
st.divider()
st.header("3. 手动存档 (当你在 Gemini 得到结果后)", divider="gray")
st.write("如果你在 Gemini 聊出了满意的结果，可以在这里手动存入你的 Google 表格。")

with st.expander("点击展开存档工具"):
    # 这里保留你之前的 Google Sheets 存储逻辑，方便你把 Gemini 的回答存回来
    user_thought = st.text_area("我的心得：", height=100)
    ai_output = st.text_area("Gemini 的回答：", height=150)
    
    if st.button("💾 手动存入 Google Sheets"):
        # 此处可以复用之前的 gspread 代码，如果你依然需要持久化存储
        st.warning("请确保你已经在代码中配置了 gspread 连接逻辑。")

# --- 历史回顾 ---
if st.checkbox("📚 查看历史笔记"):
    st.info("这里可以接入你之前的查看表格代码。")
