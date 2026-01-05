import streamlit as st
from openai import OpenAI
import json
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 核心初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        # --- 核心写作 ---
        "chapters": {1: []},       
        "current_chapter": 1,      
        "daily_target": 3000,
        
        # --- 数据库 ---
        "codex": {},               
        "scrap_yard": [],          
        
        # --- 状态管理 ---
        "logged_in": False,
        "first_visit": True,
        
        # --- 备战区 ---
        "context_buffer": "",      
        "mimic_style": "",         
        
        # --- 蓝图数据 (双保险：分开存输入和结果，防止覆盖丢失) ---
        "bp_idea_prompt": "",      # 你的原始脑洞输入 (永不被AI修改)
        "bp_idea_result": "",      # AI生成的脑洞结果 (可编辑)
        
        "bp_char_prompt": "",      # 你的原始人设要求
        "bp_char_result": "",      # AI生成的人设结果
        
        "bp_outline_prompt": "",   # 你的细纲要求
        "bp_outline_result": "",   # AI生成的细纲结果
        
        # --- 定稿锁 (连接蓝图和写作的关键) ---
        "locked_blueprint": None,  
        "is_blueprint_locked": False,
        
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
# 1. 样式系统 (CSS)
# ==========================================
st.markdown("""
<style>
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
    
    /* 输入框聚焦 */
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #228be6; box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    /* 标题样式 */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    /* 蓝图容器 */
    .blueprint-box {
        border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; 
        background: white; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* 违禁词高亮 */
    .risky-box {
        padding: 15px; background: #fff5f5; border: 1px solid #ffc9c9; 
        border-radius: 8px; color: #495057; margin-top: 10px; font-family: monospace;
        white-space: pre-wrap; line-height: 1.6; font-size: 14px;
    }
    .highlight-word {
        background-color: #ffcccc; color: #c92a2a; font-weight: bold; 
        padding: 2px 4px; border-radius: 3px; border: 1px solid #ffa8a8;
    }
    
    /* 状态栏 */
    .status-locked {
        padding: 10px 15px; background: #dbe4ff; border-radius: 8px; 
        color: #3b5bdb; font-weight: bold; margin-bottom: 20px; border: 1px solid #bac8ff;
    }
    .status-unlocked {
        padding: 10px 15px; background: #fff5f5; border-radius: 8px; 
        color: #e03131; font-weight: bold; margin-bottom: 20px; border: 1px solid #ffc9c9;
    }
    
    /* 引导卡片 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    
    /* 导演台 */
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
            st.markdown("<p style='text-align: center; color: gray;'>V 7.0 终极稳定版</p>", unsafe_allow_html=True)
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

    # --- 全局设置 ---
    st.markdown("### 📚 书籍配置")
    with st.container():
        # A. 类型
        genre_ops = ["东方玄幻", "都市异能", "末世求生", "无限流", "悬疑惊悚", "赛博朋克", "历史穿越", "西幻", "女频爽文", "自定义..."]
        sel_g = st.selectbox("小说类型", genre_ops, key="sb_g")
        if sel_g == "自定义...":
            st.session_state["global_genre"] = st.text_input("✍️ 输入类型", value="克苏鲁修仙", key="sb_g_cust")
        else:
            st.session_state["global_genre"] = sel_g
        
        # B. 基调
        tone_ops = ["热血 / 王道", "暗黑 / 压抑", "轻松 / 搞笑", "悬疑 / 烧脑", "治愈 / 情感", "自定义..."]
        sel_t = st.selectbox("核心基调", tone_ops, key="sb_t")
        if sel_t == "自定义...":
            st.session_state["global_tone"] = st.text_input("✍️ 输入基调", value="慢热、群像", key="sb_t_cust")
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
        if st.button("➕ 录入", key="cd_add"): 
            st.session_state["codex"][k] = v; st.success("已录")
        for key, val in st.session_state["codex"].items(): st.markdown(f"**{key}**: {val}")

    with st.expander("🗑️ 废稿篓"):
        s = st.text_area("暂存", height=60, key="sc_in")
        if st.button("📥 存", key="sc_save"): 
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
            <span class="guide-title">📂</span>
            <div class="guide-title">全局设定</div>
            <div class="guide-desc">在侧边栏配置小说类型与基调。<br>支持自定义世界观与起名风格。</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-title">🗺️</span>
            <div class="guide-title">创世蓝图</div>
            <div class="guide-desc"><b>双框设计，防丢字</b>。<br>先输入灵感，再生成结果。确认无误后锁定同步。</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-title">✍️</span>
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
# TAB 1: 创世蓝图 (V7 双框安全版)
# ==========================================
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图")
    st.info("💡 流程：左/上框输入灵感 -> 点击生成 -> 右/下框显示结果 -> 修改结果 -> **点击锁定**")
    
    planner_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】直接输出内容，不要输出'好的'。不要写标题。"
    )

    # --- 1. 核心脑洞 ---
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # 框1：永久输入框 (你的字永远在这里，不会被覆盖)
    bp_idea_in = st.text_area("✍️ 在此输入你的原始灵感", 
                              value=st.session_state.get("bp_idea_prompt", ""), 
                              height=100, 
                              key="idea_in_safe")
    
    # 按钮栏
    c_b1, c_b2 = st.columns([1, 4])
    if c_b1.button("✨ 生成脑洞", key="gen_idea"):
        st.session_state["bp_idea_prompt"] = bp_idea_in # 保存你的输入
        st.session_state["bp_idea_result"] = "" # 清空旧结果
        
        with st.spinner("AI 正在构思..."):
            p = f"基于点子“{bp_idea_in}”，写一个核心梗，200字内。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_idea_result"] = response
            st.rerun()

    # 框2：结果编辑框 (只有生成后才显示，绑定独立变量)
    if st.session_state.get("bp_idea_result"):
        st.markdown("---")
        # 这里的 value 绑定的是结果变量
        new_res = st.text_area("✅ AI 生成结果 (在此编辑最终版)", 
                               value=st.session_state.get("bp_idea_result", ""), 
                               height=150, 
                               key="idea_res_edit")
        st.session_state["bp_idea_result"] = new_res # 实时保存你的修改
        
        # 重写区
        c_r1, c_r2 = st.columns([3, 1])
        fb_idea = c_r1.text_input("修改意见", placeholder="如：再反转一下", key="fb_idea")
        if c_r2.button("🔄 根据意见重写", key="rw_idea"):
            if not st.session_state.bp_idea_result:
                st.error("请先生成内容！")
            else:
                with st.spinner("重写中..."):
                    # 强力控制字数，防止长篇大论
                    p = f"当前内容：{st.session_state.bp_idea_result}。\n修改意见：{fb_idea}。\n请重写。要求：简练，200字以内，禁止废话。"
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
                    response = st.write_stream(stream)
                    st.session_state["bp_idea_result"] = response
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 2. 角色档案 ---
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # 框1
    bp_char_in = st.text_area("✍️ 角色要求 (选填)", value=st.session_state.get("bp_char_prompt", ""), height=100, key="char_in_safe")
    
    c_c1, c_c2 = st.columns([1, 4])
    if c_c1.button("👥 生成人设", key="gen_char"):
        if not st.session_state.get("bp_idea_result"): st.error("请先完成脑洞！"); st.stop()
        st.session_state["bp_char_prompt"] = bp_char_in
        
        with st.spinner("捏人中..."):
            p = f"基于脑洞：{st.session_state.bp_idea_result}。\n额外要求：{bp_char_in}。\n生成主角档案。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_char_result"] = response
            st.rerun()

    # 框2
    if st.session_state.get("bp_char_result"):
        st.markdown("---")
        new_char = st.text_area("✅ 人设结果 (可编辑)", value=st.session_state.get("bp_char_result", ""), height=200, key="char_res_edit")
        st.session_state["bp_char_result"] = new_char
        
        c_cr1, c_cr2 = st.columns([3, 1])
        fb_char = c_cr1.text_input("修改意见", placeholder="如：男主太弱了", key="fb_char")
        if c_cr2.button("🔄 重写人设", key="rw_char"):
            with st.spinner("重写中..."):
                p = f"当前人设：{st.session_state.bp_char_result}。\n修改意见：{fb_char}。\n请重写。要求：简练。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
                response = st.write_stream(stream)
                st.session_state["bp_char_result"] = response
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 3. 剧情细纲 ---
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # 框1
    bp_out_in = st.text_area("✍️ 细纲要求 (选填)", value=st.session_state.get("bp_outline_prompt", ""), height=100, key="out_in_safe")
    
    c_o1, c_o2 = st.columns([1, 4])
    if c_o1.button("📜 生成细纲", key="gen_out"):
        if not st.session_state.get("bp_char_result"): st.error("请先完成人设！"); st.stop()
        st.session_state["bp_outline_prompt"] = bp_out_in
        
        with st.spinner("推演中..."):
            p = f"脑洞：{st.session_state.bp_idea_result}。\n人设：{st.session_state.bp_char_result}。\n要求：{bp_out_in}。\n生成前三章细纲。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_outline_result"] = response
            st.rerun()

    # 框2
    if st.session_state.get("bp_outline_result"):
        st.markdown("---")
        new_out = st.text_area("✅ 细纲结果 (可编辑)", value=st.session_state.get("bp_outline_result", ""), height=300, key="out_res_edit")
        st.session_state["bp_outline_result"] = new_out
        
        c_or1, c_or2 = st.columns([3, 1])
        fb_out = c_or1.text_input("修改意见", placeholder="如：节奏太慢", key="fb_out")
        if c_or2.button("🔄 重写细纲", key="rw_out"):
            with st.spinner("重写中..."):
                p = f"当前细纲：{st.session_state.bp_outline_result}。\n修改意见：{fb_out}。\n请重写。要求：简练。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
                response = st.write_stream(stream)
                st.session_state["bp_outline_result"] = response
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- 核心：定稿按钮 ---
    if st.button("🔒 锁定并同步到写作区", type="primary", use_container_width=True, key="lock_all"):
        st.session_state["locked_blueprint"] = {
            "idea": st.session_state.get("bp_idea_result", ""),
            "char": st.session_state.get("bp_char_result", ""),
            "outline": st.session_state.get("bp_outline_result", "")
        }
        st.session_state["is_blueprint_locked"] = True
        st.success("✅ 已同步！现在去 [沉浸写作] 页面，AI 将严格按照此设定创作。")

# ==========================================
# TAB 2: 沉浸写作 (接收蓝图)
# ==========================================
with tab_write:
    # 状态栏
    if st.session_state["is_blueprint_locked"]:
        bp_len = len(st.session_state['locked_blueprint']['idea']) + len(st.session_state['locked_blueprint']['outline'])
        st.markdown(f"""<div class="status-locked">🟢 蓝图已挂载 | 设定总字数：{bp_len} 字</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="status-unlocked">🔴 尚未定稿 | AI 目前处于自由发挥模式。请去 [创世蓝图] 点击锁定按钮。</div>""", unsafe_allow_html=True)

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
    with c_d1: phase = st.selectbox("剧情状态", ["✨ AI 自动把控", "🌊 铺垫", "🔥 推进", "💥 高潮", "❤️ 收尾"], key="ph")
    with c_d2: focus = st.selectbox("描写侧重", ["🎲 均衡", "👁️ 画面", "🗣️ 对话", "🧠 心理", "👊 动作"], key="fo")
    with c_d3: w_lim = st.number_input("本章字数目标", 100, 10000, 2000, 100, key="wl")
    with c_d4: 
        view = st.selectbox("视角", ["第三人称", "第一人称"], key="vi")
        burst = st.toggle("💥 注水模式", key="bu")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    use_split = st.toggle("📖 对照模式", value=True, key="sp_view")
    
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
                bad = st.text_input("粘贴片段", key="bad_frag")
                if st.button("✨ 润色", key="btn_pol") and bad:
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                    st.write_stream(stream)
            with t2:
                req = st.text_input("重写要求", key="rew_req")
                if st.button("💥 重写本章", key="btn_rew_chap"):
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"指令：重写本章。要求：{req}"})
                    st.rerun()

        # 违禁词 (核心修复：高亮算法)
        if st.button("🛡️ 扫描违禁词", key="btn_scan"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政治"]
            txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            found = [w for w in risky if w in txt]
            if found: 
                st.error(f"发现敏感词：{list(set(found))}")
                # 使用 HTML 背景色实现高亮
                hl_text = txt
                for w in set(found):
                    hl_text = hl_text.replace(w, f"<span class='highlight-word'>{w}</span>")
                st.markdown("👇 **定位结果**：")
                st.markdown(f"<div class='risky-box'>{hl_text}</div>", unsafe_allow_html=True)
            else: st.success("✅ 内容安全")

        st.markdown("---")
        user_in = st.chat_input("输入剧情...")
        
        if user_in:
            # 组装 Prompt
            sys_p = (
                f"你是由DeepSeek驱动的作家。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"背景：{st.session_state['global_world_bg']}。起名：{st.session_state['global_naming']}。\n"
                f"视角：{view}。字数目标：{w_lim}。\n"
            )
            
            # 注入定稿蓝图
            if st.session_state["is_blueprint_locked"]:
                bp = st.session_state["locked_blueprint"]
                sys_p += f"\n【重要：严格遵循以下设定】\n核心梗：{bp['idea']}\n角色：{bp['char']}\n大纲：{bp['outline']}\n"
            
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
                t = st.selectbox("类型", ["配角", "反派", "宗门", "宝物"], key="s_nm")
                if st.button("🎲 生成", key="btn_nm"):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"生成5个{st.session_state['global_genre']}风格的{t}。"}])
                    st.write(r.choices[0].message.content)
            with st.expander("📜 大纲参考"):
                disp = st.session_state["locked_blueprint"].get("outline", "暂无定稿") if st.session_state["is_blueprint_locked"] else "请先在 [创世蓝图] 定稿"
                st.text_area("只读", disp, height=300, disabled=True, key="out_read")

# --- TAB 3: 灵感工具箱 ---
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
    st.text_area("预览", cl[:500]+"...", height=200, disabled=True, key="pub_prev")
    st.download_button("📥 下载全书 (TXT)", cl, "novel.txt", key="btn_dl_txt")
    
    if st.button("🎁 分章 ZIP", key="btn_zip"):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                z.writestr(f"Chapter_{ch}.txt", clean("".join([m["content"] for m in msgs if m["role"]=="assistant"])))
        st.download_button("下载 ZIP", b.getvalue(), "chapters.zip", mime="application/zip", key="btn_dl_zip")