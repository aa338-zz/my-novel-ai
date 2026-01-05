import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 强力初始化 (完全保留原版)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    # 这里合并了新旧所有的状态，确保数据不丢失
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "history_snapshots": [],
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_world": "",
        "pipe_outline": "",
        "codex": {},        # 设定集
        "scrap_yard": [],   # 废稿篓
        "mimic_analysis": "", # 原版文风记忆
        "mimic_style": "",    # 新版文风滤镜
        "context_buffer": "", # 新版续写缓存
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
# 1. 样式美化 (CSS) - (完全保留原版 + 新增样式)
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
    }
    
    /* 原版新手引导样式 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    
    /* 系统生成框样式 */
    .system-box {
        background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%);
        border: 2px solid #339af0; border-radius: 8px; padding: 15px;
        color: #1864ab; font-family: 'Courier New', monospace; font-weight: bold;
    }

    /* 新增：章节标题样式 */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 24px; font-weight: bold; color: #343a40;
        border-bottom: 2px solid #ced4da; padding-bottom: 10px; margin-bottom: 20px;
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (完全保留原版)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666")
                if st.form_submit_button("🚀 启动引擎", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：指挥塔 (完全复原原版功能)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 神经网络：在线")
    else:
        st.error("🔴 请配置 API Key")
        st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # --- 仪表盘 ---
    st.divider()
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    st.markdown(f"**🔥 今日码字** ({current_text_len} / {st.session_state['daily_target']})")
    st.progress(min(current_text_len / st.session_state['daily_target'], 1.0))
    st.divider()

    # --- 章节控制 (保留) ---
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("章号", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: st.caption(f"第 {st.session_state.current_chapter} 章")
    
    if st.button("⏪ 撤销上一步"):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("时光倒流成功", icon="↩️")
            st.rerun()

    st.divider()

    # --- 📂 档案室 (原版保留) ---
    with st.expander("📂 档案室 (侧边栏版)", expanded=True):
        t_imp1, t_imp2 = st.tabs(["📥 导入旧稿", "🧬 文风克隆"])
        # 1. 导入旧稿
        with t_imp1:
            uploaded_draft = st.file_uploader("传TXT续写", type=["txt"], key="draft_up_sidebar")
            if uploaded_draft and st.button("📥 确认导入"):
                draft_content = uploaded_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "user", "content": f"以下是我之前写的内容，请读取并准备续写：\n\n{draft_content}"}
                )
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "assistant", "content": "✅ 已读取旧稿，请指示下一步剧情。"}
                )
                st.success(f"已导入 {len(draft_content)} 字！")
                st.rerun()
        # 2. 文风克隆
        with t_imp2:
            uploaded_style = st.file_uploader("传大神作品", type=["txt"], key="style_up_sidebar")
            if uploaded_style and st.button("🧠 提取文风"):
                raw_style = uploaded_style.getvalue().decode("utf-8")[:2000]
                with st.spinner("正在解构大神文风..."):
                    r = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[{"role":"user","content":f"分析这段文字的文风（用词、节奏、叙事视角）：\n{raw_style}"}]
                    )
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                    st.success("文风已激活！")

    # --- 设定集 (原版保留) ---
    with st.expander("📕 设定集"):
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已录")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    # --- 废稿篓 (原版保留) ---
    with st.expander("🗑️ 废稿篓"):
        scrap = st.text_area("存入", height=60)
        if st.button("📥"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")
                if st.button(f"❌ 删 {i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i)
                    st.rerun()
                    
    # --- 新增：一些全局参数 ---
    st.divider()
    st.markdown("### 🧠 全局设置")
    genre_list = [
        "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
        "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
        "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
        "游戏 | 第四天灾", "女频 | 豪门爽文", "女频 | 宫斗宅斗", "自定义"
    ]
    t_sel = st.selectbox("📚 小说类型", genre_list)
    novel_type = st.text_input("输入具体类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel.split("|")[0]
    burst_mode = st.toggle("💥 强力扩写 (注水模式)", value=True)


# ==========================================
# 4. 新手引导 (完全保留原版)
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #228be6;'>✨ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #868e96;'>功能全开 · 续写神器 · 格式无忧</p><br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">📂</span>
            <div class="guide-title">导入与文风</div>
            <div class="guide-desc">在侧边栏 <b>[档案室]</b>。<br>上传写了一半的稿子继续写，或者上传大神的小说让 AI 模仿文风。</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">✍️</span>
            <div class="guide-title">沉浸与精修</div>
            <div class="guide-desc"><b>[写作区]</b> 集成了一切。<br>一边写，一边点开下方的工具箱进行<b>局部润色</b>或<b>整章重写</b>。</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">💾</span>
            <div class="guide-title">发布神器</div>
            <div class="guide-desc"><b>[发书控制台]</b>。<br>自动清洗 Markdown 符号，支持<b>一键分章打包</b>，发书不求人。</div>
        </div>
        """, unsafe_allow_html=True)

    c_center = st.columns([1, 2, 1])
    with c_center[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 开始创作 (Bug已修复)", type="primary", use_container_width=True):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "🔮 灵感外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 (融合版：保留原貌，增加功能) ---
with tab_write:
    # >>> 区域 1：导演级备战区 (新增) <<<
    with st.expander("🎬 备战区：素材投喂 & 状态控制 (新增)", expanded=True):
        col_prep_1, col_prep_2 = st.columns([1, 1])
        # A. 素材投喂
        with col_prep_1:
            st.markdown("#### 📂 素材投喂")
            upload_mode = st.radio("模式选择", ["🚫 不使用", "📄 导入旧稿续写", "🧬 导入大神样章仿写"], horizontal=True, label_visibility="collapsed")
            if upload_mode == "📄 导入旧稿续写":
                uploaded_ctx = st.file_uploader("上传TXT (自动读取末尾2000字)", type=["txt"], key="ctx_up_main")
                if uploaded_ctx:
                    raw = uploaded_ctx.getvalue().decode("utf-8")[-2000:]
                    st.session_state["context_buffer"] = raw
                    st.success(f"✅ 已装载前文")
            elif upload_mode == "🧬 导入大神样章仿写":
                uploaded_sty = st.file_uploader("上传样章", type=["txt"], key="sty_up_main")
                if uploaded_sty and st.button("🧠 提取文风 DNA"):
                    with st.spinner("正在分析..."):
                        sample = uploaded_sty.getvalue().decode("utf-8")[:3000]
                        r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"分析文风：\n\n{sample}"}])
                        st.session_state["mimic_style"] = r.choices[0].message.content
                        st.success("✅ 文风已激活")
        # B. 导演参数
        with col_prep_2:
            st.markdown("#### 🎚️ 导演控制台")
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                plot_phase = st.selectbox("当前状态", ["🌊 铺垫/日常", "🔥 推进/解谜", "💥 高潮/冲突", "❤️ 情感/收尾"])
                desc_focus = st.selectbox("描写侧重", ["👁️ 画面/光影", "🗣️ 对话/交锋", "🧠 心理/内省", "👊 动作/招式"])
            with c_p2:
                view_point = st.selectbox("视角", ["第三人称 (上帝)", "第一人称 (我)"])
                word_target = st.number_input("字数目标", 100, 5000, 1500, 100)
    
    st.markdown("---")
    
    # >>> 区域 2：分栏开关 (新增) <<<
    use_split_view = st.toggle("📖 开启对照模式 (左边写，右边看大纲/工具)", value=False)
    
    if use_split_view:
        col_write, col_aux = st.columns([2, 1])
    else:
        col_write = st.container()
        col_aux = st.container() # 如果不分栏，这个区域放在下面或者不显示
    
    # --- 写作主逻辑 ---
    with col_write:
        st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
        
        # 组装 Prompt (保留原版逻辑 + 融合新参数)
        # 1. 基础上下文
        ctx = ""
        if st.session_state.get("pipe_char"): ctx += f"\n【角色】{st.session_state['pipe_char']}"
        if st.session_state.get("pipe_outline"): ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
        if st.session_state.get("mimic_analysis"): ctx += f"\n【档案室文风】{st.session_state['mimic_analysis']}"
        if st.session_state.get("mimic_style"): ctx += f"\n【备战区文风】{st.session_state['mimic_style']}"
        if st.session_state.get("context_buffer"): ctx += f"\n【续写前文】{st.session_state['context_buffer']}"
        
        # 2. RAG 设定集
        active_codex = [f"{k}:{v}" for k, v in st.session_state["codex"].items()]
        if active_codex: ctx += f"\n【设定集】{';'.join(active_codex)}"

        # 3. 导演指令
        phase_map = {"🌊 铺垫/日常": "节奏舒缓", "🔥 推进/解谜": "节奏紧凑", "💥 高潮/冲突": "短句密集，紧张", "❤️ 情感/收尾": "细腻情感"}
        sys_p = (
            f"你是由DeepSeek驱动的作家。类型：{novel_type}。\n"
            f"视角：{view_point}。剧情状态：{phase_map[plot_phase]}。侧重：{desc_focus}。\n"
            f"{ctx}\n"
            f"【执行铁律】\n"
            f"1. **格式强制**：输出的第一行必须是Markdown标题！(### 第X章：标题)\n"
            f"2. 字数：{word_target}。\n"
            f"3. 严禁输出'好的'，直接开始创作。"
        )

        container = st.container(height=450)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with container:
            if not current_msgs: st.info("✨ 准备就绪...")
            for msg in current_msgs:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
                content = msg["content"]
                if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠)"
                st.chat_message(msg["role"], avatar=avatar).write(content)

        # 🔥 随手精修面板 (原版保留)
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
                        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + st.session_state["chapters"][st.session_state.current_chapter], stream=True)
                        response = st.write_stream(stream)
                        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content": response})
                    except Exception as e: st.error(str(e))

        # === 违禁词雷达 & 复制 (原版保留) ===
        c_tool1, c_tool2 = st.columns([1, 1])
        with c_tool1:
            with st.expander("🛡️ 违禁词雷达"):
                if st.button("🔍 扫描本章"):
                    risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "自杀", "爆炸"] 
                    txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                    found = [w for w in risky if w in txt]
                    if found:
                        st.error(f"发现：{found}")
                        for w in set(found): txt = txt.replace(w, f":red[**{w}**]")
                        st.markdown("### 👇 违规定位")
                        st.markdown(txt)
                    else: st.success("✅ 内容安全")
        with c_tool2:
            last_ai_msg = ""
            for m in reversed(current_msgs):
                if m["role"] == "assistant": last_ai_msg = m["content"]; break
            if last_ai_msg:
                with st.expander("📋 一键复制", expanded=True):
                    st.text_area("复制专用框", value=last_ai_msg, height=100, label_visibility="collapsed")

        st.markdown("---")
        
        # 输入区
        c_input, c_btn = st.columns([5, 1])
        with c_input:
            manual_plot = st.text_input(
                "💡 剧情微操 (导演指令)", 
                placeholder="留空 = AI自动发挥；填了 = 强制按你的剧本演"
            )
        with c_btn:
            st.write("")
            st.write("")
            btn_cont = st.button("🔄 继续写", use_container_width=True)

        if prompt := st.chat_input("输入剧情..."):
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(prompt)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

        if btn_cont:
            p = f"接着写。注意：{manual_plot}。" if manual_plot else "接着上文继续写，保持连贯。"
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(p)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # --- 右侧：智能辅助区 (在开启分栏时显示) ---
    if use_split_view and col_aux:
        with col_aux:
            st.info("📌 智能辅助区")
            # 1. 剧情预测 (新增)
            with st.expander("🔮 剧情预测 (卡文点我)", expanded=True):
                if st.button("🎲 接下来发生什么？"):
                    recent = "".join([m["content"] for m in current_msgs[-2:]])
                    p = f"基于剧情：{recent[:500]}... 给出3个有趣的发展分支。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)
            
            # 2. 润色 (新增)
            with st.expander("✨ 润色神器"):
                raw_s = st.text_area("输入句子", placeholder="他很生气")
                if st.button("🪄 润色"):
                    p = f"扩写润色句子：{raw_s}。要求画面感强。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)
            
            # 3. 大纲 (原版数据)
            with st.expander("📜 本书大纲"):
                st.write(st.session_state.get("pipe_outline", "暂无大纲"))


# --- TAB 2: 流水线 (原版保留 + 新增手动录入) ---
with tab_pipeline:
    st.info("AI 策划师模式。已限制字数。")
    planner_prompt = "你是一个网文策划。只提供设定和大纲，**严禁撰写正文**。字数控制在 300 字以内。"

    # Step 1: 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("输入你的初始点子", value=st.session_state["pipe_idea"])
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

    # Step 2: 人设 (增加手动模式)
    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        t_c1, t_c2 = st.tabs(["🎲 AI生成", "✍️ 手动录入"])
        with t_c1:
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
        with t_c2:
            manual_char = st.text_area("输入你的人设草稿", placeholder="主角名：... 性格：...")
            if st.button("✨ 格式化人设"):
                 p = f"整理以下人设为标准档案格式：{manual_char}"
                 stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
                 st.session_state["pipe_char"] = st.write_stream(stream)

    if st.session_state["pipe_char"]:
        st.session_state["pipe_char"] = st.text_area("✅ 人设结果", st.session_state["pipe_char"], height=200)

# Step 3: 大纲
    with st.expander("Step 3: 大纲", expanded=bool(st.session_state["pipe_char"])):
        if st.button("📜 生成细纲"):
            # 强制 AI 输出标题
            p = (
                f"核心梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。\n"
                "生成前三章细纲。**格式严格要求**：\n"
                "每一章必须有章节名！例如：\n"
                "**第一章：[章节名]**\n"
                "1. ...\n"
                "2. ..."
            )
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)

# --- TAB 3: 外挂 (原版保留 + 新增) ---
with tab_tools:
    st.info("🔮 灵感生成器 (全家桶)")
    c1, c2 = st.columns(2)
    # 1. 原版工具
    with c1:
        st.markdown("### 🎬 万能场面 (原版)")
        scene_type = st.selectbox("类型", ["⚔️ 战斗/热血", "💖 感情/甜宠", "👻 悬疑/恐怖", "😎 装逼/打脸", "💼 商战/智斗"])
        scene_info = st.text_input("描述一下", placeholder="例如：男主壁咚女主")
        if st.button("✨ 生成场面"):
            p = f"写一段【{scene_type}】描写。内容：{scene_info}。要求：画面感强，300字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
            
    with c2:
        st.markdown("### 📟 系统生成 (原版)")
        sys_txt = st.text_input("系统提示语", placeholder="如：获得神级技能！")
        if st.button("生成面板"):
            st.markdown(f"""<div class="system-box">【系统提示】<br>⚡ 触发：{sys_txt}</div>""", unsafe_allow_html=True)

    st.divider()
    # 2. 新增工具
    st.markdown("### 📛 起名助手 (新增)")
    c3, c4 = st.columns(2)
    with c3:
         name_t = st.selectbox("起名类型", ["玄幻人名", "现代人名", "功法名", "地名"])
    with c4:
         if st.button("🎲 随机生成"):
             p = f"生成5个{name_t}，风格要独特。"
             r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
             st.info(r.choices[0].message.content)

# --- TAB 4: 发书控制台 (原版保留 + 增强清洗) ---
with tab_publish:
    st.info("准备发布？")
    full_book_text = ""
    for ch_num, msgs in st.session_state["chapters"].items():
        ch_txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        full_book_text += f"\n\n### 第 {ch_num} 章 ###\n\n{ch_txt}"
    
    # 清洗函数 (新增)
    def clean_text(text):
        t = text.replace("**", "").replace("##", "")
        # 去除多余Markdown符号
        return t

    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        st.markdown("#### 🧹 纯净 TXT")
        clean_content = clean_text(full_book_text)
        st.download_button("📥 下载全书 (已清洗)", clean_content, "novel_clean.txt")
        st.text_area("预览", clean_content[:200]+"...", height=100, disabled=True)

    with c_p2:
        st.markdown("#### 📦 分章打包 (ZIP)")
        if st.button("🎁 生成压缩包"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ch_num, msgs in st.session_state["chapters"].items():
                    ch_content = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
                    ch_content = clean_text(ch_content)
                    zip_file.writestr(f"Chapter_{ch_num}.txt", ch_content)
            st.download_button("📥 下载 ZIP", zip_buffer.getvalue(), "novel_chapters.zip", mime="application/zip")
            
    with c_p3:
        st.markdown("#### 💊 全数据备份")
        # 包含所有新旧数据
        backup = {
            "chapters": st.session_state["chapters"], 
            "codex": st.session_state["codex"], 
            "scrap": st.session_state["scrap_yard"], 
            "pipe": st.session_state["pipe_idea"]
        }
        st.download_button("📥 导出 JSON", json.dumps(backup, ensure_ascii=False), "backup.json")