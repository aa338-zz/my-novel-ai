import streamlit as st
from openai import OpenAI
import json
import io
import zipfile

# ==========================================
# 0. 全局配置 & 强力初始化
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
        # 流水线数据
        "pipe_idea": "", "pipe_cheat": "", "pipe_level": "", "pipe_char": "", "pipe_outline": "",
        # 工具与设定
        "codex": {}, "scrap_yard": [], "mimic_analysis": "",
        "logged_in": False, "first_visit": True,
        # 全局参数 (五维控制)
        "p_type": "玄幻爽文", "p_pov": "第三人称", "p_pace": "🚀 爽文快节奏",
        "p_tone": "😐 严肃正剧", "p_focus": "⚖️ 均衡模式", "p_hook": False,
        "p_word_limit": 800, "p_burst": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (方案B: 羽毛笔 + 纯净米白)
# ==========================================
st.markdown("""
<style>
    /* 基础配色 */
    .stApp { background-color: #fdfbf7; color: #2c1e12; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #efebe9; }

    /* 强力汉化补丁 */
    [data-testid='stFileUploader'] section { background-color: #fcfcfc; border: 1px dashed #b0a8a0; }
    [data-testid='stFileUploader'] section > input + div { display: none !important; }
    [data-testid='stFileUploader'] section::after { content: "📄 点击上传本地 TXT"; color: #8c7b70; display: block; text-align: center; padding: 10px; }
    [data-testid='stFileUploader'] small { display: none; }

    /* 按钮美化 */
    .stButton>button {
        background-color: #2c3e50; color: #fdfbf7 !important; 
        border-radius: 4px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
    }
    .stButton>button:hover { background-color: #1a252f; transform: translateY(-1px); }
    
    /* Logo 方案 B */
    .logo-container { text-align: center; margin-bottom: 2.5rem; }
    .logo-icon { font-size: 50px; background: -webkit-linear-gradient(45deg, #d4af37, #2c3e50); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .logo-text { font-family: 'Times New Roman', serif; font-size: 36px; font-weight: bold; color: #2c3e50; margin-top: -10px; }
    
    /* 磨砂登录卡片 */
    .login-box { background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #efebe9; }
    
    /* 诊断报告样式 */
    .diag-box { background-color: #f1f3f5; border-left: 5px solid #2c3e50; padding: 15px; border-radius: 4px; font-family: sans-serif; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (方案B Logo)
# ==========================================
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><div class='logo-container'><div class='logo-icon'>✒️</div><div class='logo-text'>Genesis 创世笔</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        with st.form("login"):
            pwd = st.text_input("通行密钥", type="password", placeholder="666", label_visibility="collapsed")
            if st.form_submit_button("提笔创作", use_container_width=True):
                if pwd == "666": st.session_state["logged_in"] = True; st.rerun()
                else: st.error("密钥错误")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. 侧边栏：全局参数与灵感工具
# ==========================================
with st.sidebar:
    st.markdown("### ✒️ 创世笔 `Ultimate`")
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: st.error("请配置 API Key"); st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # --- ⚙️ 全局参数 (五维控制) ---
    with st.expander("⚙️ 全局写作参数", expanded=True):
        st.session_state["p_type"] = st.text_input("小说类型", st.session_state["p_type"])
        st.session_state["p_pov"] = st.selectbox("叙事视角", ["第三人称", "第一人称", "女主视角", "男主视角"])
        st.session_state["p_focus"] = st.selectbox("描写侧重", ["⚖️ 均衡模式", "🗣️ 对话流", "🖼️ 画面流", "🧠 心理流"])
        st.session_state["p_pace"] = st.selectbox("剧情节奏", ["🚀 爽文快节奏", "🐢 慢热铺垫"])
        st.session_state["p_tone"] = st.selectbox("文风基调", ["😐 严肃正剧", "🤣 幽默玩梗", "🖤 黑暗压抑", "🌸 轻松治愈"])
        st.session_state["p_hook"] = st.toggle("🎣 结尾强制留钩子 (Cliffhanger)")
        st.session_state["p_word_limit"] = st.number_input("单词生成字数", 100, 5000, 800)
        st.session_state["p_burst"] = st.toggle("强力扩写", value=True)

    # --- 🎲 灵感工具箱 ---
    with st.expander("🎲 灵感工具箱"):
        t_tool1, t_tool2 = st.tabs(["起名器", "命运卡"])
        with t_tool1:
            name_type = st.selectbox("类型", ["人名", "宗门", "功法", "武器", "地名"])
            if st.button("生成名字"):
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"随机生成5个霸气的{st.session_state['p_type']}风格的{name_type}名。"}])
                st.write(r.choices[0].message.content)
        with t_tool2:
            if st.button("🃏 抽一张剧情卡"):
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"我现在写到{st.session_state['p_type']}小说卡文了，请给出一个意想不到的剧情转折或灵感，一句话即可。"}])
                st.info(r.choices[0].message.content)

    # --- 📂 档案室 (导入/文风) ---
    with st.expander("📂 档案室"):
        t_arc1, t_arc2 = st.tabs(["导入旧稿", "文风克隆"])
        with t_arc1:
            up = st.file_uploader("上传TXT", type=["txt"])
            if up and st.button("确认导入"):
                content = up.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"读取旧稿：\n{content}"})
                st.success("导入成功")
        with t_arc2:
            up_s = st.file_uploader("上传样本", type=["txt"])
            if up_s and st.button("分析文风"):
                sample = up_s.getvalue().decode("utf-8")[:1000]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风：{sample}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("学习完成")

    # --- 设定/废稿 ---
    with st.expander("📕 设定/🗑️ 废稿"):
        t_set1, t_set2 = st.tabs(["设定", "废稿"])
        with t_set1:
            k = st.text_input("词条"); v = st.text_input("描述")
            if st.button("➕"): st.session_state["codex"][k]=v
            st.write(st.session_state["codex"])
        with t_set2:
            scrap = st.text_area("暂存"); 
            if st.button("📥"): st.session_state["scrap_yard"].append(scrap)
            for i, txt in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", txt, height=60, key=f"scr_{i}")

# ==========================================
# 4. 主工作区
# ==========================================
if st.session_state["first_visit"]:
    st.markdown("<br><h2 style='text-align:center;'>🖋️ 欢迎来到创世笔工作室</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>请在左侧设置您的全局写作偏好，然后开始创作。</p>", unsafe_allow_html=True)
    if st.button("开始创作", use_container_width=True): st.session_state["first_visit"] = False; st.rerun()
    st.stop()

tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线 (5步)", "🔮 万能外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    # 核心系统指令拼接
    p = st.session_state
    ctx = f"类型：{p['p_type']}。视角：{p['p_pov']}。基调：{p['p_tone']}。节奏：{p['p_pace']}。侧重：{p['p_focus']}。"
    if p["p_hook"]: ctx += "【结尾必须留悬念】。"
    if p["mimic_analysis"]: ctx += f"【文风模仿】{p['mimic_analysis']}。"
    if p["codex"]: ctx += f"【已存设定】{str(p['codex'])}。"
    
    sys_p = f"你是由DeepSeek驱动的网文大神。{ctx}\n字数目标：{p['p_word_limit']}。{'【强力扩写】注重细节描述。' if p['p_burst'] else ''}\n禁止任何客套，直接输出正文。"

    container = st.container(height=450)
    history = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        for msg in history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "✒️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 工具合体面板
    with st.expander("🛠️ 章节精修与体检"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🩺 章节体检报告"):
                full_text = "".join([m["content"] for m in history if m["role"]=="assistant"])
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"请作为专业编辑对以下章节进行节奏、爽点、逻辑的体检报告：\n{full_text}"}])
                st.markdown(f"<div class='diag-box'>{r.choices[0].message.content}</div>", unsafe_allow_html=True)
        with col2:
            req_full = st.text_input("整章重写要求")
            if st.button("💥 推翻重写"):
                history.append({"role":"user", "content":f"按要求重写本章：{req_full}"})
                with container:
                    with st.chat_message("assistant", avatar="✒️"):
                        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                        response = st.write_stream(stream)
                        history.append({"role":"assistant", "content":response})

    # 输入与微操
    st.divider()
    c_in, c_btn = st.columns([5, 1])
    with c_in: manual = st.text_input("💡 剧情微操", placeholder="导演指令：不填则AI自动，填了则AI强制按你说的写...")
    with c_btn:
        st.write(""); st.write("")
        if st.button("🔄 继续写", use_container_width=True):
            p_text = f"接着上文写。{'注意：'+manual if manual else ''}"
            history.append({"role":"user", "content":p_text})
            with container:
                with st.chat_message("assistant", avatar="✒️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                    response = st.write_stream(stream)
                    history.append({"role":"assistant", "content":response})

    if prompt := st.chat_input("输入新剧情指令..."):
        history.append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="✒️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                response = st.write_stream(stream)
                history.append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 ---
with tab_pipeline:
    st.info(f"正在策划：{st.session_state['p_type']}。字数控制在300字以内。")
    planner = "你是一个网文策划。只写设定，不写正文。"
    
    with st.expander("Step 1: 脑洞"):
        idea = st.text_input("点子")
        if st.button("✨ 生成"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"生成梗：{idea}"}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
    
    with st.expander("Step 2: 金手指"):
        if st.button("💍 设计"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"设计金手指：{st.session_state['pipe_idea']}"}], stream=True)
            st.session_state["pipe_cheat"] = st.write_stream(stream)

    with st.expander("Step 3: 世界与等级"):
        if st.button("📈 铺设"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"设计力量体系与势力：{st.session_state['p_type']}"}], stream=True)
            st.session_state["pipe_level"] = st.write_stream(stream)

    with st.expander("Step 4: 人设"):
        if st.button("👥 生成"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"生成主角反派：{st.session_state['pipe_idea']}"}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)

    with st.expander("Step 5: 大纲"):
        if st.button("📜 生成"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":"生成前三章细纲"}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)

# --- TAB 3: 外挂与系统 ---
with tab_tools:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎬 万能场面生成")
        stype = st.selectbox("场面类型", ["⚔️ 战斗", "💖 感情", "👻 悬疑", "😎 装逼"])
        sdesc = st.text_input("描述场面")
        if st.button("生成"):
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"描写一段{stype}场面：{sdesc}"}], stream=True)
            st.write_stream(stream)
    with c2:
        st.markdown("#### 📟 系统面板")
        stxt = st.text_input("系统提示语")
        if st.button("生成"):
            st.markdown(f"<div style='background:#f1f3f5; padding:15px; border-left:5px solid #d4af37;'>【系统】⚡ {stxt}</div>", unsafe_allow_html=True)

# --- TAB 4: 发书控制台 ---
with tab_publish:
    all_text = ""
    for ch, msgs in st.session_state["chapters"].items():
        txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        all_text += f"\n\n### 第 {ch} 章 ###\n\n{txt}"
    
    clean = all_text.replace("**", "").replace("##", "")
    st.download_button("📥 导出纯净TXT", clean, "novel_clean.txt")
    
    if st.button("📦 分章打包 ZIP"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                c = "".join([m["content"] for m in msgs if m["role"]=="assistant"]).replace("**","")
                z.writestr(f"Chapter_{ch}.txt", c)
        st.download_button("📥 下载 ZIP", buf.getvalue(), "chapters.zip", mime="application/zip")