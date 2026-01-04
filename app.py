import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="✒️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "history_snapshots": [],
        # 流水线数据
        "pipe_idea": "",
        "pipe_cheat": "", 
        "pipe_level": "", 
        "pipe_char": "",
        "pipe_outline": "",
        # 工具数据
        "codex": {},
        "scrap_yard": [],
        "mimic_analysis": "",
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "init_done": True,
        # 全局参数状态
        "global_novel_type": "玄幻爽文",
        "global_word_target": 800,
        "global_burst_mode": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (方案B: 羽毛笔 + 米白)
# ==========================================
st.markdown("""
<style>
    /* 1. 背景：高级米白 (护眼纸张感) */
    .stApp {
        background-color: #fdfbf7; 
        color: #2c1e12;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #efebe9;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }

    /* 2. 强力汉化补丁 */
    [data-testid='stFileUploader'] section {
        background-color: #fcfcfc;
        border: 1px dashed #b0a8a0;
    }
    [data-testid='stFileUploader'] section > input + div {
        display: none !important;
    }
    [data-testid='stFileUploader'] section::after {
        content: "📄 点击上传本地 TXT 文档";
        color: #8c7b70;
        font-weight: 500;
        display: block;
        text-align: center;
        padding: 10px;
    }
    [data-testid='stFileUploader'] small { display: none; }

    /* 3. 按钮美化 (墨蓝色) */
    .stButton>button {
        background-color: #2c3e50; 
        color: #fdfbf7 !important; 
        border-radius: 4px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1a252f; transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* 4. Logo 方案 B: 创世羽毛笔 */
    .logo-container { text-align: center; margin-bottom: 2.5rem; }
    .logo-icon { 
        font-size: 50px; 
        background: -webkit-linear-gradient(45deg, #d4af37, #2c3e50);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 2px 5px rgba(0,0,0,0.1);
        cursor: default;
    }
    .logo-text {
        font-family: 'Times New Roman', serif; /* 衬线体体现文学感 */
        font-size: 36px; font-weight: bold; color: #2c3e50; letter-spacing: 1px;
        margin-top: -10px;
    }
    .logo-sub { 
        color: #8c7b70; font-size: 14px; letter-spacing: 3px; 
        text-transform: uppercase; font-family: sans-serif;
    }

    /* 5. 登录卡片 (干净) */
    .login-box {
        background: #ffffff;
        padding: 40px; border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid #efebe9;
    }
    
    /* 6. 输入框美化 */
    .stTextInput>div>div>input {
        background-color: #ffffff; border: 1px solid #e0e0e0;
        color: #333;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (方案B Logo)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            # 方案 B Logo
            st.markdown("""
            <div class="logo-container">
                <div class="logo-icon">✒️</div>
                <div class="logo-text">Genesis 创世笔</div>
                <div class="logo-sub">AI Literary Assistant</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 登录卡片
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            with st.form("login"):
                st.markdown("<p style='text-align:center; color:#666;'>请输入通行密钥</p>", unsafe_allow_html=True)
                pwd = st.text_input("Key", type="password", placeholder="666", label_visibility="collapsed")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("🖋️ 提笔创作", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; margin-top:20px; color:#aaa; font-size:12px;'>© 2025 Genesis AI · 专注中文创作</div>", unsafe_allow_html=True)
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏 (功能回归！！！)
# ==========================================
with st.sidebar:
    # 顶部
    st.markdown("### ✒️ 创世笔 `Pro`")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    else:
        st.error("请配置 Secrets")
        st.stop()
    
    st.divider()
    
    # 1. 仪表盘
    curr_msgs = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    words = len("".join([m["content"] for m in curr_msgs if m["role"]=="assistant"]))
    st.caption(f"📊 今日目标: {words}/{st.session_state['daily_target']}")
    st.progress(min(words / st.session_state['daily_target'], 1.0))
    
    # 2. 章节与撤销
    c_chap1, c_chap2 = st.columns([2, 1])
    with c_chap1:
        target_chap = st.number_input("章号", min_value=1, value=st.session_state.current_chapter)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c_chap2: st.caption("当前")

    if st.button("⏪ 撤销 (时光机)", use_container_width=True, help="不满刚才的生成？点我回档。"):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已撤销", icon="↩️")
            st.rerun()

    st.markdown("---")

    # 3. 档案室 (导入/文风)
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

    # 4. 设定集
    with st.expander("📕 设定集"):
        k = st.text_input("词条", placeholder="如：九转金丹")
        v = st.text_input("描述", placeholder="如：起死回生")
        if st.button("➕ 录入"): st.session_state["codex"][k]=v; st.success("OK")
        st.write(st.session_state["codex"])

    # 5. 废稿篓
    with st.expander("🗑️ 废稿篓"):
        s = st.text_area("存废稿", height=60)
        if st.button("📥"): st.session_state["scrap_yard"].append(s); st.success("OK")
        for i, txt in enumerate(st.session_state["scrap_yard"]):
            st.text_area(f"#{i+1}", txt, height=60, key=f"s_{i}")

    st.markdown("---")
    
    # 6. 🔥🔥🔥 全局参数 (终于回来了！！！) 🔥🔥🔥
    st.markdown("#### ⚙️ 全局参数")
    st.session_state["global_novel_type"] = st.text_input("小说类型", value=st.session_state["global_novel_type"], help="例如：克苏鲁修仙、赛博朋克")
    st.session_state["global_word_target"] = st.number_input("单次字数", 100, 5000, st.session_state["global_word_target"], 100)
    st.session_state["global_burst_mode"] = st.toggle("强力扩写模式", value=st.session_state["global_burst_mode"])

# ==========================================
# 4. 新手引导
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br><h1 style='text-align: center; font-family:serif;'>Genesis 创世笔</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>功能全开 · 专注中文 · 极简高效</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.info("🧠 **流水线 (Tab 2)**\n\n五步法构建世界：脑洞、金手指、世界观、人设、大纲。");
    with col2: st.success("✍️ **沉浸写作 (Tab 1)**\n\n左侧设置好参数，这里专注于写。支持随手精修和微操。");
    with col3: st.warning("💾 **发布控制 (Tab 4)**\n\n一键清洗格式、分章打包 ZIP，直接发书。");
    
    if st.button("🖋️ 开始创作", type="primary", use_container_width=True):
        st.session_state["first_visit"] = False
        st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线 (5步)", "🔮 灵感外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 组装 Prompt (使用侧边栏的参数)
    ctx = ""
    if st.session_state.get("pipe_char"): ctx += f"\n【角色】{st.session_state['pipe_char']}"
    if st.session_state.get("pipe_cheat"): ctx += f"\n【金手指】{st.session_state['pipe_cheat']}"
    if st.session_state.get("pipe_level"): ctx += f"\n【等级体系】{st.session_state['pipe_level']}"
    if st.session_state.get("pipe_outline"): ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("mimic_analysis"): ctx += f"\n【文风】{st.session_state['mimic_analysis']}"
    if st.session_state.get("codex"): ctx += f"\n【设定集】{str(st.session_state['codex'])}"
    
    # 使用全局参数
    novel_type = st.session_state["global_novel_type"]
    word_target = st.session_state["global_word_target"]
    burst = st.session_state["global_burst_mode"]
    
    sys_p = f"你是由DeepSeek驱动的作家。类型：{novel_type}。{ctx}\n字数目标：{word_target}。{'【强力扩写】注重环境、心理、动作细节。' if burst else ''}\n禁止客套。"

    # 聊天区
    container = st.container(height=480)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    with container:
        if not current_msgs: st.info(f"✨ 准备就绪。当前类型：{novel_type}，字数目标：{word_target}。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "✒️"
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
                with st.chat_message("assistant", avatar="✒️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+current_msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    if prompt := st.chat_input("输入剧情..."):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="✒️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+current_msgs, stream=True)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 (5步法) ---
with tab_pipeline:
    st.info("💡 5步法构建。如果不填，AI 会按默认标准写。")
    planner = "你是一个网文策划。只写设定，严禁写正文！字数300以内。"

    # 1. 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("核心点子")
        if st.button("✨ 生成梗"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"基于点子生成梗：{idea}"}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
    if st.session_state["pipe_idea"]: st.text_area("✅ 脑洞", st.session_state["pipe_idea"])

    # 2. 金手指
    with st.expander("Step 2: 金手指 (选填)", expanded=True):
        if st.button("💍 设计金手指"):
            p = f"基于梗：{st.session_state['pipe_idea']}。设计一个爽感强的金手指。包括功能、限制。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_cheat"] = st.write_stream(stream)
    if st.session_state["pipe_cheat"]: st.text_area("✅ 金手指", st.session_state["pipe_cheat"])

    # 3. 世界与等级
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
            st.markdown(f"""<div class="login-box" style="padding:10px; border-left:4px solid #d4af37;">【系统】⚡ {stxt}</div>""", unsafe_allow_html=True)

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