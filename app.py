import streamlit as st
from openai import OpenAI
import json
import random
import re
import time

# ==========================================
# 0. 全局配置 & 强力初始化 (修复 KeyError)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛠️ 修复核心：定义一个专门的初始化函数，缺什么补什么
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
        "mimic_analysis": "",  # 👈 之前报错的就是它，现在强制补上
        "mimic_style": "",
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "init_done": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 执行初始化
init_session()

# ==========================================
# 1. 样式美化
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #ffffff; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #f7f9fb; border-right: 1px solid #e0e0e0;}
    .stButton>button {
        background-color: #007bff; color: white !important; 
        border-radius: 6px; border: none; font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,123,255,0.2); transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #0056b3; transform: translateY(-1px);
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #fff; border: 1px solid #ced4da; border-radius: 6px;
    }
    .stChatMessage {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; margin-bottom: 10px;}
    .alert-word {color: #d93025; font-weight: bold; background-color: #ffe6e6; padding: 0 4px; border-radius: 3px;}
    .onboarding-header {font-size: 24px; font-weight: bold; color: #007bff; margin-bottom: 10px;}
    .onboarding-step {background-color: #f0f7ff; border: 1px solid #cce5ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;}
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
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Fix版</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666")
                if st.form_submit_button("🚀 启动", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏
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
    
    # 仪表盘
    st.divider()
    # 安全获取章节，防止报错
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    
    progress = min(current_text_len / st.session_state["daily_target"], 1.0)
    st.markdown(f"**🔥 今日成就** ({current_text_len} / {st.session_state['daily_target']} 字)")
    st.progress(progress)

    st.divider()

    # 章节
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2:
        st.caption(f"第 {st.session_state.current_chapter} 章")
    
    if st.button("⏪ 撤销上一步", use_container_width=True):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已撤销", icon="↩️")
            st.rerun()
        else:
            st.warning("无内容可撤销")

    st.divider()

    # 工具包
    with st.expander("📕 设定集"):
        new_term = st.text_input("新词条名")
        new_desc = st.text_input("描述")
        if st.button("➕ 收录"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已收录")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    with st.expander("🗑️ 回收站"):
        scrap = st.text_area("存入片段", height=60)
        if st.button("📥 存入"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("已保存")
        for i, s in enumerate(st.session_state["scrap_yard"]):
            st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")

    with st.expander("🛡️ 违禁词雷达"):
        if st.button("🔴 扫描"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政府"]
            txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter]])
            found = [w for w in risky if w in txt]
            if found: st.error(f"发现: {list(set(found))}")
            else: st.success("安全")

    st.divider()
    all_types = ["末世 | 囤货基地", "末世 | 丧尸围城", "玄幻 | 东方玄幻", "都市 | 异术超能", "历史 | 架空历史", "无限流 | 诸天万界", "女频 | 豪门总裁", "自定义"]
    t_sel = st.selectbox("类型", all_types)
    novel_type = st.text_input("输入类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel
    word_target = st.number_input("字数目标", 100, 5000, 800, 100)
    burst_mode = st.toggle("强力扩写", value=True)

# ==========================================
# 4. 新手引导 (可选，仅第一次显示)
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    with st.container():
        st.markdown("""<div class="onboarding-header">🎉 欢迎回来！</div>""", unsafe_allow_html=True)
        st.info("已修复所有卡顿和报错问题。请点击下方按钮开始创作。")
        if st.button("✅ 开始创作", type="primary", use_container_width=True):
            st.session_state["first_visit"] = False
            st.rerun()

# ==========================================
# 5. 主工作区
# ==========================================
if not st.session_state["first_visit"]:
    tab_write, tab_pipeline, tab_edit, tab_tools, tab_export = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "✨ 精修重写", "🔮 外挂", "💾 导出"])

    # --- TAB 1: 写作 ---
    with tab_write:
        st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
        
        # 组装 Prompt
        context_prompt = ""
        # 这里的 .get 是双重保险，防止报错
        if st.session_state.get("pipe_char"): context_prompt += f"\n【角色】{st.session_state['pipe_char']}"
        if st.session_state.get("pipe_outline"): context_prompt += f"\n【大纲】{st.session_state['pipe_outline']}"
        if st.session_state.get("mimic_analysis"): context_prompt += f"\n【模仿】{st.session_state['mimic_analysis']}"
        
        instruction = f"字数目标：{word_target}。" + ("【强力扩写】详细描写。" if burst_mode else "")
        system_prompt = f"你是由DeepSeek驱动的作家。类型：{novel_type}。{context_prompt}\n{instruction}\n禁止客套。"

        container = st.container(height=500)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with container:
            if not current_msgs: st.info("准备就绪...")
            for msg in current_msgs:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
                content = msg["content"]
                if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠)"
                st.chat_message(msg["role"], avatar=avatar).write(content)

        c1, c2 = st.columns([5, 1])
        with c1: manual_plot = st.text_input("剧情微操", placeholder="例如：主角捡到一把枪...")
        with c2: 
            st.write("")
            st.write("")
            btn_cont = st.button("🔄 继续", use_container_width=True)

        if prompt := st.chat_input("输入剧情..."):
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(prompt)
                with st.chat_message("assistant", avatar="🖊️"):
                    try:
                        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}] + current_msgs, stream=True, temperature=1.2)
                        response = st.write_stream(stream)
                        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})
                    except Exception as e:
                        st.error(f"生成出错: {e}")

        if btn_cont:
            p = f"接着写。注意：{manual_plot}。" if manual_plot else "接着写，保持连贯。"
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(p)
                with st.chat_message("assistant", avatar="🖊️"):
                    try:
                        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}] + current_msgs, stream=True, temperature=1.2)
                        response = st.write_stream(stream)
                        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})
                    except Exception as e:
                        st.error(f"生成出错: {e}")

    # --- TAB 2: 流水线 ---
    with tab_pipeline:
        st.info("AI 设定生成器。")
        with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
            c1, c2 = st.columns([3,1])
            idea = c1.text_input("点子")
            if c2.button("✨ 生成梗"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"为{novel_type}写个梗，基于：{idea}"}], stream=True)
                st.session_state["pipe_idea"] = st.write_stream(stream)
                # 这里不加 rerun，让用户自己看，避免闪烁
        if st.session_state["pipe_idea"]:
            st.session_state["pipe_idea"] = st.text_area("✅ 脑洞", st.session_state["pipe_idea"], height=100)

        with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
            if st.button("👥 生成人设"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于梗生成人设：{st.session_state['pipe_idea']}"}], stream=True)
                st.session_state["pipe_char"] = st.write_stream(stream)
        if st.session_state["pipe_char"]:
            st.session_state["pipe_char"] = st.text_area("✅ 人设", st.session_state["pipe_char"], height=200)

        with st.expander("Step 3: 大纲", expanded=bool(st.session_state["pipe_char"])):
            if st.button("📜 生成细纲"):
                p = f"梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。生成前三章细纲，不要废话。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                st.session_state["pipe_outline"] = st.write_stream(stream)
        if st.session_state["pipe_outline"]:
            st.session_state["pipe_outline"] = st.text_area("✅ 大纲", st.session_state["pipe_outline"], height=300)

    # --- TAB 3: 精修重写 (🛠️ 修复了这里的BUG) ---
    with tab_edit:
        st.markdown("### 🛠️ 章节精修")
        
        t1, t2, t3 = st.tabs(["📋 全文复制", "✍️ 局部润色", "💥 整章重写"])
        
        # 获取纯文本
        full_text = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
        
        with t1:
            st.code(full_text if full_text else "暂无内容", language="text")
            
        with t2:
            c1, c2 = st.columns(2)
            with c1: bad = st.text_area("粘贴片段", height=150)
            with c2: req = st.text_area("修改要求", height=150)
            if st.button("✨ 润色片段"):
                if bad and req:
                    p = f"修改片段：{bad}\n要求：{req}\n直接输出内容。"
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                    st.write_stream(stream) # 直接流式输出，不存入章节历史
                    
        with t3:
            st.warning("⚠️ 注意：这将生成一个新的版本，建议先复制备份旧版本。")
            req_full = st.text_input("重写意见", placeholder="例：节奏快一点")
            if st.button("💥 推翻重写"):
                if not full_text:
                    st.warning("本章还没内容，没法重写。")
                else:
                    # 🛠️ 修复点：这里直接流式输出，不再强制 Rerun，防止“哑巴”
                    p = f"【指令】重写本章，要求：{req_full}。保留核心剧情。"
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"重写指令：{req_full}"})
                    
                    st.markdown("**正在重写中...**")
                    try:
                        stream = client.chat.completions.create(
                            model="deepseek-chat", 
                            messages=[{"role":"system","content":system_prompt}] + st.session_state["chapters"][st.session_state.current_chapter], 
                            stream=True
                        )
                        # 使用 write_stream 捕获输出
                        response = st.write_stream(stream)
                        # 必须手动存入 Session State，否则刷新就没了
                        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content": response})
                        st.success("重写完成！")
                    except Exception as e:
                        st.error(f"API 出错: {e}")

    # --- TAB 4: 外挂 ---
    with tab_tools:
        c1, c2 = st.columns(2)
        with c1:
            st.info("⚔️ 战斗场面")
            fighter = st.text_input("对战信息")
            if st.button("👊 生成"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"写战斗：{fighter}"}], stream=True)
                st.write_stream(stream)
        with c2:
            st.info("🧬 文风分析")
            f = st.file_uploader("上传样本", type=["txt"])
            if f and st.button("分析"):
                raw = f.getvalue().decode("utf-8")[:1000]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风:{raw}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("已提取")

    # --- TAB 5: 导出 ---
    with tab_export:
        clean_text = full_text.replace("**", "").replace("##", "")
        st.download_button("📥 导出纯净TXT", clean_text, "novel.txt")