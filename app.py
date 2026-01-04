import streamlit as st
from openai import OpenAI
import json
import io
import zipfile

# ==========================================
# 0. 全局配置 & 强力初始化 (绝不漏掉变量)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "pipe_idea": "", "pipe_cheat": "", "pipe_level": "", "pipe_char": "", "pipe_outline": "",
        "codex": {}, "scrap_yard": [], "mimic_analysis": "",
        "logged_in": False, "first_visit": True,
        # 全局五维参数
        "p_type": "玄幻爽文", "p_pov": "第三人称", "p_pace": "🚀 爽文快节奏",
        "p_tone": "😐 严肃正剧", "p_focus": "⚖️ 均衡模式", "p_hook": False,
        "p_word_limit": 800, "p_burst": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (极光背景 + 汉化补丁)
# ==========================================
st.markdown("""
<style>
    /* 1. 动态渐变背景 */
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .stApp {
        background: linear-gradient(-45deg, #f3f4f6, #e0e7ff, #d1fae5, #fef3c7);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }

    /* 2. 强力汉化补丁 */
    [data-testid='stFileUploader'] section::after {
        content: "📄 点击或拖拽上传 TXT 文档 (自动分析)";
        color: #4f46e5; font-weight: bold; display: block; text-align: center; padding: 10px;
    }
    [data-testid='stFileUploader'] section > input + div { display: none !important; }
    [data-testid='stFileUploader'] small { display: none; }

    /* 3. 登录火箭呼吸动画 */
    @keyframes breathe {
        0% { transform: scale(1); filter: drop-shadow(0 0 5px #3b82f6); }
        50% { transform: scale(1.1); filter: drop-shadow(0 0 20px #3b82f6); }
        100% { transform: scale(1); filter: drop-shadow(0 0 5px #3b82f6); }
    }
    .rocket-logo {
        font-size: 100px; text-align: center; margin-bottom: 20px;
        animation: breathe 3s infinite ease-in-out;
    }

    /* 4. 磨砂卡片 */
    .glass-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        padding: 40px; border-radius: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.5);
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #4f46e5 0%, #3b82f6 100%);
        color: white !important; border-radius: 8px; font-weight: 600;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (火箭回归 & 密钥修复)
# ==========================================
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><div class='rocket-logo'>🚀</div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>创世笔 GENESIS</h2>", unsafe_allow_html=True)
        with st.form("login"):
            user_input = st.text_input("用户名", placeholder="任意用户名")
            pwd_input = st.text_input("通行密钥", type="password", placeholder="请输入 666")
            if st.form_submit_button("发射并启动 🚀", use_container_width=True):
                # 修复逻辑：只要密码对就行
                if pwd_input == "666":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("密钥错误，请输入 666")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. 侧边栏 (功能全集)
# ==========================================
with st.sidebar:
    st.markdown("### 🚀 创世笔 `Ultimate`")
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: st.error("请配置 API Key"); st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 全局参数面板
    with st.expander("⚙️ 写作参数 (五维控制)", expanded=True):
        st.session_state["p_type"] = st.text_input("小说类型", st.session_state["p_type"])
        st.session_state["p_pov"] = st.selectbox("视角", ["第三人称", "第一人称", "上帝视角"])
        st.session_state["p_focus"] = st.selectbox("侧重", ["⚖️ 均衡模式", "🗣️ 对话流", "🖼️ 描写流", "🧠 心理流"])
        st.session_state["p_pace"] = st.selectbox("节奏", ["🚀 爽文快奏", "🐢 慢热铺垫"])
        st.session_state["p_tone"] = st.selectbox("文风", ["😐 严肃", "🤣 幽默", "🖤 暗黑"])
        st.session_state["p_word_limit"] = st.number_input("单词生成字数", 100, 5000, 800)
        st.session_state["p_hook"] = st.toggle("🎣 结尾强制钩子")
        st.session_state["p_burst"] = st.toggle("强力扩写", value=True)

    # 灵感工具
    with st.expander("🎲 灵感工具箱"):
        t_t1, t_t2 = st.tabs(["起名器", "命运卡"])
        with t_t1:
            nt = st.selectbox("起名类型", ["人名", "宗门", "功法", "地名"])
            if st.button("随机生成名字"):
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"生成5个{st.session_state['p_type']}风格的{nt}"}])
                st.code(r.choices[0].message.content)
        with t_t2:
            if st.button("🃏 抽一张剧情卡"):
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":"给一个剧情转折灵感"}])
                st.info(r.choices[0].message.content)

    # 档案室 (回归！)
    with st.expander("📂 档案室 (导入/文风)"):
        t_a1, t_a2 = st.tabs(["导入旧稿", "文风克隆"])
        with t_a1:
            up_f = st.file_uploader("传TXT续写", type=["txt"])
            if up_f and st.button("确认导入"):
                c = up_f.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"读取旧稿：\n{c}"})
                st.success("导入成功")
        with t_a2:
            up_s = st.file_uploader("传样本学习", type=["txt"])
            if up_s and st.button("分析文风"):
                sample = up_s.getvalue().decode("utf-8")[:1000]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风：{sample}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("已学习文风")

    # 设定/废稿/章节
    with st.expander("📕 设定/🗑️ 废稿"):
        t_s1, t_s2 = st.tabs(["设定", "废稿"])
        with t_s1:
            k = st.text_input("词条"); v = st.text_input("描述")
            if st.button("➕"): st.session_state["codex"][k]=v
            st.write(st.session_state["codex"])
        with t_s2:
            sc = st.text_area("暂存"); 
            if st.button("📥"): st.session_state["scrap_yard"].append(sc)
            for i, x in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", x, height=60, key=f"s_{i}")

    st.divider()
    curr_c = st.number_input("跳转章", min_value=1, value=st.session_state.current_chapter)
    if curr_c != st.session_state.current_chapter:
        if curr_c not in st.session_state.chapters: st.session_state.chapters[curr_c] = []
        st.session_state.current_chapter = curr_c
        st.rerun()
    if st.button("⏪ 撤销上一步"):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.rerun()

# ==========================================
# 4. 主工作区
# ==========================================
if st.session_state["first_visit"]:
    st.markdown("<br><h2 style='text-align:center;'>🖋️ 欢迎使用创世笔 Ultimate 版</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>所有功能已大满贯回归。请在左侧设置参数，开始创作。</p>", unsafe_allow_html=True)
    if st.button("立刻进入工作室", use_container_width=True): st.session_state["first_visit"] = False; st.rerun()
    st.stop()

tab_w, tab_p, tab_t, tab_e = st.tabs(["✍️ 沉浸写作", "🚀 流水线 (5步)", "🔮 灵感外挂", "💾 发布控制"])

# --- TAB 1: 写作 ---
with tab_w:
    p = st.session_state
    ctx = f"类型：{p['p_type']}。视角：{p['p_pov']}。文风：{p['p_tone']}。侧重：{p['p_focus']}。"
    if p["p_hook"]: ctx += "【结尾强制留悬念】。"
    if p["mimic_analysis"]: ctx += f"【文风模仿】{p['mimic_analysis']}。"
    if p["codex"]: ctx += f"【已存设定】{str(p['codex'])}。"
    
    sys_p = f"你是由DeepSeek驱动的网文大神。{ctx}\n字数目标：{p['p_word_limit']}。{'【强力扩写】注重细节描述。' if p['p_burst'] else ''}\n禁止客套，直接输出正文。"

    container = st.container(height=500)
    history = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        for msg in history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "✒️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 快捷精修
    with st.expander("🛠️ 章节体检与精修"):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🩺 章节体检报告"):
                full_t = "".join([m["content"] for m in history if m["role"]=="assistant"])
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"体检：{full_t}"}])
                st.info(r.choices[0].message.content)
        with c2:
            req_f = st.text_input("重写要求")
            if st.button("💥 推翻重写"):
                history.append({"role":"user", "content":f"重写：{req_f}"})
                with container:
                    with st.chat_message("assistant", avatar="✒️"):
                        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                        response = st.write_stream(stream)
                        history.append({"role":"assistant", "content":response})

    st.divider()
    ci, cb = st.columns([5, 1])
    with ci: manual = st.text_input("💡 剧情微操", placeholder="导演指令...")
    with cb:
        st.write(""); st.write("")
        if st.button("🔄 继续写", use_container_width=True):
            p_t = f"接着写。{'注意：'+manual if manual else ''}"
            history.append({"role":"user", "content":p_t})
            with container:
                with st.chat_message("assistant", avatar="✒️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                    response = st.write_stream(stream)
                    history.append({"role":"assistant", "content":response})

    if prompt := st.chat_input("输入新剧情..."):
        history.append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="✒️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                response = st.write_stream(stream)
                history.append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 ---
with tab_p:
    st.info("5步流水线模式")
    planner = "你是一个网文策划，只写设定，字数300以内。"
    with st.expander("Step 1: 脑洞"):
        idea = st.text_input("点子")
        if st.button("✨ 生成"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"点子：{idea}"}])
            st.session_state["pipe_idea"] = st.write(r.choices[0].message.content)
    with st.expander("Step 2: 金手指"):
        if st.button("💍 设计"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"设计挂：{st.session_state['pipe_idea']}"}])
            st.session_state["pipe_cheat"] = st.write(r.choices[0].message.content)
    with st.expander("Step 3: 世界/等级"):
        if st.button("📈 铺设"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"设计世界等级：{st.session_state['p_type']}"}])
            st.session_state["pipe_level"] = st.write(r.choices[0].message.content)
    with st.expander("Step 4: 人设"):
        if st.button("👥 生成"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"生成人设：{st.session_state['pipe_idea']}"}])
            st.session_state["pipe_char"] = st.write(r.choices[0].message.content)
    with st.expander("Step 5: 大纲"):
        if st.button("📜 生成"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":"写大纲"}])
            st.session_state["pipe_outline"] = st.write(r.choices[0].message.content)

# --- TAB 3: 外挂 ---
with tab_t:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎬 万能场面")
        stype = st.selectbox("类型", ["打斗", "感情", "装逼"])
        sdesc = st.text_input("描述")
        if st.button("生成"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"写描写：{sdesc}"}])
            st.write(r.choices[0].message.content)
    with c2:
        st.markdown("#### 📟 系统面板")
        stxt = st.text_input("内容")
        if st.button("生成面板"):
            st.markdown(f"<div style='background:#f1f3f5; padding:15px; border-left:5px solid #d4af37;'>【系统】⚡ {stxt}</div>", unsafe_allow_html=True)

# --- TAB 4: 导出 ---
with tab_e:
    at = ""
    for ch, msgs in st.session_state["chapters"].items():
        t = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        at += f"\n\n### 第 {ch} 章 ###\n\n{t}"
    cl = at.replace("**", "").replace("##", "")
    st.download_button("📥 导出纯净TXT", cl, "novel.txt")
    if st.button("📦 分章 ZIP"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                c = "".join([m["content"] for m in msgs if m["role"]=="assistant"]).replace("**","")
                z.writestr(f"Chapter_{ch}.txt", c)
        st.download_button("📥 下载 ZIP包", buf.getvalue(), "novel.zip", mime="application/zip")