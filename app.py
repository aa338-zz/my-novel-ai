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
        # --- 核心写作数据 ---
        "chapters": {1: []},       
        "current_chapter": 1,      
        
        # --- 数据库 ---
        "codex": {},               
        "scrap_yard": [],          
        
        # --- 用户状态 ---
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        
        # --- 备战区数据 ---
        "context_buffer": "",      
        "mimic_style": "",         
        
        # --- 创世蓝图数据 (独立存储) ---
        "bp_idea_input": "",       # 脑洞输入
        "bp_idea_res": "",         # 脑洞结果
        "bp_char_res": "",         # 人设结果
        "bp_outline_res": "",      # 细纲结果
        
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
    
    /* 按钮增强 */
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 6px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
    }
    
    /* 输入框聚焦样式 */
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #228be6;
        box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    /* 章节标题头 */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    /* 蓝图区域容器 */
    .blueprint-box {
        border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; 
        background: white; margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* 引导卡片 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    
    /* 系统提示框 */
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
            st.markdown("<p style='text-align: center; color: gray;'>V 4.2 稳定正式版</p>", unsafe_allow_html=True)
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

    # --- 全局书籍设置 ---
    st.markdown("### 📚 世界观基石")
    with st.container():
        # A. 小说类型
        genre_options = [
            "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
            "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
            "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
            "女频 | 豪门爽文", "自定义类型..."
        ]
        selected_genre = st.selectbox("小说类型", genre_options, index=0)
        
        if selected_genre == "自定义类型...":
            custom_genre = st.text_input("✍️ 请输入类型", value="克苏鲁修仙")
            st.session_state["global_genre"] = custom_genre
        else:
            st.session_state["global_genre"] = selected_genre.split("|")[0].strip()
        
        # B. 核心基调
        tone_options = [
            "热血 / 王道 / 爽文", "暗黑 / 压抑 / 生存", "轻松 / 搞笑 / 吐槽", 
            "悬疑 / 烧脑 / 反转", "治愈 / 情感 / 细腻", "自定义基调..."
        ]
        selected_tone = st.selectbox("核心基调", tone_options, index=0)
        
        if selected_tone == "自定义基调...":
            custom_tone = st.text_input("✍️ 请输入基调", value="慢热、群像")
            st.session_state["global_tone"] = custom_tone
        else:
            st.session_state["global_tone"] = selected_tone
        
        # C. 其他设置
        st.session_state["global_world_bg"] = st.text_input("世界背景", placeholder="如：蒸汽朋克大明")
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名", "西方译名", "日式轻小说", "古风雅韵"])

    st.divider()

    # --- 仪表盘 ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    st.markdown(f"**🔥 今日码字** ({current_text_len} / {st.session_state['daily_target']})")
    st.progress(min(current_text_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: 
        if st.button("⏪", help="撤销"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.toast("撤销成功")
                st.rerun()

    # --- 设定集 & 废稿篓 ---
    with st.expander("📕 设定集"):
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕ 录入"):
            st.session_state["codex"][new_term] = new_desc; st.success("已录")
        st.markdown("---")
        for k, v in st.session_state["codex"].items(): st.markdown(f"**{k}**: {v}")

    with st.expander("🗑️ 废稿篓"):
        scrap = st.text_area("暂存", height=60)
        if st.button("📥 存"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", s, height=60, key=f"scr_{i}")
                if st.button(f"删 #{i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i); st.rerun()

# ==========================================
# 4. 新手引导
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br><h1 style='text-align: center; color: #228be6;'>✨ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>功能全开 · 续写神器 · 格式无忧</p><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.info("🛠️ 全局设置：支持自定义"); c2.info("🗺️ 蓝图：支持流式生成与重写"); c3.info("🤐 写作：支持分栏对照")
    if st.button("🚀 开始创作", type="primary", use_container_width=True):
        st.session_state["first_visit"] = False
        st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区 Tabs
# ==========================================
tab_write, tab_blueprint, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🗺️ 创世蓝图", "🔮 灵感工具箱", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 (完整版) ---
with tab_write:
    # 1. 备战区
    with st.expander("🎬 备战区：素材投喂 (续写/仿写)", expanded=True):
        c_prep1, c_prep2 = st.columns([1, 1])
        with c_prep1:
            st.markdown("#### 📄 导入旧稿")
            uploaded_ctx = st.file_uploader("上传TXT", type=["txt"])
            if uploaded_ctx:
                raw_text = uploaded_ctx.getvalue().decode("utf-8")
                st.session_state["context_buffer"] = raw_text[-2000:]
                st.success(f"✅ 已装载旧稿 (末尾2000字)")
        with c_prep2:
            st.markdown("#### 🧬 仿写文风")
            uploaded_sty = st.file_uploader("上传样章", type=["txt"])
            if uploaded_sty and st.button("🧠 提取文风"):
                with st.spinner("分析中..."):
                    p = f"分析文风：{uploaded_sty.getvalue().decode('utf-8')[:3000]}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风提取成功")

    # 2. 导演控制台
    st.markdown("<div class='director-control-box'>", unsafe_allow_html=True)
    st.markdown("#### 🎚️ 导演控制台")
    c_d1, c_d2, c_d3, c_d4 = st.columns(4)
    with c_d1: plot_phase = st.selectbox("剧情状态", ["✨ AI 自动把控", "🌊 铺垫", "🔥 推进", "💥 高潮", "❤️ 收尾"])
    with c_d2: desc_focus = st.selectbox("描写侧重", ["🎲 均衡", "👁️ 画面", "🗣️ 对话", "🧠 心理", "👊 动作"])
    with c_d3: view_point = st.selectbox("视角", ["第三人称", "第一人称"])
    with c_d4: burst_mode = st.toggle("💥 注水模式", False, help="开启后 AI 会疯狂扩写细节")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    use_split_view = st.toggle("📖 对照模式 (开启右侧外挂)", value=True)
    
    if use_split_view: col_write, col_assist = st.columns([7, 3])
    else: col_write = st.container(); col_assist = st.empty()

    # --- 左侧：核心写作 ---
    with col_write:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        msg_container = st.container(height=600)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with msg_container:
            for msg in current_msgs:
                st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"]=="user" else "🖊️").write(msg["content"])

        # 精修面板
        with st.expander("🛠️ 快速精修"):
            t_f1, t_f2 = st.tabs(["局部润色", "重写本章"])
            with t_f1:
                bad = st.text_input("粘贴片段")
                if st.button("✨ 润色") and bad:
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                    st.write_stream(stream)
            with t_f2:
                req = st.text_input("重写要求")
                if st.button("💥 重写"):
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"指令：重写本章。要求：{req}"})
                    st.rerun()

        # 违禁词雷达
        c_tool1, c_tool2 = st.columns([1, 1])
        with c_tool1:
            with st.expander("🛡️ 违禁词雷达"):
                if st.button("🔍 扫描"):
                    risky = ["杀人", "死", "血", "恐怖", "色情", "政治", "自杀"] 
                    txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                    found = [w for w in risky if w in txt]
                    if found: 
                        for w in set(found): txt = txt.replace(w, f":red[**{w}**]")
                        st.markdown(txt)
                    else: st.success("✅ 安全")
        with c_tool2:
            last_msg = ""
            for m in reversed(current_msgs):
                if m["role"]=="assistant": last_msg = m["content"]; break
            if last_msg:
                with st.expander("📋 复制"):
                    st.text_area("复制框", last_msg, height=100)

        st.markdown("---")
        user_input = st.chat_input("输入剧情...")
        if user_input:
            # System Prompt
            sys_p = (
                f"你是由DeepSeek驱动的作家。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"背景：{st.session_state['global_world_bg']}。起名：{st.session_state['global_naming']}。\n"
                f"视角：{view_point}。\n"
            )
            if plot_phase != "✨ AI 自动把控": sys_p += f"【强制要求】状态：{plot_phase}。\n"
            if desc_focus != "🎲 均衡": sys_p += f"【强制要求】侧重：{desc_focus}。\n"
            if burst_mode: sys_p += "【扩写要求】强力注水模式，大量细节。\n"
            if st.session_state["mimic_style"]: sys_p += f"【文风模仿】{st.session_state["mimic_style"]}\n"
            if st.session_state["context_buffer"]: sys_p += f"【前文接龙】{st.session_state["context_buffer"]}\n"
            codex_str = "; ".join([f"{k}:{v}" for k,v in st.session_state["codex"].items()])
            if codex_str: sys_p += f"【设定集】{codex_str}\n"
            sys_p += "\n【铁律】1. 输出第一行必须是Markdown二级标题 (## 章节名)。2. 严禁废话。"

            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":user_input})
            with msg_container:
                st.chat_message("user", avatar="🧑‍💻").write(user_input)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system", "content":sys_p}] + current_msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # --- 右侧：外挂 ---
    if use_split_view and col_assist:
        with col_assist:
            st.info("🧩 灵感外挂")
            with st.expander("🔮 剧情预测", True):
                if st.button("🎲 预测走向"):
                    recent = "".join([m["content"] for m in current_msgs[-3:]])
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"基于剧情：{recent[-800:]}，给出3个分支。"}])
                    st.info(r.choices[0].message.content)
            with st.expander("📛 起名助手"):
                t = st.selectbox("类型", ["配角", "反派", "宗门", "宝物"])
                if st.button("🎲 生成"):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":f"生成5个{st.session_state['global_genre']}风格的{t}。"}])
                    st.write(r.choices[0].message.content)
            with st.expander("📜 细纲参考"):
                st.text_area("只读", st.session_state["bp_outline_res"], height=200, disabled=True)

# --- TAB 2: 创世蓝图 (修复版：流式 + 严控字数) ---
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图 (Ideation)")
    st.info("✨ 支持流式生成。输入框与结果已分离。")
    
    # 核心 Prompt
    planner_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】不要输出'好的'。直接输出策划内容。"
    )

    # === 1. 核心脑洞 ===
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # [Input]
    bp_idea_in = st.text_area("✍️ 输入你的原始灵感", value=st.session_state.get("bp_idea_input", ""), height=100, key="idea_in_main")
    
    c_b1, c_b2 = st.columns([1, 3])
    generate_idea = c_b1.button("✨ 生成/完善脑洞")
    
    if generate_idea:
        st.session_state["bp_idea_input"] = bp_idea_in # 保存输入
        with st.spinner("AI 正在构思..."):
            p = f"基于点子“{bp_idea_in}”，完善成一个有吸引力的核心梗，200字内。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_idea_res"] = response
            st.rerun()

    # [Result & Feedback]
    if st.session_state["bp_idea_res"]:
        st.markdown("---")
        st.session_state["bp_idea_res"] = st.text_area("✅ 脑洞结果 (可修改)", st.session_state["bp_idea_res"], height=150)
        
        col_fb1, col_fb2 = st.columns([3, 1])
        idea_feedback = col_fb1.text_input("🗣️ 不满意？给 AI 提意见 (如：反转再多点)", key="fb_idea")
        if col_fb2.button("🔄 根据意见重写"):
             with st.spinner("重写中..."):
                # 🔥🔥🔥 修复点：加入字数限制，防止废话 🔥🔥🔥
                p = f"当前脑洞：{st.session_state['bp_idea_res']}。\n修改意见：{idea_feedback}。\n请重写。要求：保持简练，200字以内，不要写多余的标题。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
                response = st.write_stream(stream)
                st.session_state["bp_idea_res"] = response
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 2. 角色档案 ===
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_c1, c_c2 = st.columns([1, 4])
    if c_c1.button("👥 生成/重置人设"):
        if not st.session_state["bp_idea_res"]:
            st.error("请先生成脑洞！")
        else:
            p = f"基于脑洞：{st.session_state['bp_idea_res']}。生成男女主档案。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_char_res"] = response
            st.rerun()

    if st.session_state["bp_char_res"]:
        st.markdown("---")
        st.session_state["bp_char_res"] = st.text_area("✅ 人设结果 (可修改)", st.session_state["bp_char_res"], height=200)
        
        col_fb_c1, col_fb_c2 = st.columns([3, 1])
        char_feedback = col_fb_c1.text_input("🗣️ 人设意见 (如：男主太弱了)", key="fb_char")
        if col_fb_c2.button("🔄 重写人设"):
             # 🔥🔥🔥 修复点：限制废话 🔥🔥🔥
             p = f"当前人设：{st.session_state['bp_char_res']}。\n修改意见：{char_feedback}。\n请重写。只输出档案本身，不要废话。"
             stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
             response = st.write_stream(stream)
             st.session_state["bp_char_res"] = response
             st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 3. 剧情细纲 ===
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_o1, c_o2 = st.columns([1, 4])
    if c_o1.button("📜 生成/重置细纲"):
        if not st.session_state["bp_char_res"]:
            st.error("请先生成人设！")
        else:
            p = f"脑洞：{st.session_state['bp_idea_res']}。\n人设：{st.session_state['bp_char_res']}。\n生成前三章细纲。严禁客套话。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
            response = st.write_stream(stream)
            st.session_state["bp_outline_res"] = response
            st.rerun()

    if st.session_state["bp_outline_res"]:
        st.markdown("---")
        st.session_state["bp_outline_res"] = st.text_area("✅ 细纲结果 (可修改)", st.session_state["bp_outline_res"], height=300)
        
        col_fb_o1, col_fb_o2 = st.columns([3, 1])
        out_feedback = col_fb_o1.text_input("🗣️ 细纲意见 (如：节奏太慢)", key="fb_out")
        if col_fb_o2.button("🔄 重写细纲"):
             # 🔥🔥🔥 修复点：限制废话 🔥🔥🔥
             p = f"当前细纲：{st.session_state['bp_outline_res']}。\n修改意见：{out_feedback}。\n请重写。要求：只调整需要修改的部分，不要写太长，300字以内。"
             stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}], stream=True)
             response = st.write_stream(stream)
             st.session_state["bp_outline_res"] = response
             st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 3: 灵感工具箱 ---
with tab_tools:
    st.info("🛠️ 经典工具箱")
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        st.markdown("### 🎬 万能场面")
        s_type = st.selectbox("类型", ["⚔️ 战斗", "💖 感情", "👻 恐怖", "😎 装逼"])
        s_desc = st.text_input("描述", placeholder="如：壁咚")
        if st.button("生成场面"):
            p = f"写一段{s_type}。内容：{s_desc}。300字。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.text_area("结果", r.choices[0].message.content, height=200)
    with c_t2:
        st.markdown("### 📟 系统生成")
        sys_i = st.text_input("提示语", placeholder="获得神器")
        if st.button("生成"):
            st.markdown(f"""<div class="system-box">【系统】{sys_i}</div>""", unsafe_allow_html=True)

# --- TAB 4: 发书控制台 ---
with tab_publish:
    st.markdown("### 🚀 发书控制台")
    # 聚合
    full_text = ""
    for ch, msgs in st.session_state["chapters"].items():
        txt = "".join([m["content"] for m in msgs if m["role"] == "assistant"])
        full_text += f"\n\n### 第 {ch} 章 ###\n\n{txt}"
    
    # 清洗
    def clean(t):
        t = t.replace("**", "").replace("##", "")
        t = re.sub(r'#+\s*', '', t)
        lines = [f"　　{l.strip()}" for l in t.split('\n') if l.strip()]
        return "\n\n".join(lines)
    
    cl_txt = clean(full_text)
    st.text_area("预览", cl_txt[:500]+"...", height=200, disabled=True)
    st.download_button("📥 下载全书 (TXT)", cl_txt, "novel.txt")
    
    # 打包
    if st.button("🎁 分章 ZIP"):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                z.writestr(f"Chapter_{ch}.txt", clean("".join([m["content"] for m in msgs if m["role"]=="assistant"])))
        st.download_button("下载 ZIP", b.getvalue(), "chapters.zip", mime="application/zip")
    
    # 备份
    bk = {
        "conf": {"genre": st.session_state["global_genre"], "tone": st.session_state["global_tone"]}, 
        "ch": st.session_state["chapters"], 
        "bp": [st.session_state["bp_idea_res"], st.session_state["bp_char_res"], st.session_state["bp_outline_res"]]
    }
    st.download_button("💊 备份 JSON", json.dumps(bk, ensure_ascii=False), "backup.json")