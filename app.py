import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 强力初始化 (State Management)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    # 这里初始化了所有的变量，确保新老功能都能正常运行，不会报错
    defaults = {
        # --- 核心写作数据 ---
        "chapters": {1: []},       # 章节内容字典
        "current_chapter": 1,      # 当前章节号
        "history_snapshots": [],   # 历史撤销快照
        
        # --- 数据库 ---
        "codex": {},               # 设定集 (词条:描述)
        "scrap_yard": [],          # 废稿篓 (列表)
        
        # --- 用户状态 ---
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "init_done": True,
        
        # --- 备战区数据 (Tab 1) ---
        "context_buffer": "",      # 续写模式的前文缓存
        "mimic_style": "",         # 仿写模式的文风缓存
        
        # --- 创世蓝图数据 (Tab 2 - 独立存储以支持反复编辑) ---
        # 1. 脑洞部分
        "bp_idea_input": "",       # 用户的灵感输入
        "bp_idea_res": "",         # AI生成的脑洞结果
        # 2. 人设部分
        "bp_char_res": "",         # AI生成的人设结果
        # 3. 细纲部分
        "bp_outline_res": "",      # AI生成的细纲结果
        
        # --- 旧版流水线兼容变量 (防止旧版逻辑报错) ---
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_world": "",
        "pipe_outline": "",
        
        # --- 全局设置 (Tab Sidebar) ---
        "global_genre": "东方玄幻",
        "global_tone": "热血 / 王道",
        "global_naming": "东方中文名",
        "global_world_bg": ""
    }
    
    # 遍历并初始化
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (CSS - 完整保留原版并增强)
# ==========================================
st.markdown("""
<style>
    /* 全局背景与字体 */
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff; 
        border-right: 1px solid #e0e0e0;
    }
    
    /* 按钮样式增强 */
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    /* 输入框聚焦样式 */
    .stTextInput>div>div>input:focus {
        border-color: #228be6;
        box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    /* 新手引导卡片样式 */
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .guide-card:hover {
        transform: translateY(-5px);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    .guide-desc {color: #868e96; font-size: 14px; line-height: 1.5;}
    
    /* 系统生成框样式 (旧版工具箱) */
    .system-box {
        background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%);
        border: 2px solid #339af0; border-radius: 8px; padding: 15px;
        color: #1864ab; font-family: 'Courier New', monospace; font-weight: bold;
    }
    
    /* === 新增功能样式 === */
    
    /* 章节标题头 */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    /* 导演控制台容器 */
    .director-control-box {
        background-color: #e7f5ff; border-left: 5px solid #339af0;
        padding: 15px; border-radius: 4px; margin-bottom: 20px;
    }
    
    /* 蓝图区域容器 */
    .blueprint-box {
        border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; 
        background: white; margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (保留原版)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>V 4.0 交互完美修正版</p>", unsafe_allow_html=True)
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
# 3. 侧边栏：指挥塔 (全局设置 + 导航)
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

    # --- 1. 全局书籍设置 (修复：自定义输入框) ---
    st.markdown("### 📚 世界观基石")
    with st.container():
        st.info("在此定义本书的底层逻辑。")
        
        # A. 小说类型 (支持自定义)
        genre_options = [
            "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
            "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
            "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
            "女频 | 豪门爽文", "自定义类型..."
        ]
        selected_genre = st.selectbox("小说类型", genre_options, index=0)
        
        # 逻辑：如果选了自定义，显示输入框
        if selected_genre == "自定义类型...":
            custom_genre = st.text_input("✍️ 请输入自定义类型", value="克苏鲁修仙")
            st.session_state["global_genre"] = custom_genre
        else:
            st.session_state["global_genre"] = selected_genre.split("|")[0].strip()
        
        # B. 核心基调 (支持自定义)
        tone_options = [
            "热血 / 王道 / 爽文", 
            "暗黑 / 压抑 / 生存", 
            "轻松 / 搞笑 / 吐槽", 
            "悬疑 / 烧脑 / 反转", 
            "治愈 / 情感 / 细腻", 
            "自定义基调..."
        ]
        selected_tone = st.selectbox("核心基调", tone_options, index=0)
        
        if selected_tone == "自定义基调...":
            custom_tone = st.text_input("✍️ 请输入自定义基调", value="慢热、群像、史诗感")
            st.session_state["global_tone"] = custom_tone
        else:
            st.session_state["global_tone"] = selected_tone
        
        # C. 其他设置
        st.session_state["global_world_bg"] = st.text_input("世界背景 (简述)", placeholder="如：蒸汽朋克大明")
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名 (萧炎)", "西方译名 (艾伦)", "日式轻小说 (佐藤)", "古风雅韵 (纳兰)"])

    st.divider()

    # --- 2. 仪表盘 & 导航 (保留) ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    # 计算 assistant 回复的总字数
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    
    st.markdown(f"**🔥 今日码字** ({current_text_len} / {st.session_state['daily_target']})")
    st.progress(min(current_text_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: 
        if st.button("⏪", help="撤销最后一次对话"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.toast("时光倒流成功", icon="↩️")
                st.rerun()

    st.divider()

    # --- 3. 设定集 (保留在底部) ---
    with st.expander("📕 设定集 (Codex)"):
        st.caption("防止 AI 吃书，在此记录专有名词")
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕ 录入设定"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已录")
        st.markdown("---")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    # --- 4. 废稿篓 (保留在底部) ---
    with st.expander("🗑️ 废稿篓 (Scrap Yard)"):
        scrap = st.text_area("暂存", height=60, placeholder="写废的段落扔这里...")
        if st.button("📥 存入"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")
                if st.button(f"❌ 删 {i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i)
                    st.rerun()

# ==========================================
# 4. 新手引导 (保留原版文案)
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
            <div class="guide-title">备战与设定</div>
            <div class="guide-desc"><b>[侧边栏]</b> 配置世界观基调（支持自定义）。<br><b>[写作区顶部]</b> 投喂旧稿或样章。</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">✍️</span>
            <div class="guide-title">沉浸与外挂</div>
            <div class="guide-desc"><b>[写作区]</b> 开启分栏模式。<br>左边写书，右边实时获取<b>剧情预测</b>与<b>润色灵感</b>。</div>
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
        if st.button("🚀 开始创作 (Bug修复版)", type="primary", use_container_width=True):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区 Tabs
# ==========================================
tab_write, tab_blueprint, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🗺️ 创世蓝图", "🔮 灵感工具箱", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    
    # 1. 备战区 (Import & Mimic)
    with st.expander("🎬 备战区：素材投喂 (续写/仿写)", expanded=True):
        c_prep1, c_prep2 = st.columns([1, 1])
        
        # 功能 A：续写
        with c_prep1:
            st.markdown("#### 📄 导入旧稿续写")
            uploaded_ctx = st.file_uploader("上传TXT", type=["txt"], key="ctx_up_main")
            if uploaded_ctx:
                raw_text = uploaded_ctx.getvalue().decode("utf-8")
                st.session_state["context_buffer"] = raw_text[-2000:]
                st.success(f"✅ 已装载旧稿！AI 将记忆最后 2000 字。")

        # 功能 B：仿写
        with c_prep2:
            st.markdown("#### 🧬 导入大神样章仿写")
            uploaded_sty = st.file_uploader("上传样章", type=["txt"], key="sty_up_main")
            if uploaded_sty and st.button("🧠 提取文风 DNA"):
                with st.spinner("正在分析文风..."):
                    sample_txt = uploaded_sty.getvalue().decode("utf-8")[:3000]
                    r = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"user", "content":f"请专业分析这段文字的文风（句式长短、形容词密度、叙事视角），总结为写作指南：\n\n{sample_txt}"}]
                    )
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风滤镜已激活！")

    # 2. 导演控制台 (Director Control)
    st.markdown("<div class='director-control-box'>", unsafe_allow_html=True)
    st.markdown("#### 🎚️ 导演控制台")
    c_dir1, c_dir2, c_dir3, c_dir4 = st.columns(4)
    with c_dir1:
        plot_phase = st.selectbox("剧情状态", ["✨ AI 自动把控节奏", "🌊 铺垫/日常", "🔥 推进/解谜", "💥 高潮/冲突", "❤️ 情感/收尾"], index=0)
    with c_dir2:
        desc_focus = st.selectbox("描写侧重", ["🎲 均衡/随机", "👁️ 画面/光影", "🗣️ 对话/交锋", "🧠 心理/内省", "👊 动作/招式"], index=0)
    with c_dir3:
        view_point = st.selectbox("叙事视角", ["第三人称 (上帝)", "第一人称 (我)"])
    with c_dir4:
        burst_mode = st.toggle("💥 强力注水模式", value=False, help="开启后 AI 会疯狂扩写细节")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # 3. 分栏模式逻辑
    use_split_view = st.toggle("📖 开启对照模式 (左侧写作 | 右侧灵感外挂)", value=True)
    
    if use_split_view:
        col_write, col_assist = st.columns([7, 3])
    else:
        col_write = st.container()
        col_assist = st.empty()

    # --- 左侧：核心写作区 ---
    with col_write:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        
        # 消息容器
        msg_container = st.container(height=600)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with msg_container:
            if not current_msgs: 
                st.info(f"✨ 准备就绪。设定：{st.session_state['global_genre']} | 基调：{st.session_state['global_tone']}")
            
            for msg in current_msgs:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
                content = msg["content"]
                st.chat_message(msg["role"], avatar=avatar).write(content)

        # 随手精修面板
        with st.expander("🛠️ 快速精修 (润色/重写)"):
            t_fix1, t_fix2 = st.tabs(["✍️ 局部润色", "💥 本章重写"])
            with t_fix1:
                c_f1, c_f2 = st.columns(2)
                bad_frag = c_f1.text_area("粘贴片段", height=100)
                fix_req = c_f2.text_area("修改要求", height=100)
                if st.button("✨ 润色片段") and bad_frag:
                    p = f"修改片段：{bad_frag}\n要求：{fix_req}\n风格：{st.session_state['global_tone']}。\n直接输出修改后的内容。"
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                    st.write_stream(stream)
            with t_fix2:
                re_req = st.text_input("重写要求", placeholder="如：节奏太慢了，直接进入高潮")
                if st.button("💥 推翻重写本章"):
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"【指令】重写本章，要求：{re_req}。"})
                    st.rerun()

        # 违禁词雷达
        if st.button("🛡️ 扫描违禁词"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政治", "自杀"] 
            txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            found = [w for w in risky if w in txt]
            if found: st.error(f"发现敏感词：{found}")
            else: st.success("✅ 内容安全")

        st.markdown("---")
        
        # 核心写作输入区
        user_input = st.chat_input("输入剧情简述...")
        
        if user_input:
            # 构建 System Prompt
            sys_p = (
                f"你是由DeepSeek驱动的网文作家。\n"
                f"【全局设定】类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"世界背景：{st.session_state['global_world_bg']}。起名风格：{st.session_state['global_naming']}。\n"
                f"【基础参数】视角：{view_point}。\n"
            )
            
            # 导演指令
            if plot_phase != "✨ AI 自动把控节奏": sys_p += f"【强制要求】剧情节奏：{plot_phase}。\n"
            if desc_focus != "🎲 均衡/随机": sys_p += f"【强制要求】描写侧重：{desc_focus}。\n"
            if burst_mode: sys_p += "【扩写要求】强力注水模式：必须大量描写环境、光影、气味、微表情。\n"

            # 注入素材
            if st.session_state["mimic_style"]: sys_p += f"【文风模仿】\n{st.session_state['mimic_style']}\n"
            if st.session_state["context_buffer"]: sys_p += f"【前文接龙】\n{st.session_state['context_buffer']}\n"
            
            # 注入设定集
            codex_str = "; ".join([f"{k}:{v}" for k,v in st.session_state["codex"].items()])
            if codex_str: sys_p += f"【已知设定】{codex_str}\n"

            # 格式铁律
            sys_p += "\n【铁律】1. 输出第一行必须是Markdown二级标题 (## 章节名)。2. 严禁输出'好的'等废话。"

            # 发送请求
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":user_input})
            with msg_container:
                st.chat_message("user", avatar="🧑‍💻").write(user_input)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"system", "content":sys_p}] + current_msgs,
                        stream=True
                    )
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # --- 右侧：灵感外挂 ---
    if use_split_view and col_assist:
        with col_assist:
            st.info("🧩 灵感外挂")
            
            # 剧情罗盘
            with st.expander("🔮 剧情罗盘 (预测)", expanded=True):
                if st.button("🎲 接下来写啥？"):
                    recent_ctx = "".join([m["content"] for m in current_msgs[-3:]])
                    p = f"基于以下剧情：\n{recent_ctx[-800:]}\n\n给出3个有趣的后续发展分支。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.info(r.choices[0].message.content)

            # 起名助手
            with st.expander("📛 起名助手"):
                name_type = st.selectbox("类型", ["配角名", "反派名", "宗门", "宝物"])
                if st.button("🎲 生成"):
                    p = f"根据风格【{st.session_state['global_naming']}】和类型【{st.session_state['global_genre']}】，生成5个{name_type}。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)

            # 扩写笔
            with st.expander("💄 扩写/润色"):
                raw_s = st.text_input("输入短句")
                if st.button("🪄 润色") and raw_s:
                    p = f"润色句子“{raw_s}”。风格：{st.session_state['global_tone']}。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)
            
            # 细纲查看
            with st.expander("📜 细纲参考"):
                st.text_area("内容", st.session_state["bp_outline_res"], height=200, disabled=True)

# --- TAB 2: 创世蓝图 (交互修复版：输入/输出分离 + 反复编辑) ---
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图 (Ideation)")
    st.info("💡 修复说明：输入框和结果框已分离。你可以修改输入重新生成，也可以修改生成结果。")
    
    planner_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】不要输出'好的'、'需要我继续吗'。直接输出策划内容。"
    )

    # === 1. 核心脑洞 ===
    st.markdown("#### 1️⃣ 核心脑洞")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    # 输入框 (绑定 session_state 以便持久化)
    user_idea = st.text_input("💡 你的灵感 (可反复修改)", value=st.session_state.get("bp_idea_input", ""))
    st.session_state["bp_idea_input"] = user_idea # 更新状态
    
    c_b1, c_b2 = st.columns([1, 2])
    if c_b1.button("✨ 生成/完善脑洞"):
        with st.spinner("AI 构思中..."):
            p = f"基于点子“{user_idea}”，完善成一个有吸引力的核心梗，200字内。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
            st.session_state["bp_idea_res"] = r.choices[0].message.content
            st.rerun()

    # 结果框 (只有生成后才显示)
    if st.session_state["bp_idea_res"]:
        st.markdown("---")
        st.text_area("生成结果 (可手动编辑保存)", st.session_state["bp_idea_res"], height=150, key="res_editor_idea")
        
        # 反馈修改逻辑 (Feedback Loop)
        idea_feedback = st.text_input("🗣️ 不满意？给 AI 提意见 (如：反转再多点)", key="fb_idea")
        if c_b2.button("🔄 根据意见重写"):
             with st.spinner("重写中..."):
                p = f"当前脑洞：{st.session_state['bp_idea_res']}。\n修改意见：{idea_feedback}。\n请重写。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
                st.session_state["bp_idea_res"] = r.choices[0].message.content
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 2. 角色档案 ===
    st.markdown("#### 2️⃣ 角色档案")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_c1, c_c2 = st.columns([1, 2])
    if c_c1.button("👥 生成/重置人设"):
        if not st.session_state["bp_idea_res"]:
            st.error("请先生成脑洞！")
        else:
            with st.spinner("捏人中..."):
                p = f"基于脑洞：{st.session_state['bp_idea_res']}。生成男女主档案。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
                st.session_state["bp_char_res"] = r.choices[0].message.content
                st.rerun()

    if st.session_state["bp_char_res"]:
        st.markdown("---")
        st.text_area("人设结果 (可手动编辑保存)", st.session_state["bp_char_res"], height=200, key="res_editor_char")
        
        char_feedback = st.text_input("🗣️ 人设修改意见 (如：男主要更腹黑)", key="fb_char")
        if c_c2.button("🔄 根据意见重写人设"):
             with st.spinner("重写中..."):
                p = f"当前人设：{st.session_state['bp_char_res']}。\n修改意见：{char_feedback}。\n请重写。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
                st.session_state["bp_char_res"] = r.choices[0].message.content
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # === 3. 剧情细纲 ===
    st.markdown("#### 3️⃣ 剧情细纲")
    st.markdown("<div class='blueprint-box'>", unsafe_allow_html=True)
    
    c_o1, c_o2 = st.columns([1, 2])
    if c_o1.button("📜 生成/重置细纲"):
        if not st.session_state["bp_char_res"]:
            st.error("请先生成人设！")
        else:
            with st.spinner("推演剧情..."):
                p = f"脑洞：{st.session_state['bp_idea_res']}。\n人设：{st.session_state['bp_char_res']}。\n生成前三章细纲。严禁客套话。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
                # 简单过滤结尾废话
                clean_res = r.choices[0].message.content.replace("需要我继续吗？", "").replace("您觉得如何？", "")
                st.session_state["bp_outline_res"] = clean_res
                st.rerun()

    if st.session_state["bp_outline_res"]:
        st.markdown("---")
        st.text_area("细纲结果 (可手动编辑保存)", st.session_state["bp_outline_res"], height=300, key="res_editor_out")
        
        outline_feedback = st.text_input("🗣️ 细纲修改意见 (如：第一章节奏太慢)", key="fb_outline")
        if c_o2.button("🔄 根据意见重写细纲"):
             with st.spinner("重写中..."):
                p = f"当前细纲：{st.session_state['bp_outline_res']}。\n修改意见：{outline_feedback}。\n请重写。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
                st.session_state["bp_outline_res"] = r.choices[0].message.content
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# --- TAB 3: 灵感工具箱 (旧版保留) ---
with tab_tools:
    st.info("🛠️ 经典工具箱 (旧版功能保留)")
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
    st.info("一键清洗 Markdown 符号，自动排版，支持分章打包。")
    
    # 1. 聚合全书
    full_text_raw = ""
    for ch, msgs in st.session_state["chapters"].items():
        ch_txt = "".join([m["content"] for m in msgs if m["role"] == "assistant"])
        full_text_raw += f"\n\n### 第 {ch} 章 ###\n\n{ch_txt}"
        
    # 2. 清洗算法
    def clean_novel_format(text):
        text = text.replace("**", "")
        text = re.sub(r'#+\s*', '', text)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        formatted = [f"　　{line}" for line in lines]
        return "\n\n".join(formatted)

    clean_content = clean_novel_format(full_text_raw)
    
    # 3. 界面展示
    c_pub1, c_pub2 = st.columns([2, 1])
    with c_pub1:
        st.markdown("#### 👁️ 纯净预览")
        st.text_area("预览", clean_content[:1000] + "...", height=400, disabled=True)
        
    with c_pub2:
        st.markdown("#### 💾 导出操作")
        st.download_button("📥 下载全书 (TXT)", clean_content, "novel.txt", type="primary")
        
        if st.button("🎁 分章打包 (ZIP)"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ch, msgs in st.session_state["chapters"].items():
                    raw_c = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
                    clean_c = clean_novel_format(raw_c)
                    zip_file.writestr(f"Chapter_{ch}.txt", clean_c)
            st.download_button("点击保存 ZIP", zip_buffer.getvalue(), "chapters.zip", mime="application/zip")
            
        st.markdown("---")
        
        # 备份
        backup_data = {
            "config": {"genre": st.session_state["global_genre"], "tone": st.session_state["global_tone"]},
            "chapters": st.session_state["chapters"],
            "codex": st.session_state["codex"],
            "blueprint": {"idea": st.session_state["bp_idea_res"], "char": st.session_state["bp_char_res"], "outline": st.session_state["bp_outline_res"]}
        }
        st.download_button("💊 完整备份 (JSON)", json.dumps(backup_data, ensure_ascii=False), "backup.json")