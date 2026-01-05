import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time
import datetime

# ==========================================
# 0. 全局配置 & 核心初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛠️ 强力初始化：确保每一个变量都存在，绝不报错
def init_session():
    # 基础数据结构
    defaults = {
        "chapters": {1: []},          # 章节存储
        "current_chapter": 1,         # 当前章节号
        "history_snapshots": [],      # 撤销历史
        # 5步流水线数据
        "pipe_idea": "",              # 脑洞
        "pipe_cheat": "",             # 金手指
        "pipe_level": "",             # 等级体系
        "pipe_char": "",              # 人设
        "pipe_outline": "",           # 大纲
        # 工具箱数据
        "codex": {},                  # 设定集 (字典)
        "scrap_yard": [],             # 废稿篓 (列表)
        "mimic_analysis": "",         # 文风模仿数据
        # 状态标记
        "logged_in": False,           # 登录状态
        "first_visit": True,          # 新手引导标记
        "daily_target": 3000,         # 每日字数目标
        # 全局写作参数 (五维控制)
        "global_novel_type": "玄幻爽文",
        "global_pov": "第三人称",
        "global_tone": "😐 严肃正剧",
        "global_pace": "🚀 爽文快节奏",
        "global_focus": "⚖️ 均衡模式",
        "global_word_limit": 1500,
        "global_burst_mode": True,
        "global_hook_mode": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (极光背景 + 磨砂玻璃 + 动画)
# ==========================================
st.markdown("""
<style>
    /* 1. 动态极光背景 (流体动画) */
    @keyframes gradientBG {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        color: #1a1a1a;
    }
    
    /* 2. 侧边栏：半透明磨砂白 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255,255,255,0.6);
        box-shadow: 2px 0 15px rgba(0,0,0,0.05);
    }

    /* 3. 强力汉化补丁 (覆盖上传框英文) */
    [data-testid='stFileUploader'] section {
        background-color: #f8f9fa;
        border: 1px dashed #4f46e5;
    }
    [data-testid='stFileUploader'] section > input + div { display: none !important; }
    [data-testid='stFileUploader'] section::after {
        content: "📄 点击或拖拽上传 TXT 文档";
        color: #4f46e5; font-weight: bold; display: block; text-align: center; padding: 10px;
    }
    [data-testid='stFileUploader'] small { display: none; }

    /* 4. 按钮美化 (蓝紫色渐变) */
    .stButton>button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
        transition: all 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    
    /* 5. 登录页火箭呼吸动画 */
    @keyframes breathe {
        0% { transform: scale(1); filter: drop-shadow(0 0 10px #4f46e5); }
        50% { transform: scale(1.1); filter: drop-shadow(0 0 25px #ec4899); }
        100% { transform: scale(1); filter: drop-shadow(0 0 10px #4f46e5); }
    }
    .rocket-logo {
        font-size: 100px; text-align: center; margin-bottom: 20px;
        animation: breathe 3s infinite ease-in-out;
        cursor: default;
    }

    /* 6. 磨砂卡片容器 */
    .glass-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        padding: 50px; border-radius: 24px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.4);
        text-align: center;
    }
    
    /* 7. 主内容区白底容器 */
    .main-container {
        background: rgba(255,255,255,0.95);
        border-radius: 16px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-top: 10px;
    }
    
    /* 8. 系统消息框 */
    .system-box {
        background: #f0f9ff; border-left: 5px solid #0ea5e9; 
        padding: 15px; border-radius: 4px; color: #0369a1; 
        font-family: monospace; font-weight: bold;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (火箭 + 密钥修复)
# ==========================================
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # 呼吸灯火箭
        st.markdown("<div class='rocket-logo'>🚀</div>", unsafe_allow_html=True)
        # 磨砂卡片
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='color:#333;'>创世笔 GENESIS</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#666;'>全能网文创作系统 V3.0 Ultimate</p>", unsafe_allow_html=True)
        
        with st.form("login"):
            pwd = st.text_input("通行密钥", type="password", placeholder="请输入 666", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 发射启动", use_container_width=True):
                # 修复逻辑：强制匹配字符串
                if str(pwd).strip() == "666":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("密钥错误 (提示: 666)")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. 侧边栏 (功能大满贯)
# ==========================================
with st.sidebar:
    st.markdown("### 🚀 创世笔 `Ultimate`")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
    else:
        st.error("请配置 Secrets API Key")
        st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 1. 仪表盘 (Dashboard)
    curr_msgs = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    words = len("".join([m["content"] for m in curr_msgs if m["role"]=="assistant"]))
    st.caption(f"🔥 本章字数: {words} / {st.session_state['daily_target']}")
    st.progress(min(words / st.session_state['daily_target'], 1.0))
    
    # 2. 章节与时光机
    c_ch1, c_ch2 = st.columns([2, 1])
    with c_ch1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c_ch2: st.caption("当前")
    
    if st.button("⏪ 撤销上一步 (Undo)", use_container_width=True):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("时光倒流成功", icon="↩️")
            st.rerun()

    st.markdown("---")

    # 3. 🧠 全局写作参数 (五维控制 - 修复版)
    with st.expander("🧠 全局写作参数 (控制台)", expanded=True):
        # 小说类型 (随时可改)
        genre_options = ["玄幻 | 东方玄幻", "都市 | 异术超能", "末世 | 囤货基地", "无限流 | 诸天万界", "悬疑 | 诡秘复苏", "自定义"]
        t_sel = st.selectbox("📚 类型", genre_options)
        if t_sel == "自定义":
            st.session_state["global_novel_type"] = st.text_input("输入类型", "克苏鲁修仙")
        else:
            st.session_state["global_novel_type"] = t_sel.split("|")[0]
            
        # 五维参数
        st.session_state["global_pov"] = st.selectbox("👁️ 视角", ["第三人称 (上帝)", "第一人称 (我)", "女主视角", "男主视角"])
        st.session_state["global_tone"] = st.select_slider("🎭 基调", options=["严肃", "正常", "幽默", "暗黑", "轻松"], value="正常")
        st.session_state["global_pace"] = st.radio("⏱️ 节奏", ["🚀 快节奏 (爽文)", "🐢 慢节奏 (铺垫)"], index=0)
        st.session_state["global_focus"] = st.selectbox("⚖️ 侧重", ["均衡模式", "对话流", "描写流", "心理流"])
        
        st.session_state["global_word_limit"] = st.number_input("单次字数", 100, 5000, 800, 100)
        st.session_state["global_burst_mode"] = st.toggle("💥 强力扩写", value=True)
        st.session_state["global_hook_mode"] = st.toggle("🎣 结尾强制留钩子", value=False)

    # 4. 📂 档案室 (导入/文风 - 修复版)
    with st.expander("📂 档案室 (导入/文风)"):
        t_arc1, t_arc2 = st.tabs(["📥 导入", "🧬 文风"])
        with t_arc1:
            up_draft = st.file_uploader("传TXT续写", type=["txt"], key="draft_up")
            if up_draft and st.button("确认导入"):
                c = up_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"读取旧稿：\n{c}"})
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":"✅ 已读取旧稿，请指示下一步。"})
                st.success("导入成功")
                st.rerun()
        with t_arc2:
            up_style = st.file_uploader("传大神作品", type=["txt"], key="style_up")
            if up_style and st.button("分析学习"):
                c = up_style.getvalue().decode("utf-8")[:1500]
                with st.spinner("正在解构文风..."):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析这段文字的文风（用词、节奏、叙事）：\n{c}"}])
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("文风已激活！")

    # 5. 📕 设定集 & 废稿
    with st.expander("📕 设定 / 🗑️ 废稿"):
        t_s1, t_s2 = st.tabs(["设定", "废稿"])
        with t_s1:
            k = st.text_input("词条名"); v = st.text_input("描述内容")
            if st.button("➕ 录入"): st.session_state["codex"][k]=v; st.success("已存")
            st.write(st.session_state["codex"])
        with t_s2:
            sc = st.text_area("存入片段", height=60)
            if st.button("📥 暂存"): st.session_state["scrap_yard"].append(sc)
            for i, txt in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", txt, height=60, key=f"s_{i}")

# ==========================================
# 4. 新手引导 (全屏大卡片)
# ==========================================
if st.session_state["first_visit"]:
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>🚀 欢迎回到驾驶舱</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: st.info("🧠 **流水线 (Tab 2)**\n\n5步构建：脑洞、金手指、世界、人设、大纲。");
    with c2: st.success("✍️ **沉浸写作 (Tab 1)**\n\n左侧调整参数，右侧实时生成。集成精修体检。");
    with c3: st.warning("💾 **发布 (Tab 4)**\n\n一键清洗、分章打包。");
    if st.button("开始创作", use_container_width=True): st.session_state["first_visit"] = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 5. 主工作区 (白底容器包裹)
# ==========================================
st.markdown('<div class="main-container">', unsafe_allow_html=True)

tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线 (5步)", "🔮 灵感外挂", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 (核心) ---
with tab_write:
    # 1. 组装超强 Prompt
    p = st.session_state
    context_block = ""
    if p["pipe_char"]: context_block += f"\n【角色档案】{p['pipe_char']}"
    if p["pipe_cheat"]: context_block += f"\n【金手指】{p['pipe_cheat']}"
    if p["pipe_level"]: context_block += f"\n【世界等级】{p['pipe_level']}"
    if p["pipe_outline"]: context_block += f"\n【大纲】{p['pipe_outline']}"
    if p["mimic_analysis"]: context_block += f"\n【模仿文风】{p['mimic_analysis']}"
    if p["codex"]: context_block += f"\n【设定集】{str(p['codex'])}"
    
    system_prompt = (
        f"你是由DeepSeek驱动的网文大神。类型：{p['global_novel_type']}。\n"
        f"【写作参数】视角：{p['global_pov']} | 基调：{p['global_tone']} | 节奏：{p['global_pace']} | 侧重：{p['global_focus']}\n"
        f"{context_block}\n"
        f"【指令】字数目标：{p['global_word_limit']}。{'请进行强力扩写，注重环境光影、动作细节、心理微表情。' if p['global_burst_mode'] else ''}\n"
        f"{'【注意】本段结尾必须留下强烈的悬念/钩子！' if p['global_hook_mode'] else ''}\n"
        f"禁止输出任何客套话，直接开始写正文。"
    )

    # 2. 聊天显示区
    container = st.container(height=500)
    history = st.session_state["chapters"][st.session_state.current_chapter]
    with container:
        for msg in history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🚀"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 3. 工具合体：精修 + 体检 + 雷达
    with st.expander("🛠️ 章节精修 / 体检 / 雷达"):
        t1, t2, t3 = st.tabs(["✍️ 润色重写", "🩺 章节体检", "🛡️ 违禁雷达"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                bad = st.text_area("片段", height=70, placeholder="粘贴写得不好的片段")
                req = st.text_input("润色要求")
                if st.button("✨ 润色"):
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色这段：{bad}。要求：{req}"}], stream=True)
                    st.write_stream(s)
            with c2:
                rf = st.text_input("整章重写要求")
                if st.button("💥 推翻重写"):
                    history.append({"role":"user", "content":f"重写本章：{rf}"})
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}]+history, stream=True)
                    r = st.write_stream(s)
                    history.append({"role":"assistant", "content":r})
        with t2:
            if st.button("🩺 生成体检报告"):
                full_t = "".join([m["content"] for m in history if m["role"]=="assistant"])
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"请作为专业编辑，点评以下章节的节奏、爽点、逻辑：\n{full_t}"}])
                st.info(r.choices[0].message.content)
        with t3:
            if st.button("🔍 扫描敏感词"):
                risky = ["杀人", "死", "血", "恐怖", "色情", "政府"]
                txt = "".join([m["content"] for m in history])
                found = [w for w in risky if w in txt]
                if found: st.error(f"发现：{found}")
                else: st.success("内容安全")

    # 4. 底部输入区
    st.divider()
    c_in, c_btn = st.columns([5, 1])
    with c_in: 
        manual = st.text_input("💡 剧情微操", placeholder="导演指令：如'主角突然发现宝箱'...", help="填了就强制执行，不填就自动续写")
    with c_btn:
        st.write(""); st.write("")
        if st.button("🔄 继续写", use_container_width=True):
            p_text = f"接着写。{'注意：'+manual if manual else ''}"
            history.append({"role":"user", "content":p_text})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(p_text)
                with st.chat_message("assistant", avatar="🚀"):
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}]+history, stream=True)
                    r = st.write_stream(s)
            history.append({"role":"assistant", "content":r})

    if prompt := st.chat_input("输入新剧情指令..."):
        history.append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🚀"):
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}]+history, stream=True)
                r = st.write_stream(s)
        history.append({"role":"assistant", "content":r})

# --- TAB 2: 流水线 (5步满血版) ---
with tab_pipeline:
    st.info("5步流水线：脑洞 -> 金手指 -> 世界 -> 人设 -> 大纲")
    planner = "你是一个网文策划。只写设定，字数300以内。"
    
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("核心点子")
        if st.button("✨ 生成梗"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"类型：{st.session_state['global_novel_type']}，点子：{idea}，生成梗"}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(s)
    
    with st.expander("Step 2: 金手指 (Cheat Code)"):
        if st.button("💍 设计金手指"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"基于{st.session_state['pipe_idea']}设计金手指"}], stream=True)
            st.session_state["pipe_cheat"] = st.write_stream(s)

    with st.expander("Step 3: 世界与等级"):
        if st.button("📈 铺设世界观"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"设计世界等级体系"}], stream=True)
            st.session_state["pipe_level"] = st.write_stream(s)

    with st.expander("Step 4: 人设"):
        if st.button("👥 生成人设"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"生成人设"}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(s)

    with st.expander("Step 5: 大纲"):
        if st.button("📜 生成细纲"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":f"生成前三章细纲"}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(s)

# --- TAB 3: 灵感外挂 (全) ---
with tab_tools:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎬 万能场面")
        t = st.selectbox("场面类型", ["打斗", "感情", "悬疑", "装逼"])
        d = st.text_input("描述场面")
        if st.button("生成场面"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"写一段{t}：{d}"}], stream=True)
            st.write_stream(s)
    with c2:
        st.markdown("#### 🎲 随机起名")
        nt = st.selectbox("起名类型", ["人名", "宗门", "功法", "地名"])
        if st.button("随机生成"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"生成5个{st.session_state['global_novel_type']}风格的{nt}"}])
            st.code(r.choices[0].message.content)
            
    st.divider()
    st.markdown("#### 🃏 命运卡牌 (解决卡文)")
    if st.button("抽一张剧情反转卡"):
        r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":"给一个意想不到的剧情转折灵感，一句话。"}])
        st.info(f"💡 灵感：{r.choices[0].message.content}")

# --- TAB 4: 导出控制台 ---
with tab_publish:
    at = ""
    for ch, msgs in st.session_state["chapters"].items():
        t = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        at += f"\n\n### 第 {ch} 章 ###\n\n{t}"
    
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        st.markdown("#### 🧹 纯净 TXT")
        st.download_button("📥 下载全书", at.replace("**","").replace("##",""), "novel.txt")
    with c_p2:
        st.markdown("#### 📦 分章 ZIP")
        if st.button("🎁 打包下载"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
                for ch, msgs in st.session_state["chapters"].items():
                    c = "".join([m["content"] for m in msgs if m["role"]=="assistant"]).replace("**","")
                    z.writestr(f"Chapter_{ch}.txt", c)
            st.download_button("📥 下载ZIP", buf.getvalue(), "chapters.zip", mime="application/zip")
    with c_p3:
        st.markdown("#### 💊 全数据备份")
        bk = {"chapters": st.session_state["chapters"], "codex": st.session_state["codex"], "scrap": st.session_state["scrap_yard"], "pipe": st.session_state["pipe_idea"]}
        st.download_button("📥 导出JSON", json.dumps(bk, ensure_ascii=False), "backup.json")

st.markdown('</div>', unsafe_allow_html=True)