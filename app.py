import streamlit as st
from openai import OpenAI
import json
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 核心数据初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    # 核心数据结构 (State)
    defaults = {
        # --- 核心写作 ---
        "chapters": {1: []},       
        "current_chapter": 1,      
        "daily_target": 3000,
        
        # --- 数据库 ---
        "codex": {},               
        "scrap_yard": [],          
        
        # --- 用户状态 ---
        "logged_in": False,
        "first_visit": True,
        
        # --- 备战区 ---
        "context_buffer": "",      
        "mimic_style": "",         
        
        # --- 蓝图数据 (核心修复：直接用这些变量绑定输入框) ---
        "bp_idea_content": "",     # 脑洞内容
        "bp_char_content": "",     # 人设内容
        "bp_outline_content": "",  # 细纲内容
        
        # --- 蓝图定稿 (发送给写作区的数据) ---
        "locked_blueprint": None,  # 只有点击定稿后，这里才会有数据
        
        # --- 全局设置 ---
        "global_genre": "东方玄幻",
        "global_tone": "热血 / 王道",
        "global_naming": "东方中文名",
        "global_world_bg": ""
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (CSS - 完整版)
# ==========================================
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 6px; font-weight: 600; border: none; padding: 0.5rem 1rem;
        transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    /* 输入框聚焦高亮 */
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #228be6; box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    /* 章节标题 */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    /* 蓝图容器 */
    .blueprint-box {
        border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; 
        background: white; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* 状态栏 */
    .status-bar-locked {
        padding: 10px 15px; background: #dbe4ff; border-radius: 8px; 
        color: #3b5bdb; font-weight: bold; margin-bottom: 20px; border: 1px solid #bac8ff;
    }
    .status-bar-unlocked {
        padding: 10px 15px; background: #fff5f5; border-radius: 8px; 
        color: #e03131; font-weight: bold; margin-bottom: 20px; border: 1px solid #ffc9c9;
    }
    
    /* 违禁词高亮区 */
    .risky-box {
        padding: 15px; background: #fff5f5; border: 1px solid #ffc9c9; 
        border-radius: 8px; color: #495057; margin-top: 10px; font-family: monospace;
        white-space: pre-wrap; line-height: 1.6;
    }
    
    /* 引导卡片 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    
    /* 导演控制台 */
    .director-box {
        background-color: #e7f5ff; border-left: 5px solid #339af0;
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
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
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ GENESIS</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>全功能 · 稳定版</p>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666", key="pwd_in")
                if st.form_submit_button("🚀 启动", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：指挥塔
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        st.success("✅ 神经网络：在线")
    else:
        st.error("🔴 请配置 API Key")
        st.stop()
    
    st.divider()

    # --- 全局设置 (Fixed) ---
    st.markdown("### 📚 书籍配置")
    with st.container():
        # A. 类型 (修复自定义)
        genre_ops = [
            "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
            "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
            "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
            "女频 | 豪门爽文", "自定义类型..."
        ]
        sel_g = st.selectbox("小说类型", genre_ops, key="sb_sel_g")
        if sel_g == "自定义类型...":
            st.session_state["global_genre"] = st.text_input("✍️ 输入类型", value="克苏鲁修仙", key="sb_inp_g")
        else:
            st.session_state["global_genre"] = sel_g.split("|")[0].strip()
        
        # B. 基调 (修复自定义)
        tone_ops = ["热血 / 王道", "暗黑 / 压抑", "轻松 / 搞笑", "悬疑 / 烧脑", "治愈 / 情感", "自定义基调..."]
        sel_t = st.selectbox("核心基调", tone_ops, key="sb_sel_t")
        if sel_t == "自定义基调...":
            st.session_state["global_tone"] = st.text_input("✍️ 输入基调", value="慢热、群像", key="sb_inp_t")
        else:
            st.session_state["global_tone"] = sel_t
        
        st.session_state["global_world_bg"] = st.text_input("世界背景", placeholder="如：蒸汽朋克大明", key="sb_bg")
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名", "西方译名", "日式轻小说", "古风雅韵"], key="sb_nm")

    st.divider()

    # --- 仪表盘 ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    curr_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    st.markdown(f"**🔥 字数统计** ({curr_len} / {st.session_state['daily_target']})")
    st.progress(min(curr_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.number_input("章号", 1, value=st.session_state.current_chapter, key="sb_nav")
        if target != st.session_state.current_chapter:
            if target not in st.session_state.chapters: st.session_state.chapters[target] = []
            st.session_state.current_chapter = target
            st.rerun()
    with c2: 
        if st.button("⏪", help="撤销", key="sb_undo"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.rerun()

    # --- 工具 ---
    with st.expander("📕 设定集"):
        k = st.text_input("词条", placeholder="青莲火", key="cd_k")
        v = st.text_input("描述", placeholder="异火榜19", key="cd_v")
        if st.button("➕ 录入", key="btn_cd"): 
            st.session_state["codex"][k] = v; st.success("已录")
        for key, val in st.session_state["codex"].items(): st.markdown(f"**{key}**: {val}")

    with st.expander("🗑️ 废稿篓"):
        s = st.text_area("暂存", height=60, key="sc_in")
        if st.button("📥 存", key="btn_sc"): 
            st.session_state["scrap_yard"].append(s); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, txt in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", txt, height=60, key=f"sc_v_{i}")
                if st.button(f"删 #{i+1}", key=f"d_sc_{i}"):
                    st.session_state["scrap_yard"].pop(i); st.rerun()
    
    st.divider()
    if st.button("ℹ️ 重看新手引导", use_container_width=True, key="btn_gd"):
        st.session_state["first_visit"] = True
        st.rerun()

# ==========================================
# 4. 新手引导
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br><h1 style='text-align: center; color: #228be6;'>✨ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #868e96;'>功能全开 · 续写神器 · 格式无忧</p><br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">📂</span>
            <div class="guide-title">全局设定</div>
            <div class="guide-desc">在侧边栏配置小说类型与基调。<br>支持自定义世界观与起名风格。</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">🗺️</span>
            <div class="guide-title">创世蓝图</div>
            <div class="guide-desc"><b>先生成，再定稿</b>。<br>支持<b>流式生成</b>与<b>反复修改</b>，确认后同步给写作 AI。</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">✍️</span>
            <div class="guide-title">沉浸写作</div>
            <div class="guide-desc">开启<b>分栏模式</b>对照大纲写作。<br>使用<b>导演控制台</b>精准把控节奏。</div>
        </div>
        """, unsafe_allow_html=True)

    c_center = st.columns([1, 2, 1])
    with c_center[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 开始创作", type="primary", use_container_width=True, key="btn_go"):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_blueprint, tab_write, tab_tools, tab_publish = st.tabs(["🗺️ 创世蓝图 (策划)", "✍️ 沉浸写作 (正文)", "🔮 灵感工具箱", "💾 发书控制台"])

# ==========================================
# TAB 1: 创世蓝图 (完美修复版)
# ==========================================
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图")
    st.info("💡 这里的每一个字都可以手动修改。改满意后，**必须点击底部的 [锁定并同步]**，写作 AI 才会知道你的设定。")
    
    plan_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】直接输出内容，不要输出'好的'。不要写标题。"
    )

    # --- 1. 核心脑洞 ---
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # 核心修复：直接绑定 session_state["bp_idea_content"]
    # 这样无论是手动输入，还是AI生成，都更新同一个变量，不会打架
    if "bp_idea_content" not in st.session_state: st.session_state.bp_idea_content = ""
    
    st.text_area("在此输入或生成脑洞 (可任意修改)", key="bp_idea_content", height=150)
    
    c_b1, c_b2, c_b3 = st.columns([1, 2, 1])
    
    # 生成按钮
    if c_b1.button("✨ 帮我构思", key="gen_idea"):
        with st.spinner("AI 构思中..."):
            p = "请构思一个有吸引力的核心梗，包含冲突和期待感。200字内。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            # 核心修复：write_stream 返回后，直接赋值给 state 并 rerun
            response = st.write_stream(stream)
            st.session_state.bp_idea_content = response 
            st.rerun()
            
    # 重写按钮
    fb_idea = c_b2.text_input("修改意见", placeholder="如：再反转一下", label_visibility="collapsed", key="fb_idea")
    if c_b3.button("🔄 根据意见重写", key="rw_idea"):
        if not st.session_state.bp_idea_content:
            st.error("请先有内容再重写")
        else:
            with st.spinner("重写中..."):
                p = f"当前内容：{st.session_state.bp_idea_content}。\n修改意见：{fb_idea}。\n请重写。要求：直接输出新版本，不要废话。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
                response = st.write_stream(stream)
                st.session_state.bp_idea_content = response
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. 角色档案 ---
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    if "bp_char_content" not in st.session_state: st.session_state.bp_char_content = ""
    st.text_area("角色设定 (可任意修改)", key="bp_char_content", height=200)
    
    c_c1, c_c2, c_c3 = st.columns([1, 2, 1])
    if c_c1.button("👥 生成人设", key="gen_char"):
        if not st.session_state.bp_idea_content: st.error("请先完成脑洞！"); st.stop()
        with st.spinner("捏人中..."):
            p = f"基于脑洞：{st.session_state.bp_idea_content}。生成主角档案（姓名/性格/金手指）。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state.bp_char_content = response
            st.rerun()
            
    fb_char = c_c2.text_input("修改意见", placeholder="如：男主太弱了", label_visibility="collapsed", key="fb_char")
    if c_c3.button("🔄 根据意见重写", key="rw_char"):
        with st.spinner("重写中..."):
            p = f"当前人设：{st.session_state.bp_char_content}。\n修改意见：{fb_char}。\n请重写。要求：直接输出新档案。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state.bp_char_content = response
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 3. 剧情细纲 ---
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    if "bp_outline_content" not in st.session_state: st.session_state.bp_outline_content = ""
    st.text_area("细纲内容 (可任意修改)", key="bp_outline_content", height=300)
    
    c_o1, c_o2, c_o3 = st.columns([1, 2, 1])
    if c_o1.button("📜 生成细纲", key="gen_out"):
        if not st.session_state.bp_char_content: st.error("请先完成人设！"); st.stop()
        with st.spinner("推演中..."):
            p = f"脑洞：{st.session_state.bp_idea_content}。\n人设：{st.session_state.bp_char_content}。\n生成前三章细纲。严禁客套话。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state.bp_outline_content = response
            st.rerun()
            
    fb_out = c_o2.text_input("修改意见", placeholder="如：节奏太慢", label_visibility="collapsed", key="fb_out")
    if c_o3.button("🔄 根据意见重写", key="rw_out"):
        with st.spinner("重写中..."):
            p = f"当前细纲：{st.session_state.bp_outline_content}。\n修改意见：{fb_out}。\n请重写。要求：直接输出新细纲，不要写废话。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state.bp_outline_content = response
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- 核心修复：定稿按钮 ---
    # 只有点击这个，数据才会锁定并传输给写作区
    if st.button("🔒 锁定并同步到写作区", type="primary", use_container_width=True, key="lock_bp"):
        st.session_state["locked_blueprint"] = {
            "idea": st.session_state.bp_idea_content,
            "char": st.session_state.bp_char_content,
            "outline": st.session_state.bp_outline_content
        }
        st.session_state["is_blueprint_locked"] = True
        st.success("✅ 已同步！现在 AI 将严格按照此设定进行创作。请切换到 [沉浸写作] 标签页。")

# ==========================================
# TAB 2: 沉浸写作 (接收蓝图数据)
# ==========================================
with tab_write:
    # 状态栏
    if st.session_state["is_blueprint_locked"]:
        st.markdown(f"""<div class="status-bar-locked">🟢 蓝图已挂载 | 脑洞：{len(st.session_state['locked_blueprint']['idea'])}字 | 大纲：{len(st.session_state['locked_blueprint']['outline'])}字</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="status-bar-unlocked">🔴 尚未定稿 | AI 目前处于自由发挥模式。请去 [创世蓝图] 点击锁定按钮。</div>""", unsafe_allow_html=True)

    # 1. 备战区
    with st.expander("🎬 备战区 (续写/仿写)", expanded=True):
        c_p1, c_p2 = st.columns([1, 1])
        with c_p1:
            u_ctx = st.file_uploader("上传TXT续写", type=["txt"], key="u_ctx")
            if u_ctx:
                raw_text = u_ctx.getvalue().decode("utf-8")
                st.session_state["context_buffer"] = raw_text[-2000:]
                st.success(f"✅ 已装载旧稿")
        with c_p2:
            u_sty = st.file_uploader("上传样章仿写", type=["txt"], key="u_sty")
            if u_sty and st.button("🧠 提取文风", key="btn_ex_sty"):
                with st.spinner("分析中..."):
                    p = f"分析文风：{u_sty.getvalue().decode('utf-8')[:3000]}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风已提取")

    # 2. 导演控制台
    st.markdown("<div class='director-box'>", unsafe_allow_html=True)
    st.markdown("#### 🎚️ 导演控制台")
    c_d1, c_d2, c_d3, c_d4 = st.columns(4)
    with c_d1: phase = st.selectbox("剧情状态", ["✨ AI 自动把控", "🌊 铺垫", "🔥 推进", "💥 高潮", "❤️ 收尾"], key="s_ph")
    with c_d2: focus = st.selectbox("描写侧重", ["🎲 均衡", "👁️ 画面", "🗣️ 对话", "🧠 心理", "👊 动作"], key="s_fo")
    with c_d3: word_limit = st.number_input("本章字数目标", 100, 10000, 2000, 100, key="n_wl")
    with c_d4: 
        view = st.selectbox("视角", ["第三人称", "第一人称"], key="s_vi")
        burst = st.toggle("💥 注水模式", key="t_bu")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    use_split = st.toggle("📖 对照模式 (右侧显示辅助工具)", value=True, key="t_sp")
    
    if use_split: col_w, col_a = st.columns([7, 3])
    else: col_w = st.container(); col_a = st.empty()

    # --- 左侧：写作 ---
    with col_w:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        msg_container = st.container(height=600)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with msg_container:
            for msg in current_msgs:
                st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"]=="user" else "🖊️").write(msg["content"])

        # 精修
        with st.expander("🛠️ 快速精修"):
            t1, t2 = st.tabs(["润色", "重写"])
            with t1:
                bad = st.text_input("粘贴片段", key="in_bad")
                if st.button("✨ 润色", key="btn_pol") and bad:
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                    st.write_stream(stream)
            with t2:
                req = st.text_input("重写要求", key="in_req")
                if st.button("💥 重写本章", key="btn_rew"):
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"指令：重写本章。要求：{req}"})
                    st.rerun()

        # 违禁词 (V5.0 修复高亮算法)
        if st.button("🛡️ 扫描违禁词", key="btn_scan"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政治"]
            txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            found = [w for w in risky if w in txt]
            if found: 
                st.error(f"发现敏感词：{list(set(found))}")
                # 高亮显示逻辑
                highlighted_txt = txt
                for w in set(found):
                    # 使用 HTML 背景色实现高亮，比 Markdown 更可靠
                    highlighted_txt = highlighted_txt.replace(w, f"<span style='background-color:#ffcccc; color:red; font-weight:bold; padding:2px;'>{w}</span>")
                
                st.markdown("👇 **违规内容定位**：")
                st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px; background:white;'>{highlighted_txt}</div>", unsafe_allow_html=True)
            else: st.success("✅ 内容安全")

        st.markdown("---")
        user_in = st.chat_input("输入剧情...")
        
        if user_in:
            # 组装 Prompt (注入蓝图)
            sys_p = (
                f"你是由DeepSeek驱动的作家。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"背景：{st.session_state['global_world_bg']}。起名：{st.session_state['global_naming']}。\n"
                f"视角：{view}。字数目标：{word_limit}。\n"
            )
            
            # 注入定稿的蓝图
            if st.session_state["is_blueprint_locked"]:
                bp = st.session_state["locked_blueprint"]
                sys_p += f"\n【重要：严格遵循以下设定】\n核心梗：{bp['idea']}\n角色：{bp['char']}\n大纲：{bp['outline']}\n"
            
            # 注入其他
            if phase != "✨ AI 自动把控": sys_p += f"【强制要求】状态：{phase}。\n"
            if focus != "🎲 均衡": sys_p += f"【强制要求】侧重：{focus}。\n"
            if burst: sys_p += "【强制要求】强力注水模式，极尽描摹。\n"
            if st.session_state["mimic_style"]: sys_p += f"【文风模仿】{st.session_state['mimic_style']}\n"
            if st.session_state["context_buffer"]: sys_p += f"【前文接龙】{st.session_state['context_buffer']}\n"
            
            sys_p += "\n【铁律】1. 必须Markdown标题。2. 严禁废话。"

            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":user_in})
            with msg_container:
                st.chat_message("user", avatar="🧑‍💻").write(user_in)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system", "content":sys_p}] + current_msgs, stream=True)
                    resp = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":resp})

    # --- 右侧：外挂 ---
    if use_split and col_a:
        with col_a:
            st.info("🧩 灵感外挂")
            with st.expander("🔮 剧情预测", True):
                if st.button("🎲 预测", key="btn_pre"):
                    recent = "".join([m["content"] for m in current_msgs[-3:]])
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"基于：{recent[-800:]}，给出3个分支。"}])
                    st.info(r.choices[0].message.content)
            with st.expander("📛 起名助手"):
                t = st.selectbox("类型", ["配角", "反派", "宗门", "宝物"], key="s_na")
                if st.button("🎲 生成", key="btn_na"):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"生成5个{st.session_state['global_genre']}风格的{t}。"}])
                    st.write(r.choices[0].message.content)
            with st.expander("📜 大纲参考"):
                # 这里显示的是定稿后的大纲
                display_outline = st.session_state["locked_blueprint"].get("outline", "暂无定稿大纲") if st.session_state["is_blueprint_locked"] else "请先在 [创世蓝图] 定稿"
                st.text_area("只读", display_outline, height=300, disabled=True, key="out_read")

# --- TAB 3: 灵感工具箱 (保留) ---
with tab_tools:
    st.info("🛠️ 经典工具箱")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎬 万能场面")
        t = st.selectbox("类型", ["⚔️ 战斗", "💖 感情", "👻 恐怖", "😎 装逼"], key="sc_t")
        d = st.text_input("描述", placeholder="如：壁咚", key="sc_d")
        if st.button("生成", key="btn_sc"):
            p = f"写一段{t}。内容：{d}。300字。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.text_area("结果", r.choices[0].message.content, height=200, key="sc_r")
    with c2:
        st.markdown("### 📟 系统生成")
        i = st.text_input("提示语", placeholder="获得神器", key="sys_i")
        if st.button("生成", key="btn_sys"):
            st.markdown(f"""<div class="system-box">【系统】{i}</div>""", unsafe_allow_html=True)

# --- TAB 4: 发书控制台 ---
with tab_publish:
    st.markdown("### 🚀 发书控制台")
    full = ""
    for ch, msgs in st.session_state["chapters"].items():
        txt = "".join([m["content"] for m in msgs if m["role"] == "assistant"])
        full += f"\n\n### 第 {ch} 章 ###\n\n{txt}"
    
    def clean(t):
        t = t.replace("**", "").replace("##", "")
        t = re.sub(r'#+\s*', '', t)
        lines = [f"　　{l.strip()}" for l in t.split('\n') if l.strip()]
        return "\n\n".join(lines)
    
    cl = clean(full)
    st.text_area("预览", cl[:500]+"...", height=200, disabled=True, key="pub_pre")
    st.download_button("📥 下载全书 (TXT)", cl, "novel.txt", key="btn_dl_txt")
    
    if st.button("🎁 分章 ZIP", key="btn_dl_zip"):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                z.writestr(f"Chapter_{ch}.txt", clean("".join([m["content"] for m in msgs if m["role"]=="assistant"])))
        st.download_button("下载 ZIP", b.getvalue(), "chapters.zip", mime="application/zip", key="btn_real_dl_zip")