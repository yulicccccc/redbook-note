import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# 页面配置 (手机优化)
st.set_page_config(page_title="Kira的大脑外挂", layout="centered", page_icon="🧠")

# --- 1. 连接 Google Sheets (只用于存，不消耗 API) ---
@st.cache_resource
def connect_to_sheet():
    try:
        if "gcp_json" in st.secrets:
            json_str = st.secrets["gcp_json"]
            creds_dict = json.loads(json_str)
            gc = gspread.service_account_from_dict(creds_dict)
            sh = gc.open("My_Knowledge_Base")
            return sh.sheet1
        return None
    except Exception as e:
        return None

# 主标题
st.title("🧠 Kira's Prompt Launcher")
st.caption("指令生成器 | 免 API | 无限深聊")

# --- 2. 录入素材 ---
st.header("1. 喂入素材", divider="rainbow")
st.info("💡 如果是图片，请直接去 Gemini 网页版上传，这里只生成指令。")
content_text = st.text_area("📝 粘贴链接/文字：", height=100, placeholder="把想学的东西贴这里...")

# --- 3. 生成完美指令 (Prompt Engine) ---
# 这里锁死你最爱的逻辑：前三点专家深度，第四点 ADHD 原子化
expert_prompt = f"""
请你扮演我的高级知识伙伴。我是一名 PhD 背景的 Project Microbiologist，同时也是 ADHD。
请对以下内容（或我上传的图片）进行解析，严格遵守以下结构：

【第一部分：深度卡片】(专家视角，保持 PhD 级的深度逻辑)
1. **自动分类**：必须从 [跳舞, 创意摄像, 英语, AI应用, 人情世故, 学习与个人成长, 其他灵感] 中选一个。
2. **核心逻辑**：用 3 个 bullet points 提炼最有价值的信息（分析底层逻辑、构图或动作细节）。
3. **专家建议**：请基于你（知识专家）的角色，给出一个深度的、优化长远思维的洞察建议。

【第二部分：极简行动】(ADHD 教练视角)
请针对执行障碍，生成 **最多 3 个** 原子级 Action Items。
规则：
1. 极其简单（1分钟能开始）。
2. 必须具体（例如：“存下这张图到‘构图’相册”）。
格式：使用 `- [ ]` 列表。

【第三部分：深聊引导】
请在最后问我一个引导性问题，帮助我继续深入思考这个话题。

---
**我的素材内容如下：**
{content_text}
"""

if content_text:
    st.divider()
    st.header("2. 发射到 Gemini", divider="violet")
    
    # 1. 显示指令
    st.caption("👇 全选复制下面的指令框")
    st.code(expert_prompt, language="markdown")
    
    # 2. 跳转按钮
    st.link_button("🚀 打开 Gemini 网页版 (粘贴并深聊)", "https://gemini.google.com/", use_container_width=True, type="primary")

# --- 4. (可选) 聊完回来存档 ---
st.divider()
with st.expander("📥 聊完了？把精华存进仓库 (点击展开)"):
    st.caption("把 Gemini 的精彩回答贴回来，永久保存到 Google Sheets。")
    
    manual_tag = st.selectbox("分类:", ["跳舞", "创意摄像", "英语", "AI应用", "人情世故", "学习与个人成长", "其他灵感"])
    manual_note = st.text_area("我的心得/Gemini的回答:", height=150)
    
    if st.button("💾 存入表格", use_container_width=True):
        sheet = connect_to_sheet()
        if sheet:
            try:
                date_str = datetime.now().strftime("%Y-%m-%d")
                # 存入结构: Date, Category, Note, (空Action), (空Analysis), Source
                sheet.append_row([
                    date_str,
                    manual_tag, 
                    manual_note, 
                    "手动存档", 
                    "详见 Gemini 聊天记录", 
                    content_text
                ])
                st.success("🎉 已存档！")
            except Exception as e:
                st.error(f"存储失败: {e}")

# --- 5. 复习区 (Mobile 优化) ---
st.divider()
st.header("📚 NotebookLM 投喂区")
sheet = connect_to_sheet()
if sheet:
    # 简单读取，不消耗 API
    if st.button("生成本周复习文本 (Copy Block)"):
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            text_data = "# 本周知识汇总\n\n"
            for index, row in df.iterrows():
                text_data += str(row.to_dict()) + "\n---\n"
            st.code(text_data, language="markdown")
            st.caption("👆 全选复制 -> 喂给 NotebookLM")
