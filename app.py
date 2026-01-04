import streamlit as st
from openai import OpenAI
import json
import io
import zipfile

# ==========================================
# 0. 全局配置 & 初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 V3", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛠️ 强力初始化
def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_outline": "",
        "codex": {},
        "scrap_yard": [],
        "mimic_analysis": "", 
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "last_generated_text": "" # 用于一键复制
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600;
    }
    /* 红色高亮样式 */
    .risky-word {
        background-color: #ffe3e3; color: #c92a2a; font-weight: bold;
        padding: 2px 4px; border-radius: 4px; border: 1px solid #ffa8a8;
    }
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
            st.markdown("<br><br><h1 style='text-align:center'>⚡ 创世笔 V3</h1>", unsafe_allow_html=True)
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
# 3. 侧边栏：指挥塔 (修复增强版)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 神经网络：在线")
    else:
        # 允许手动输入 Key 方便调试
        api_key = st.text_input("输入 DeepSeek API Key", type="password")
        if not api_key: st.stop()
            
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 3.1 章节控制
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: st.caption(f"第 {st.session_state.current_chapter} 章")
    
    if st.button("⏪ 撤销上一步", use_container_width=True):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已撤销", icon="↩️")
            st.rerun()

    # --- 设定集 & 废稿篓 (折叠保持界面整洁) ---
    with st.expander("📕 设定集 (Codex)"):
        new_term = st.text_input("新词条", placeholder="词条名")
        new_desc = st.text_input("描述", placeholder="具体设定")
        if st.button("➕ 收录"): st.session_state["codex"][new_term] = new_desc

    st.divider()
    
    # ==========================================
    # 🔥 核心修复区：大脑控制台
    # ==========================================
    st.markdown("### 🧠 大脑控制台")
    
    # 1. 全面扩充的类型库
    genre_list = [
        "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
        "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
        "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
        "游戏 | 第四天灾", "女频 | 豪门爽文", "女频 | 宫斗宅斗", "短篇 | 脑洞故事", "自定义"
    ]
    t_sel = st.selectbox("📚 小说类型", genre_list)
    novel_type = st.text_input("自定义类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel.split("|")[0]
    
    # 2. 视角控制
    perspective = st.selectbox("👁️ 叙事视角", ["第三人称 (上帝视角)", "第一人称 (我)", "第二人称 (你)"], index=0)

    st.markdown("---")
    
    # 3. 进阶参数
    writing_style = st.select_slider("🎭 文风修饰", options=["极简白话", "幽默玩梗", "正常叙事", "辞藻华丽", "暗黑深沉"], value="正常叙事")
    
    pace_control = st.radio("⏱️ 叙事节奏", ["快速推进 (重剧情)", "平衡", "慢速沉浸 (重描写)"], index=1, horizontal=True)

    creativity = st.slider("🔥 创意温度 (严谨 <-> 脑洞)", 0.5, 1.5, 1.2, 0.1, help="值越大，AI 越敢写，但也可能乱写。")
    
    word_target = st.number_input("🎯 单次字数", 500, 5000, 1500, 100)
    burst_mode = st.toggle("💥 强力扩写 (注水模式)", value=True)

# ==========================================
# 4. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "🔮 外挂"])

# --- TAB 1: 沉浸写作 (修复版) ---
with tab_write:
    st.subheader(f"📖 第 {st.session_state.current_chapter} 章")
    
    # 构建 Prompt (加入所有新参数)
    ctx = ""
    if st.session_state.get("pipe_outline"): ctx += f"\n【本章大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("codex"): ctx += f"\n【世界观设定】{str(st.session_state['codex'])}"
    if st.session_state.get("mimic_analysis"): ctx += f"\n【模仿文风】{st.session_state['mimic_analysis']}"
    
    # 🔥 修复字数 & 标题问题的核心指令
    length_instruction = ""
    if burst_mode:
        length_instruction = "【强力扩写模式】必须大量描写环境（光影/声音/气味）和人物心理微表情，严禁记流水账。"
    
    sys_p = (
        f"你是由DeepSeek驱动的网文作家。类型：{novel_type}。视角：{perspective}。文风：{writing_style}。节奏：{pace_control}。\n"
        f"{ctx}\n\n"
        f"【执行铁律】\n"
        f"1. 每次输出**必须**以 markdown 格式的章节标题开头，例如：**### 章节名**\n"
        f"2. 字数目标：{word_target}+。{length_instruction}\n"
        "3. 禁止输出‘好的’、‘收到’，直接写正文。"
    )

    # 聊天记录显示
    container = st.container(height=450)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 🔥 功能修复区：雷达 & 复制
    c_tool1, c_tool2 = st.columns([1, 1])
    
    with c_tool1:
        # 🛡️ 敏感词高亮修复版
        with st.expander("🛡️ 违禁词雷达 (点击扫描)", expanded=False):
            if st.button("🔍 扫描本章全文"):
                # 这是一个模拟的词库，你可以自己加
                risky_words = ["杀人", "死", "血", "恐怖", "色情", "政府", "自杀", "爆炸", "毒", "违禁"]
                full_text = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                
                found_risks = [w for w in risky_words if w in full_text]
                
                if not found_risks:
                    st.success("✅ 未发现敏感词")
                else:
                    st.error(f"⚠️ 发现敏感词：{', '.join(set(found_risks))}")
                    # 高亮逻辑：使用 Streamlit 支持的颜色语法
                    highlighted_text = full_text
                    for w in set(found_risks):
                        highlighted_text = highlighted_text.replace(w, f":red[**{w}**]") # 标红加粗
                    
                    st.markdown("### 🚩 问题定位：")
                    st.markdown(highlighted_text) # 渲染高亮文本

    with c_tool2:
        # 📋 一键复制修复版
        last_ai_msg = ""
        for m in reversed(current_msgs):
            if m["role"] == "assistant":
                last_ai_msg = m["content"]
                break
        
        if last_ai_msg:
            with st.expander("📋 一键复制 (最新段落)", expanded=True):
                st.caption("👇 点击右上角的📄图标即可复制")
                # 使用 st.code 实现一键复制
                st.code(last_ai_msg, language=None)

    # 输入区
    c_input, c_btn = st.columns([5, 1])
    with c_input:
        manual_plot = st.text_input("💡 剧情指令", placeholder="例如：反派突然出现，手里拿着枪")
    with c_btn:
        st.write("")
        st.write("")
        btn_cont = st.button("🔄 续写", use_container_width=True)

    # 统一生成逻辑
    def generate_text(prompt_text):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt_text})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt_text)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=[{"role":"system","content":sys_p}] + current_msgs, 
                    stream=True, 
                    temperature=creativity # 动态温度
                )
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    if prompt := st.chat_input("输入剧情..."):
        generate_text(prompt)

    if btn_cont:
        p = f"接着写。{manual_plot}" if manual_plot else "接着上文继续写，保持连贯，多写细节。"
        generate_text(p)

# --- TAB 2: 流水线 (大纲修复版) ---
with tab_pipeline:
    st.info("AI 策划师模式")
    planner_prompt = "你是一个网文策划。**输出必须结构清晰**。不要写正文。"

    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("核心梗")
        if st.button("✨ 生成梗"):
            p = f"为{novel_type}构思一个梗：{idea}。要求：新奇、有冲突。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_idea"] = r.choices[0].message.content
    if st.session_state["pipe_idea"]: st.text_area("结果", st.session_state["pipe_idea"])

    with st.expander("Step 2: 大纲 (强制标题)", expanded=True):
        if st.button("📜 生成细纲"):
            # 🔥 强制 AI 输出标题格式
            p = (
                f"核心梗：{st.session_state['pipe_idea']}。\n"
                "请生成前3章的详细细纲。\n"
                "**重要格式要求**：\n"
                "每一章必须有具体的章节名！格式如下：\n"
                "**第一章：[章节名]**\n"
                "1. [剧情点1]\n"
                "2. [剧情点2]\n"
            )
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)

# --- TAB 3: 外挂 ---
with tab_tools:
    st.write("🔧 实用工具")
    if st.button("🧹 清理缓存 (重置)"):
        st.session_state.clear()
        st.rerun()