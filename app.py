import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 强力初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "history_snapshots": [],
        # 流水线数据 (扩充为5步)
        "pipe_idea": "",
        "pipe_cheat": "", # 金手指
        "pipe_level": "", # 等级体系
        "pipe_char": "",
        "pipe_outline": "",
        # 工具数据
        "codex": {},
        "scrap_yard": [],
        "mimic_analysis": "",
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "init_done": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (CSS 魔法)
# ==========================================
st.markdown("""
<style>
    /* 1. 动态极光背景 */
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .stApp {
        background: linear-gradient(-45deg, #f3f4f6, #e0e7ff, #d1fae5, #f3f4f6);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: #1f2937;
    }
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.85); /* 半透明磨砂 */
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.5);
    }

    /* 2. 强力汉化补丁 (覆盖上传框英文) */
    [data-testid='stFileUploader'] {
        width: 100%;
    }
    [data-testid='stFileUploader'] section {
        padding: 1rem;
        background-color: #ffffff;
        border: 1px dashed #4f46e5;
    }
    [data-testid='stFileUploader'] section > input + div {
        display: none; /* 隐藏原英文 */
    }
    [data-testid='stFileUploader'] section::after {
        content: "📄 点击或拖拽上传 TXT 文档 (自动读取)";
        color: #4f46e5;
        font-weight: bold;
        display: block;
        text-align: center;
    }
    [data-testid='stFileUploader'] small {
        display: none; /* 隐藏 Limit 200MB 英文 */
    }

    /* 3. 按钮美化 */
    .stButton>button {
        background: linear-gradient(90deg, #4f46e5 0%, #3b82f6 100%);
        color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(79, 70, 229, 0.3);
    }

    /* 4. 登录页 Logo 设计 */
    .logo-container { text-align: center; margin-bottom: 2rem; }
    .logo-icon { 
        font-size: 60px; 
        background: -webkit-linear-gradient(45deg, #4f46e5, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(79, 70, 229, 0.3);
    }
    .logo-text {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 32px; font-weight: 800; color: #111827; letter-spacing: -1px;
    }
    .logo-sub { color: #6b7280; font-size: 14px; letter-spacing: 2px; text-transform: uppercase;}

    /* 5. 登录卡片 */
    .login-box {
        background: rgba(255, 255, 255, 0.9);
        padding: 40px; border-radius: 24px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.6);
    }

    /* 隐藏水印 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (品牌化设计)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            # LOGO 区域
            st.markdown("""
            <div class="logo-container">
                <div class="logo-icon">⚡</div>
                <div class="logo-text">创世笔 GENESIS</div>
                <div class="logo-sub">AI Copilot for Novelists</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 登录卡片
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            with st.form("login"):
                st.markdown("#### 👋 欢迎回来，作者大大")
                pwd = st.text_input("通行密钥", type="password", placeholder="请输入密钥 (666)", label_visibility="collapsed")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("🚀 启动创作引擎", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 页脚
            st.markdown("""
            <div style='text-align:center; color:#9ca3af; font-size:12px; margin-top:20px;'>
                © 2025 Genesis AI · 专为中文创作优化
            </div>
            """, unsafe_allow_html=True)
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏 (极简折叠)
# ==========================================
with st.sidebar:
    # 顶部品牌
    st.markdown("### ⚡ 创世笔 `Ultimate`")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    else:
        st.error("请配置 Secrets")
        st.stop()
    
    st.divider()
    
    # 仪表盘
    curr_msgs = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    words = len("".join([m["content"] for m in curr_msgs if m["role"]=="assistant"]))
    st.caption(f"🔥 今日码字目标: {st.session_state['daily_target']}")
    st.progress(min(words / st.session_state['daily_target'], 1.0))
    
    c_chap1, c_chap2 = st.columns([2, 1])
    with c_chap1:
        target_chap = st.number_input("章号", min_value=1, value=st.session_state.current_chapter)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c_chap2: st.caption("当前章节")

    if st.button("⏪ 撤销 (时光机)", use_container_width=True, help="不满刚才的生成？点我回档。"):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已撤销", icon="↩️")
            st.rerun()

    st.markdown("---")

    # 功能折叠区
    with st.expander("📂 档案室 (导入/文风)"):
        t1, t2 = st.tabs(["导入", "文风"])
        with t1:
            up_draft = st.file_uploader("TXT续写", type=["txt"], key="u_draft")
            if up_draft and st.button("确认导入"):
                c = up_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"旧稿：\n{c}"})
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":"已读取旧稿。"})
                st.success("导入成功")
                st.rerun()
        with t2:
            up_style = st.file_uploader("大神作品", type=["txt"], key="u_style")
            if up_style and st.button("学习"):
                c = up_style.getvalue().decode("utf-8")[:1000]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风：{c}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("已学习")

    with st.expander("📕 设定集"):
        k = st.text_input("词条", placeholder="如：九转金丹")
        v = st.text_input("描述", placeholder="如：起死回生")
        if st.button("➕ 录入"): st.session_state["codex"][k]=v; st.success("OK")
        st.write(st.session_state["codex"])

    with st.expander("🗑️ 废稿篓"):
        s = st.text_area("存废稿", height=60)
        if st.button("📥"): st.session_state["scrap_yard"].append(s); st.success("OK")
        for i, txt in enumerate(st.session_state["scrap_yard"]):
            st.text_area(f"#{i+1}", txt, height=60, key=f"s_{i}")

# ==========================================
# 4. 新手引导 (全屏卡片)
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br><h1 style='text-align: center;'>✨ 欢迎来到 创世笔</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>全能网文创作系统 · V3.0 Ultimate</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.info("🧠 **流水线 (Tab 2)**\n\n从脑洞到大纲，新增金手指和等级体系设计。");
    with col2: st.success("✍️ **沉浸写作 (Tab 1)**\n\n集成了聊天、精修、剧情微操。一站式创作。");
    with col3: st.warning("💾 **发布控制 (Tab 4)**\n\n一键清洗格式、分章打包 ZIP，直接发书。");
    
    if st.button("🚀 开始创作", type="primary", use_container_width=True):
        st.session_state["first_visit"] = False
        st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "🔮 灵感外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 组装 Prompt
    ctx = ""
    if st.session_state.get("pipe_char"): ctx += f"\n【角色】{st.session_state['pipe_char']}"
    if st.session_state.get("pipe_cheat"): ctx += f"\n【金手指】{st.session_state['pipe_cheat']}" # 🔥 加上了金手指
    if st.session_state.get("pipe_level"): ctx += f"\n【等级体系】{st.session_state['pipe_level']}" # 🔥 加上了等级
    if st.session_state.get("pipe_outline"): ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("mimic_analysis"): ctx += f"\n【文风】{st.session_state['mimic_analysis']}"
    if st.session_state.get("codex"): ctx += f"\n【设定集】{str(st.session_state['codex'])}"
    
    # 参数
    c_p1, c_p2 = st.columns([2, 1])
    with c_p1: novel_type = st.text_input("小说类型", "玄幻爽文", label_visibility="collapsed", placeholder="输入类型")
    with c_p2: burst = st.toggle("强力扩写", value=True)
    
    sys_p = f"你是由DeepSeek驱动的作家。类型：{novel_type}。{ctx}\n{'扩写细节。' if burst else ''}\n禁止客套。"

    # 聊天区
    container = st.container(height=450)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    with container:
        if not current_msgs: st.info("✨ 准备就绪...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # 🛠️ 精修面板
    with st.expander("🛠️ 快速精修 (润色/重写)", expanded=False):
        t1, t2 = st.tabs(["局部润色", "整章重写"])
        with t1:
            c1, c2 = st.columns(2)
            bad = c1.text_area("粘贴片段", height=80)
            req = c2.text_input("怎么改？")
            if st.button("✨ 润色"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}。要求：{req}"}], stream=True)
                st.write_stream(stream)
        with t2:
            req_full = st.text_input("重写要求")
            if st.button("💥 推翻重写"):
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"重写：{req_full}"})
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+current_msgs, stream=True)
                response = st.write_stream(stream)
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # 底部输入
    st.markdown("---")
    c_in, c_btn = st.columns([5, 1])
    with c_in:
        manual_plot = st.text_input("💡 剧情微操 (选填)", placeholder="填了就强制按这个写，不填就自动发挥...", help="导演指令")
    with c_btn:
        st.write("")
        st.write("")
        if st.button("🔄 继续写", use_container_width=True):
            p = f"接着写。注意：{manual_plot}。" if manual_plot else "接着写。"
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(p)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+current_msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    if prompt := st.chat_input("输入剧情..."):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+current_msgs, stream=True)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 (5步法) ---
with tab_pipeline:
    st.info("💡 这里的设定如果不填，AI 就会按默认标准（凡人流/普通开局）来写。")
    planner = "你是一个网文策划。只写设定，严禁写正文！字数300以内。"

    # 1. 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("核心点子")
        if st.button("✨ 生成梗"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"基于点子生成梗：{idea}"}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
    if st.session_state["pipe_idea"]: st.text_area("✅ 脑洞", st.session_state["pipe_idea"])

    # 2. 金手指 (新)
    with st.expander("Step 2: 金手指 (选填)", expanded=True):
        if st.button("💍 设计金手指"):
            p = f"基于梗：{st.session_state['pipe_idea']}。设计一个爽感强的金手指。包括功能、限制。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_cheat"] = st.write_stream(stream)
    if st.session_state["pipe_cheat"]: st.text_area("✅ 金手指", st.session_state["pipe_cheat"])

    # 3. 世界与等级 (新)
    with st.expander("Step 3: 世界/等级 (选填)", expanded=True):
        if st.button("📈 铺设世界观"):
            p = f"设计等级体系（从低到高）和势力分布。类型：{novel_type}。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_level"] = st.write_stream(stream)
    if st.session_state["pipe_level"]: st.text_area("✅ 世界设定", st.session_state["pipe_level"])

    # 4. 人设
    with st.expander("Step 4: 人设", expanded=True):
        if st.button("👥 生成人设"):
            p = f"结合金手指：{st.session_state['pipe_cheat']}。生成主角反派档案。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
    if st.session_state["pipe_char"]: st.text_area("✅ 人设", st.session_state["pipe_char"])

    # 5. 大纲
    with st.expander("Step 5: 大纲", expanded=True):
        if st.button("📜 生成细纲"):
            p = f"综合以上所有设定，生成前三章细纲。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)
    if st.session_state["pipe_outline"]: st.text_area("✅ 大纲", st.session_state["pipe_outline"])

# --- TAB 3: 外挂 ---
with tab_tools:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎬 万能场面")
        stype = st.selectbox("类型", ["打斗", "感情", "悬疑", "装逼"])
        sdesc = st.text_input("描述")
        if st.button("生成场面"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"写一段{stype}描写：{sdesc}。300字。"}], stream=True)
            st.write_stream(stream)
    with c2:
        st.markdown("#### 📟 系统面板")
        stxt = st.text_input("提示语")
        if st.button("生成面板"):
            st.markdown(f"""<div class="system-box">【系统】⚡ {stxt}</div>""", unsafe_allow_html=True)

# --- TAB 4: 发书 ---
with tab_publish:
    full_text = ""
    for ch, msgs in st.session_state["chapters"].items():
        txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        full_text += f"\n\n### 第 {ch} 章 ###\n\n{txt}"
    
    clean = full_text.replace("**", "").replace("##", "")
    st.download_button("📥 纯净TXT", clean, "novel.txt")
    
    if st.button("📦 打包ZIP"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                c = "".join([m["content"] for m in msgs if m["role"]=="assistant"]).replace("**","")
                z.writestr(f"{ch}.txt", c)
        st.download_button("📥 下载ZIP", buf.getvalue(), "chapters.zip", mime="application/zip")