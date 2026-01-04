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
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_world": "",
        "pipe_outline": "",
        "codex": {},
        "scrap_yard": [],
        "mimic_analysis": "", # 文风记忆
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
# 1. 样式美化 (CSS)
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
    
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    
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
# 3. 侧边栏：指挥塔 (全功能回归版)
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

    # --- 章节控制 ---
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

    # --- 🔥🔥🔥 回归：档案室 (导入 & 文风) 🔥🔥🔥 ---
    with st.expander("📂 档案室 (导入/文风)", expanded=True):
        t_imp1, t_imp2 = st.tabs(["📥 导入旧稿", "🧬 文风克隆"])
        
        # 1. 导入旧稿
        with t_imp1:
            uploaded_draft = st.file_uploader("传TXT续写", type=["txt"], key="draft_up")
            if uploaded_draft and st.button("📥 确认导入"):
                draft_content = uploaded_draft.getvalue().decode("utf-8")
                # 存入当前章节历史
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
            uploaded_style = st.file_uploader("传大神作品", type=["txt"], key="style_up")
            if uploaded_style and st.button("🧠 提取文风"):
                raw_style = uploaded_style.getvalue().decode("utf-8")[:2000]
                with st.spinner("正在解构大神文风..."):
                    r = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[{"role":"user","content":f"分析这段文字的文风（用词、节奏、叙事视角）：\n{raw_style}"}]
                    )
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                    st.success("文风已激活！")

    # --- 工具包 ---
    with st.expander("📕 设定集"):
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已录")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

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

    # --- 参数 ---
    st.divider()
   # === 替换开始：增强版侧边栏 ===
    st.divider()
    st.markdown("### 🧠 大脑控制台")
    
    # 1. 扩充类型库 (满足你的要求)
    genre_list = [
        "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
        "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
        "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
        "游戏 | 第四天灾", "女频 | 豪门爽文", "女频 | 宫斗宅斗", "自定义"
    ]
    t_sel = st.selectbox("📚 小说类型", genre_list)
    novel_type = st.text_input("输入具体类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel.split("|")[0]
    
    # 2. 新增：视角选择
    perspective = st.selectbox("👁️ 视角", ["第三人称 (上帝)", "第一人称 (我)", "第二人称 (你)"], index=0)

    st.markdown("---")
    
    # 3. 新增：控制参数
    writing_style = st.select_slider("🎭 文风", options=["极简", "正常", "华丽", "暗黑", "幽默"], value="正常")
    pace_control = st.radio("⏱️ 节奏", ["快 (重剧情)", "正常", "慢 (重细节)"], index=1, horizontal=True)
    creativity = st.slider("🔥 创意温度", 0.1, 1.5, 1.2, 0.1, help="越大越疯，越小越严谨")
    
    word_target = st.number_input("字数目标", 100, 5000, 1500, 100)
    burst_mode = st.toggle("💥 强力扩写 (注水模式)", value=True)
    # === 替换结束 ===

# ==========================================
# 4. 新手引导
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

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 组装 Prompt
    ctx = ""
    if st.session_state.get("pipe_char"): ctx += f"\n【角色】{st.session_state['pipe_char']}"
    if st.session_state.get("pipe_outline"): ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("mimic_analysis"): ctx += f"\n【模仿文风】{st.session_state['mimic_analysis']}" # 🔥 文风回来了
    
  # === 替换开始：Prompt 升级 ===
    # 1. 注入所有新参数
    style_instruction = f"视角：{perspective}。文风：{writing_style}。节奏：{pace_control}。"
    
    # 2. 强力扩写逻辑
    if burst_mode:
        len_ins = f"目标字数：{word_target}+。必须大量描写环境、光影、气味和心理微表情，严禁记流水账。"
    else:
        len_ins = f"字数：{word_target}。"

    # 3. 组装最终指令
    sys_p = (
        f"你是由DeepSeek驱动的作家。类型：{novel_type}。\n"
        f"{style_instruction}\n{ctx}\n"
        f"【执行要求】\n"
        f"1. {len_ins}\n"
        f"2. 禁止输出'好的'，直接写正文。"
    )
    # === 替换结束 ===

    container = st.container(height=450)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # 🔥 随手精修面板
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
# === 插入开始：雷达与复制 ===
    c_tool1, c_tool2 = st.columns([1, 1])
    
    # 功能 1：违禁词雷达 (带标红功能)
    with c_tool1:
        with st.expander("🛡️ 违禁词雷达 (点击扫描)"):
            if st.button("🔍 扫描本章"):
                # 可以在这里添加更多词
                risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "自杀", "爆炸"] 
                txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                found = [w for w in risky if w in txt]
                
                if found:
                    st.error(f"发现：{found}")
                    # 高亮逻辑：把违禁词变成红色加粗
                    for w in set(found):
                        txt = txt.replace(w, f":red[**{w}**]")
                    st.markdown("### 👇 违规定位")
                    st.markdown(txt) # 显示标红后的文本
                else:
                    st.success("✅ 内容安全")

    # 功能 2：一键复制 (获取最新一条 AI 回复)
    with c_tool2:
        last_ai_msg = ""
        for m in reversed(current_msgs):
            if m["role"] == "assistant":
                last_ai_msg = m["content"]; break
        
        if last_ai_msg:
            with st.expander("📋 一键复制", expanded=True):
                st.caption("点击右上角📄图标复制")
                st.code(last_ai_msg, language=None)
    # === 插入结束 ===
    st.markdown("---")
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

    if prompt := st.chat_input("输入剧情..."):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True, temperature=creativity)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    if btn_cont:
        p = f"接着写。注意：{manual_plot}。" if manual_plot else "接着上文继续写，保持连贯。"
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(p)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True, temperature=creativity)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 (交互式) ---
with tab_pipeline:
    st.info("AI 策划师模式。已限制字数。")
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

# --- TAB 3: 外挂 (升级版) ---
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

# --- TAB 4: 发书控制台 (满血复活) ---
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
        backup = {"chapters": st.session_state["chapters"], "codex": st.session_state["codex"], "scrap": st.session_state["scrap_yard"], "pipe": st.session_state["pipe_idea"]}
        st.download_button("📥 导出 JSON", json.dumps(backup, ensure_ascii=False), "backup.json")