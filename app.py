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
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    # 初始化所有核心变量
    defaults = {
        # --- 核心写作 ---
        "chapters": {1: []},       
        "current_chapter": 1,      
        
        # --- 数据库 ---
        "codex": {},               
        "scrap_yard": [],          
        
        # --- 状态 ---
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        
        # --- 备战区 ---
        "context_buffer": "",      
        "mimic_style": "",         
        
        # --- 蓝图数据 ---
        "bp_idea_input": "", "bp_idea_res": "",
        "bp_char_res": "", "bp_outline_res": "",
        
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
# 1. 样式美化 (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 6px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #228be6; box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    .blueprint-box {
        border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; 
        background: white; margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
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
    
    .director-box {
        background-color: #e7f5ff; border-left: 5px solid #339af0;
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
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
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ GENESIS</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666", key="login_pwd")
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
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        st.success("✅ 神经网络：在线")
    else:
        st.error("🔴 请配置 API Key")
        st.stop()
    
    st.divider()

    # --- 全局设置 (Fixed) ---
    st.markdown("### 📚 书籍配置")
    with st.container():
        genre_ops = [
            "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
            "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
            "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
            "女频 | 豪门爽文", "自定义类型..."
        ]
        sel_g = st.selectbox("小说类型", genre_ops, key="sel_genre")
        if sel_g == "自定义类型...":
            st.session_state["global_genre"] = st.text_input("✍️ 输入类型", value="克苏鲁修仙", key="custom_g")
        else:
            st.session_state["global_genre"] = sel_g.split("|")[0].strip()
        
        tone_ops = ["热血 / 王道", "暗黑 / 压抑", "轻松 / 搞笑", "悬疑 / 烧脑", "治愈 / 情感", "自定义基调..."]
        sel_t = st.selectbox("核心基调", tone_ops, key="sel_tone")
        if sel_t == "自定义基调...":
            st.session_state["global_tone"] = st.text_input("✍️ 输入基调", value="群像、史诗", key="custom_t")
        else:
            st.session_state["global_tone"] = sel_t
        
        st.session_state["global_world_bg"] = st.text_input("世界背景", placeholder="如：蒸汽朋克大明", key="world_bg")
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名", "西方译名", "日式轻小说", "古风雅韵"], key="naming_s")

    st.divider()

    # --- 仪表盘 ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    curr_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    st.markdown(f"**🔥 字数统计** ({curr_len} / {st.session_state['daily_target']})")
    st.progress(min(curr_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.number_input("章号", 1, value=st.session_state.current_chapter, key="nav_chap")
        if target != st.session_state.current_chapter:
            if target not in st.session_state.chapters: st.session_state.chapters[target] = []
            st.session_state.current_chapter = target
            st.rerun()
    with c2: 
        if st.button("⏪", help="撤销", key="btn_undo"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.rerun()

    # --- 工具 ---
    with st.expander("📕 设定集"):
        k = st.text_input("词条", placeholder="青莲火", key="codex_k")
        v = st.text_input("描述", placeholder="异火榜19", key="codex_v")
        if st.button("➕", key="btn_add_codex"): 
            st.session_state["codex"][k] = v; st.success("已录")
        for key, val in st.session_state["codex"].items(): st.markdown(f"**{key}**: {val}")

    with st.expander("🗑️ 废稿篓"):
        s = st.text_area("暂存", height=60, key="scrap_in")
        if st.button("📥", key="btn_save_scrap"): 
            st.session_state["scrap_yard"].append(s); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, txt in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", txt, height=60, key=f"scr_view_{i}")
                if st.button(f"删 #{i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i); st.rerun()
    
    if st.button("ℹ️ 重看新手引导", use_container_width=True, key="btn_replay_guide"):
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
            <div class="guide-desc">分步生成脑洞、人设、大纲。<br>支持<b>流式生成</b>与<b>即时修改</b>。</div>
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
        if st.button("🚀 开始创作", type="primary", use_container_width=True, key="btn_start_app"):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主功能区
# ==========================================
tab_write, tab_blueprint, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🗺️ 创世蓝图", "🔮 灵感工具箱", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    # 1. 备战区
    with st.expander("🎬 备战区：素材投喂 (续写/仿写)", expanded=True):
        c_p1, c_p2 = st.columns([1, 1])
        with c_p1:
            st.markdown("#### 📄 导入旧稿")
            u_ctx = st.file_uploader("上传TXT", type=["txt"], key="u_ctx_file")
            if u_ctx:
                raw = u_ctx.getvalue().decode("utf-8")
                st.session_state["context_buffer"] = raw[-2000:]
                st.success(f"✅ 已装载旧稿")
        with c_p2:
            st.markdown("#### 🧬 仿写文风")
            u_sty = st.file_uploader("上传样章", type=["txt"], key="u_sty_file")
            if u_sty and st.button("🧠 提取文风", key="btn_extract_style"):
                with st.spinner("分析中..."):
                    p = f"分析文风：{u_sty.getvalue().decode('utf-8')[:3000]}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风已提取")

    # 2. 导演控制台
    st.markdown("<div class='director-box'>", unsafe_allow_html=True)
    st.markdown("#### 🎚️ 导演控制台")
    c_d1, c_d2, c_d3, c_d4 = st.columns(4)
    with c_d1: phase = st.selectbox("剧情状态", ["✨ AI 自动把控", "🌊 铺垫/日常", "🔥 推进/解谜", "💥 高潮/冲突", "❤️ 情感/收尾"], key="sel_phase")
    with c_d2: focus = st.selectbox("描写侧重", ["🎲 均衡/随机", "👁️ 画面/光影", "🗣️ 对话/交锋", "🧠 心理/内省", "👊 动作/招式"], key="sel_focus")
    with c_d3: 
        # 字数控制已确认存在
        word_limit = st.number_input("本章字数目标", 100, 10000, 2000, 100, key="num_word_limit")
    with c_d4: 
        burst = st.toggle("💥 强力注水模式", key="tog_burst")
        view = st.selectbox("视角", ["第三人称", "第一人称"], label_visibility="collapsed", key="sel_view")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    use_split = st.toggle("📖 对照模式 (右侧显示辅助工具)", value=True, key="tog_split")
    
    if use_split: col_w, col_a = st.columns([7, 3])
    else: col_w = st.container(); col_a = st.empty()

    # --- 左侧：写作 ---
    with col_w:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        box = st.container(height=600)
        with box:
            for m in msgs:
                st.chat_message(m["role"], avatar="🧑‍💻" if m["role"]=="user" else "🖊️").write(m["content"])

        # 精修
        with st.expander("🛠️ 快速精修"):
            t1, t2 = st.tabs(["润色", "重写"])
            with t1:
                bad = st.text_input("粘贴片段", key="in_bad_frag")
                if st.button("✨ 润色", key="btn_polish") and bad:
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                    st.write_stream(stream)
            with t2:
                req = st.text_input("重写要求", key="in_rewrite_req")
                if st.button("💥 重写本章", key="btn_rewrite_chap"):
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"指令：重写本章。要求：{req}"})
                    st.rerun()

        # 违禁词
        if st.button("🛡️ 扫描违禁词", key="btn_scan_risk"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政治"]
            txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
            found = [w for w in risky if w in txt]
            if found: st.error(f"发现：{found}")
            else: st.success("安全")

        st.markdown("---")
        user_in = st.chat_input("输入剧情...")
        
        if user_in:
            # Prompt
            sys = (
                f"你是由DeepSeek驱动的作家。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"背景：{st.session_state['global_world_bg']}。起名：{st.session_state['global_naming']}。\n"
                f"视角：{view}。字数目标：{word_limit}。\n"
            )
            if phase != "✨ AI 自动把控": sys += f"【强制要求】状态：{phase}。\n"
            if focus != "🎲 均衡/随机": sys += f"【强制要求】侧重：{focus}。\n"
            if burst: sys += "【强制要求】强力注水模式，极尽描摹，字数翻倍。\n"
            if st.session_state["mimic_style"]: sys += f"【文风模仿】{st.session_state['mimic_style']}\n"
            if st.session_state["context_buffer"]: sys += f"【前文接龙】{st.session_state['context_buffer']}\n"
            codex = "; ".join([f"{k}:{v}" for k,v in st.session_state["codex"].items()])
            if codex: sys += f"【设定集】{codex}\n"
            sys += "\n【铁律】1. 第一行Markdown标题。2. 严禁废话。"

            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":user_in})
            with box:
                st.chat_message("user", avatar="🧑‍💻").write(user_in)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys}]+msgs, stream=True)
                    resp = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":resp})

    # --- 右侧：外挂 ---
    if use_split and col_a:
        with col_a:
            st.info("🧩 灵感外挂")
            with st.expander("🔮 剧情预测", True):
                if st.button("🎲 预测", key="btn_pred"):
                    recent = "".join([m["content"] for m in msgs[-3:]])
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"基于剧情：{recent[-800:]}，给出3个分支。"}])
                    st.info(r.choices[0].message.content)
            with st.expander("📛 起名助手"):
                t = st.selectbox("类型", ["配角", "反派", "宗门", "宝物"], key="sel_name_type")
                if st.button("🎲 生成", key="btn_gen_name"):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"生成5个{st.session_state['global_genre']}风格的{t}。"}])
                    st.write(r.choices[0].message.content)
            with st.expander("📜 细纲参考"):
                st.text_area("只读", st.session_state["bp_outline_res"], height=200, disabled=True, key="area_outline_ref")

# --- TAB 2: 创世蓝图 (修复版) ---
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图")
    st.info("💡 提示：输入灵感 -> 生成结果。如果不满意，在下方输入意见点击重写。")
    
    plan_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】不要输出'好的'。直接输出策划内容。"
    )

    # === 1. 核心脑洞 ===
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    idea_in = st.text_area("✍️ 输入灵感", value=st.session_state.get("bp_idea_input", ""), height=100, key="bp_in_idea")
    
    c_b1, c_b2 = st.columns([1, 3])
    if c_b1.button("✨ 生成脑洞", key="btn_gen_idea"):
        st.session_state["bp_idea_input"] = idea_in
        with st.spinner("构思中..."):
            p = f"基于点子“{idea_in}”，写一个核心梗，200字内。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            resp = st.write_stream(stream)
            st.session_state["bp_idea_res"] = resp
            st.rerun()

    if st.session_state["bp_idea_res"]:
        st.markdown("---")
        st.session_state["bp_idea_res"] = st.text_area("✅ 脑洞结果 (可修改)", st.session_state["bp_idea_res"], height=150, key="bp_res_idea_area")
        
        c_f1, c_f2 = st.columns([3, 1])
        idea_fb = c_f1.text_input("🗣️ 修改意见", placeholder="如：再反转一下", key="in_fb_idea")
        if c_f2.button("🔄 重写", key="btn_rw_idea"):
            with st.spinner("重写中..."):
                p = f"当前脑洞：{st.session_state['bp_idea_res']}。\n修改意见：{idea_fb}。\n请重写。要求：保持简练，200字以内，不要写多余标题。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
                resp = st.write_stream(stream)
                st.session_state["bp_idea_res"] = resp
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 2. 角色档案 ===
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_c1, c_c2 = st.columns([1, 4])
    if c_c1.button("👥 生成人设", key="btn_gen_char"):
        if not st.session_state["bp_idea_res"]: st.error("请先生成脑洞！")
        else:
            p = f"基于脑洞：{st.session_state['bp_idea_res']}。生成男女主档案。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            resp = st.write_stream(stream)
            st.session_state["bp_char_res"] = resp
            st.rerun()

    if st.session_state["bp_char_res"]:
        st.markdown("---")
        st.session_state["bp_char_res"] = st.text_area("✅ 人设结果 (可修改)", st.session_state["bp_char_res"], height=200, key="bp_res_char_area")
        
        c_fc1, c_fc2 = st.columns([3, 1])
        char_fb = c_fc1.text_input("🗣️ 人设意见", placeholder="如：男主太弱了", key="in_fb_char")
        if c_fc2.button("🔄 重写", key="btn_rw_char"):
            with st.spinner("重写中..."):
                p = f"当前人设：{st.session_state['bp_char_res']}。\n修改意见：{char_fb}。\n请重写。要求：只输出档案，不要废话。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
                resp = st.write_stream(stream)
                st.session_state["bp_char_res"] = resp
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 3. 剧情细纲 ===
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_o1, c_o2 = st.columns([1, 4])
    if c_o1.button("📜 生成细纲", key="btn_gen_out"):
        if not st.session_state["bp_char_res"]: st.error("请先生成人设！")
        else:
            p = f"脑洞：{st.session_state['bp_idea_res']}。\n人设：{st.session_state['bp_char_res']}。\n生成前三章细纲。严禁客套话。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
            resp = st.write_stream(stream)
            st.session_state["bp_outline_res"] = resp
            st.rerun()

    if st.session_state["bp_outline_res"]:
        st.markdown("---")
        st.session_state["bp_outline_res"] = st.text_area("✅ 细纲结果 (可修改)", st.session_state["bp_outline_res"], height=300, key="bp_res_out_area")
        
        c_fo1, c_fo2 = st.columns([3, 1])
        out_fb = c_fo1.text_input("🗣️ 细纲意见", placeholder="如：节奏太慢", key="in_fb_out")
        if c_fo2.button("🔄 重写", key="btn_rw_out"):
            with st.spinner("重写中..."):
                p = f"当前细纲：{st.session_state['bp_outline_res']}。\n修改意见：{out_fb}。\n请重写。要求：只调整内容，不要长篇大论。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":plan_sys},{"role":"user","content":p}], stream=True)
                resp = st.write_stream(stream)
                st.session_state["bp_outline_res"] = resp
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: 灵感工具箱 (修复 ID 冲突) ---
with tab_tools:
    st.info("🛠️ 经典工具箱")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎬 万能场面")
        t = st.selectbox("类型", ["⚔️ 战斗", "💖 感情", "👻 恐怖", "😎 装逼"], key="old_scene_type")
        d = st.text_input("描述", placeholder="如：壁咚", key="old_scene_desc")
        if st.button("生成场面", key="btn_old_scene"):
            p = f"写一段{t}。内容：{d}。300字。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.text_area("结果", r.choices[0].message.content, height=200, key="old_scene_res")
    with c2:
        st.markdown("### 📟 系统生成")
        i = st.text_input("提示语", placeholder="获得神器", key="old_sys_in")
        # ⚠️ 之前就是这里报错，现在加了 key="btn_old_system"
        if st.button("生成", key="btn_old_system"):
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
    st.text_area("预览", cl[:500]+"...", height=200, disabled=True, key="pub_preview")
    st.download_button("📥 下载全书 (TXT)", cl, "novel.txt", key="dl_txt")
    
    if st.button("🎁 分章 ZIP", key="btn_zip"):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                z.writestr(f"Chapter_{ch}.txt", clean("".join([m["content"] for m in msgs if m["role"]=="assistant"])))
        st.download_button("下载 ZIP", b.getvalue(), "chapters.zip", mime="application/zip", key="dl_zip")
    
    bk = {
        "conf": {"genre": st.session_state["global_genre"], "tone": st.session_state["global_tone"]}, 
        "ch": st.session_state["chapters"], 
        "bp": [st.session_state["bp_idea_res"], st.session_state["bp_char_res"], st.session_state["bp_outline_res"]]
    }
    st.download_button("💊 备份 JSON", json.dumps(bk, ensure_ascii=False), "backup.json", key="dl_backup")