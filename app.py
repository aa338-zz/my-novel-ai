import streamlit as st
from openai import OpenAI
import json
import io
import zipfile

# ==========================================
# 0. 全局配置 & 强力初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛠️ 强力初始化：缺什么补什么，防止报错
def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "history_snapshots": [],
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_world": "",
        "pipe_outline": "",
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
# 1. 样式美化 (CSS + 动画)
# ==========================================
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    /* 按钮美化 */
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 登录页动画 */
    @keyframes breathe {
        0% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
        50% { transform: scale(1.1); opacity: 1; text-shadow: 0 0 25px #228be6, 0 0 10px #228be6; }
        100% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
    }
    .login-logo {
        font-size: 80px; text-align: center; margin-bottom: 20px;
        animation: breathe 3s infinite ease-in-out; cursor: default;
    }
    .login-card {
        background: white; padding: 40px; border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; border: 1px solid #e9ecef;
    }
    
    /* 卡片通用 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .guide-card:hover { transform: translateY(-5px); }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    .guide-desc {font-size: 14px; color: #868e96; line-height: 1.5;}

    /* 系统面板 */
    .system-box {
        background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%);
        border: 2px solid #339af0; border-radius: 8px; padding: 15px;
        color: #1864ab; font-family: 'Courier New', monospace; font-weight: bold;
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown('<div class="login-logo">⚡</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            st.markdown("<h2 style='color:#333; margin-top:0;'>创世笔 Genesis</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color:#888; font-size:14px;'>全功能 AI 写作工作台</p>", unsafe_allow_html=True)
            
            with st.form("login"):
                user = st.text_input("账号", placeholder="用户名 (任意)", label_visibility="collapsed")
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                pwd = st.text_input("密码", type="password", placeholder="请输入通行密钥 (666)", label_visibility="collapsed")
                st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
                
                if st.form_submit_button("🚀 进入工作室", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：指挥塔 (核心控制区)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    
    # API Key 配置
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎：在线 (DeepSeek)")
    else:
        # 如果没有配置 secrets，允许手动输入
        api_key = st.text_input("输入 DeepSeek API Key", type="password")
        if not api_key:
            st.warning("🔴 请输入 API Key")
            st.stop()
            
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # --- 核心数据 (常驻) ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    target = st.session_state["daily_target"]
    prog = min(current_text_len / target, 1.0)
    st.markdown(f"**🔥 今日码字** ({current_text_len} / {target})")
    st.progress(prog)
    
    # 章节跳转
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: st.caption(f"第 {st.session_state.current_chapter} 章")
    
    # 时光机
    if st.button("⏪ 撤销上一步", use_container_width=True, help="撤销最近一次 AI 生成"):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已时光倒流", icon="↩️")
            st.rerun()
        else:
            st.warning("已经是起点了")

    st.divider()

    # --- 折叠功能区 ---
    with st.expander("📂 档案室 (导入/文风)", expanded=False):
        t_imp1, t_imp2 = st.tabs(["📥 导入", "🧬 文风"])
        with t_imp1:
            uploaded_draft = st.file_uploader("传TXT续写", type=["txt"], key="draft_up")
            if uploaded_draft and st.button("📥 确认导入"):
                draft_content = uploaded_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "user", "content": f"以下是前文：\n\n{draft_content}"}
                )
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "assistant", "content": "✅ 已读取旧稿。"}
                )
                st.success(f"已导入 {len(draft_content)} 字！")
                st.rerun()
        with t_imp2:
            uploaded_style = st.file_uploader("传大神作品", type=["txt"], key="style_up")
            if uploaded_style and st.button("🧠 提取文风"):
                raw_style = uploaded_style.getvalue().decode("utf-8")[:2000]
                with st.spinner("正在解构文风..."):
                    r = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[{"role":"user","content":f"分析这段文字的文风（用词、节奏、叙事视角）：\n{raw_style}"}]
                    )
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                    st.success("文风已激活！")

    with st.expander("📕 设定集 (Codex)", expanded=False):
        new_term = st.text_input("新词条", placeholder="如：青莲地心火")
        new_desc = st.text_input("描述", placeholder="排名19的异火")
        if st.button("➕ 收录"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已收录")
        st.markdown("---")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    with st.expander("🗑️ 废稿篓 (暂存)", expanded=False):
        scrap = st.text_area("存入片段", height=60, placeholder="粘贴不要的文字...")
        if st.button("📥 丢进去"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("已保存")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")
                if st.button(f"❌ 销毁 {i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i)
                    st.rerun()

    with st.expander("🛡️ 违禁词雷达", expanded=False):
        if st.button("🔴 扫描本章"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政府"]
            txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter]])
            found = [w for w in risky if w in txt]
            if found: st.error(f"发现敏感词: {list(set(found))}")
            else: st.success("内容健康")

    # ==========================================
    # 🔥 核心增强参数 (NEW)
    # ==========================================
    st.divider()
    st.markdown("### 🧠 大脑控制台")
    
    # 1. 基础设定
    c_type1, c_type2 = st.columns(2)
    with c_type1:
        t_sel = st.selectbox("📚 类型", ["东方玄幻", "都市异能", "末世囤货", "无限流", "悬疑刑侦", "古言宫斗", "自定义"])
    with c_type2:
        # 视角选择
        perspective = st.selectbox("👁️ 视角", ["第三人称 (上帝)", "第一人称 (我)", "第二人称 (你)"], index=0)

    novel_type = st.text_input("输入具体类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel

    st.markdown("---")
    
    # 2. 进阶控制
    # 文风控制
    writing_style = st.select_slider(
        "🎭 文笔风格", 
        options=["极简白话", "轻松幽默", "正常叙事", "辞藻华丽", "暗黑深沉", "古风晦涩"], 
        value="正常叙事"
    )
    
    # 节奏控制
    pace_control = st.radio(
        "⏱️ 叙事节奏", 
        ["推进剧情 (快)", "细腻描写 (慢)", "平衡发展"], 
        index=2,
        horizontal=True
    )

    # 创意温度
    creativity = st.slider(
        "🔥 脑洞温度 (严谨 <-> 狂野)", 
        min_value=0.5, max_value=1.5, value=1.2, step=0.1,
        help="数值越高，AI 越容易产生意想不到的剧情，但也可能胡说八道。"
    )

    word_target = st.number_input("🎯 单次字数", 100, 5000, 800, 100)
    burst_mode = st.toggle("💥 强力扩写 (拒绝流水账)", value=True)


# ==========================================
# 4. 新手引导
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #228be6;'>✨ 欢迎使用 创世笔 Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #868e96;'>功能全开 · 续写神器 · 格式无忧</p><br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="guide-card"><span class="guide-icon">📂</span><div class="guide-title">设定与大纲</div><div class="guide-desc">在侧边栏配置<b>视角、文风</b>。<br>在流水线 Tab 生成大纲。</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="guide-card"><span class="guide-icon">✍️</span><div class="guide-title">沉浸写作</div><div class="guide-desc"><b>写作区</b> 是核心。<br>所有操作都在一个页面完成。</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="guide-card"><span class="guide-icon">💾</span><div class="guide-title">发布</div><div class="guide-desc"><b>发书控制台</b><br>一键打包下载。</div></div>""", unsafe_allow_html=True)

    c_center = st.columns([1, 2, 1])
    with c_center[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 开始创作！", type="primary", use_container_width=True):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "🔮 灵感外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 (已升级) ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 🟢 动态 Prompt 组装
    ctx = ""
    if st.session_state.get("pipe_char"): ctx += f"\n【角色档案】{st.session_state['pipe_char']}"
    if st.session_state.get("pipe_outline"): ctx += f"\n【当前大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("mimic_analysis"): ctx += f"\n【模仿文风】{st.session_state['mimic_analysis']}"
    if st.session_state.get("codex"): ctx += f"\n【世界观设定】{str(st.session_state['codex'])}"
    
    # 核心指令集
    style_instruction = f"使用{perspective}写作。文风要求：{writing_style}。节奏控制：{pace_control}。"
    burst_instruction = "【强力扩写模式】必须通过环境描写、心理活动、微表情来填充篇幅，禁止流水账。" if burst_mode else ""
    instruction = f"字数目标：{word_target}字。{style_instruction} {burst_instruction}"
    
    # 最终 System Prompt
    sys_p = f"你是由DeepSeek驱动的专业网文作家。小说类型：{novel_type}。\n{ctx}\n\n【执行指令】\n{instruction}\n\n禁止输出任何礼貌用语，直接写正文。"

    # 聊天显示区域
    container = st.container(height=450)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪，输入第一句开始创作...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # 快速精修面板
    with st.expander("🛠️ 快速精修面板 (润色/重写)", expanded=False):
        t1, t2 = st.tabs(["✍️ 局部润色", "💥 本章重写"])
        with t1:
            c_fix1, c_fix2 = st.columns(2)
            bad = c_fix1.text_area("粘贴片段", height=100, label_visibility="collapsed", placeholder="粘贴不满意的片段...")
            req = c_fix2.text_area("修改要求", height=100, label_visibility="collapsed", placeholder="例：写得更恐怖一点")
            if st.button("✨ 润色片段"):
                if bad and req:
                    p = f"修改片段：{bad}\n要求：{req}\n直接输出内容。"
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                    st.write_stream(stream)
        with t2:
            st.warning("⚠️ 建议先备份。")
            req_full = st.text_input("重写要求", placeholder="例：节奏太慢了，直接进入高潮")
            if st.button("💥 推翻重写本章"):
                p = f"【指令】重写本章，要求：{req_full}。保留核心逻辑。"
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"重写指令：{req_full}"})
                st.markdown("**正在重写...**")
                try:
                    stream = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[{"role":"system","content":sys_p}] + st.session_state["chapters"][st.session_state.current_chapter], 
                        stream=True,
                        temperature=creativity # 使用动态温度
                    )
                    response = st.write_stream(stream)
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content": response})
                except Exception as e: st.error(str(e))

    st.markdown("---")
    
    # 输入区与控制区
    c_input, c_btn = st.columns([5, 1])
    with c_input:
        manual_plot = st.text_input(
            "💡 剧情微操 (导演指令)", 
            placeholder="留空 = AI自动发挥；填了 = 强制按你的剧本演（如：主角捡到神器）",
            help="如果不填，AI会根据上下文逻辑自动续写。如果填了，AI 会优先满足你的剧情要求。"
        )
    with c_btn:
        st.write("")
        st.write("")
        btn_cont = st.button("🔄 继续写", use_container_width=True)

    # 逻辑 1：用户输入
    if prompt := st.chat_input("输入剧情..."):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=[{"role":"system","content":sys_p}] + current_msgs, 
                    stream=True, 
                    temperature=creativity # 使用动态温度
                )
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # 逻辑 2：点击继续写
    if btn_cont:
        p = f"接着写。注意：{manual_plot}。" if manual_plot else "接着上文继续写，保持连贯。"
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(p)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=[{"role":"system","content":sys_p}] + current_msgs, 
                    stream=True, 
                    temperature=creativity # 使用动态温度
                )
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 ---
with tab_pipeline:
    st.info("AI 策划师模式。")
    planner_prompt = "你是一个网文策划。只提供设定和大纲，**严禁撰写正文**。字数控制在 300 字以内。"

    # Step 1: 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("输入你的初始点子")
        c1, c2 = st.columns(2)
        if c1.button("✨ 生成梗"):
            p = f"基于点子“{idea}”，为{novel_type}生成核心梗。不要写正文！"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
        if c2.button("🔄 换一个"):
            p = f"基于点子“{idea}”，换一个完全不同的方向生成梗。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
    if st.session_state["pipe_idea"]:
        st.session_state["pipe_idea"] = st.text_area("✅ 脑洞结果", st.session_state["pipe_idea"], height=100)

    # Step 2: 人设
    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        c1, c2 = st.columns(2)
        if c1.button("👥 生成人设"):
            p = f"基于梗“{st.session_state['pipe_idea']}”，生成人设。只写档案！"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
        adjust = c2.text_input("哪里不满意？", label_visibility="collapsed", placeholder="输入修改意见...")
        if adjust and c2.button("🗣️ 调整"):
            p = f"修改人设：{st.session_state['pipe_char']}。要求：{adjust}。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
    if st.session_state["pipe_char"]:
        st.session_state["pipe_char"] = st.text_area("✅ 人设结果", st.session_state["pipe_char"], height=200)

    # Step 3: 大纲
    with st.expander("Step 3: 大纲", expanded=bool(st.session_state["pipe_char"])):
        if st.button("📜 生成细纲"):
            p = f"核心梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。生成前三章细纲。**只写大纲！**"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)
    if st.session_state["pipe_outline"]:
        st.session_state["pipe_outline"] = st.text_area("✅ 大纲结果", st.session_state["pipe_outline"], height=300)

# --- TAB 3: 外挂 ---
with tab_tools:
    st.info("🔮 灵感生成器")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎬 万能场面")
        scene_type = st.selectbox("类型", ["⚔️ 战斗/热血", "💖 感情/甜宠", "👻 悬疑/恐怖", "😎 装逼/打脸", "💼 商战/智斗"])
        scene_info = st.text_input("描述一下", placeholder="例如：男主壁咚女主")
        if st.button("✨ 生成"):
            p = f"写一段【{scene_type}】描写。内容：{scene_info}。要求：画面感强，300字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
    with c2:
        st.markdown("### 📟 系统生成")
        sys_txt = st.text_input("系统提示语", placeholder="如：获得神级技能！")
        if st.button("生成面板"):
            st.markdown(f"""<div class="system-box">【系统提示】<br>⚡ 触发：{sys_txt}</div>""", unsafe_allow_html=True)

# --- TAB 4: 发书控制台 ---
with tab_publish:
    st.info("准备发布？")
    full_book_text = ""
    for ch_num, msgs in st.session_state["chapters"].items():
        ch_txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        full_book_text += f"\n\n### 第 {ch_num} 章 ###\n\n{ch_txt}"
    
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        st.markdown("#### 🧹 纯净 TXT")
        clean_text = full_book_text.replace("**", "").replace("##", "")
        st.download_button("📥 下载全书", clean_text, "novel_clean.txt")
    with c_p2:
        st.markdown("#### 📦 分章打包 (ZIP)")
        if st.button("🎁 生成压缩包"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ch_num, msgs in st.session_state["chapters"].items():
                    ch_content = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
                    ch_content = ch_content.replace("**", "").replace("##", "")
                    zip_file.writestr(f"Chapter_{ch_num}.txt", ch_content)
            st.download_button("📥 下载 ZIP", zip_buffer.getvalue(), "novel_chapters.zip", mime="application/zip")
    with c_p3:
        st.markdown("#### 💊 全数据备份")
        backup = {"chapters": st.session_state["chapters"], "codex": st.session_state["codex"], "scrap": st.session_state["scrap_yard"], "pipe": st.session_state["pipe_idea"], "mimic": st.session_state["mimic_analysis"]}
        st.download_button("📥 导出 JSON", json.dumps(backup, ensure_ascii=False), "backup.json")