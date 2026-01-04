import streamlit as st
from openai import OpenAI
import json
import io
import zipfile
import re # 导入正则库用于高亮替换

# ==========================================
# 0. 全局配置
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
        "last_generated_text": "" # 新增：用于一键复制
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
    .login-logo {
        font-size: 80px; text-align: center; margin-bottom: 20px;
        animation: breathe 3s infinite ease-in-out;
    }
    @keyframes breathe {
        0% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
        50% { transform: scale(1.1); opacity: 1; text-shadow: 0 0 25px #228be6; }
        100% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
    }
    /* 红色高亮样式 */
    .risky-word {
        background-color: #ffe3e3;
        color: #c92a2a;
        font-weight: bold;
        padding: 2px 4px;
        border-radius: 4px;
        border: 1px solid #ffa8a8;
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
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown('<div class="login-logo">⚡</div>', unsafe_allow_html=True)
            with st.form("login"):
                st.markdown("<h3 style='text-align:center'>创世笔 V3</h3>", unsafe_allow_html=True)
                user = st.text_input("账号", placeholder="用户名", label_visibility="collapsed")
                st.write("")
                pwd = st.text_input("密码", type="password", placeholder="密钥 (666)", label_visibility="collapsed")
                st.write("")
                if st.form_submit_button("🚀 进入工作室", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：核心控制
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎：在线")
    else:
        api_key = st.text_input("输入 API Key", type="password")
        if not api_key: st.stop()
            
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 章节控制
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
            st.toast("已回退", icon="↩️")
            st.rerun()

    # --- 设定集 & 废稿篓 (保持原有功能，节省篇幅折叠) ---
    with st.expander("📕 设定集 (Codex)"):
        new_term = st.text_input("新词条", placeholder="词条名")
        new_desc = st.text_input("描述", placeholder="具体设定")
        if st.button("➕ 收录"): st.session_state["codex"][new_term] = new_desc

    with st.expander("🗑️ 废稿篓"):
        scrap = st.text_area("暂存", height=60)
        if st.button("📥 存"): st.session_state["scrap_yard"].append(scrap)

    st.divider()
    st.markdown("### 🧠 大脑控制台")
    
    # 3.1 扩展的类型库
    genre_list = [
        "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
        "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
        "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
        "游戏 | 第四天灾", "女频 | 豪门爽文", "女频 | 宫斗宅斗", "自定义"
    ]
    t_sel = st.selectbox("📚 小说类型", genre_list)
    novel_type = st.text_input("自定义类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel.split("|")[0]
    
    perspective = st.selectbox("👁️ 视角", ["第三人称 (上帝)", "第一人称 (我)"], index=0)

    st.markdown("---")
    
    # 3.2 强力参数
    writing_style = st.select_slider("🎭 文风", options=["极简", "正常", "华丽", "暗黑", "幽默"], value="正常")
    
    word_target = st.number_input("🎯 单次字数", 500, 5000, 1500, 100, help="设大一点，AI 会写得更长")
    
    # 强力扩写：直接影响 System Prompt
    burst_mode = st.toggle("💥 强力注水模式 (冲字数专用)", value=True, help="开启后，AI 会疯狂描写环境和心理，防止写太短。")

# ==========================================
# 4. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools = st.tabs(["✍️ 沉浸写作", "🚀 流水线", "🔮 外挂"])

# --- TAB 1: 沉浸写作 (修复版) ---
with tab_write:
    st.subheader(f"📖 第 {st.session_state.current_chapter} 章")
    
    # 构建 Prompt
    ctx = ""
    if st.session_state.get("pipe_outline"): ctx += f"\n【本章大纲】{st.session_state['pipe_outline']}"
    if st.session_state.get("codex"): ctx += f"\n【设定】{str(st.session_state['codex'])}"
    
    # 🔥 修复字数问题的核心指令
    length_instruction = ""
    if burst_mode:
        length_instruction = (
            f"【强力扩写指令】目标字数：{word_target}+。严禁流水账！"
            "必须使用‘慢镜头’写法。每发生一个动作，必须描写周围的环境（光影、声音、气味）和角色的微表情。"
            "多用比喻。如果字数不够，就增加人物的内心独白。"
        )
    else:
        length_instruction = f"字数目标：{word_target}。"

    sys_p = (
        f"你是由DeepSeek驱动的网文作家。类型：{novel_type}。视角：{perspective}。文风：{writing_style}。\n"
        f"{ctx}\n\n"
        f"【执行要求】\n{length_instruction}\n"
        "禁止输出‘好的’、‘以下是内容’等废话，直接开始写正文。"
    )

    # 聊天记录
    container = st.container(height=400)
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 🔥 修复功能区：雷达 & 复制
    c_tool1, c_tool2 = st.columns([1, 1])
    
    with c_tool1:
        # 🛡️ 敏感词高亮修复版
        with st.expander("🛡️ 敏感词雷达 (点击扫描)", expanded=False):
            if st.button("🔍 扫描本章全文"):
                risky_words = ["杀人", "死", "血", "恐怖", "色情", "政府", "自杀", "爆炸", "毒"]
                full_text = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                
                # 检查逻辑
                found_risks = [w for w in risky_words if w in full_text]
                
                if not found_risks:
                    st.success("✅ 未发现敏感词")
                else:
                    st.error(f"⚠️ 发现敏感词：{', '.join(set(found_risks))}")
                    # 高亮逻辑：使用 Markdown 的颜色语法
                    highlighted_text = full_text
                    for w in set(found_risks):
                        # 替换为红色加粗
                        highlighted_text = highlighted_text.replace(w, f":red[**{w}**]")
                    
                    st.markdown("### 🚩 问题定位：")
                    st.markdown(highlighted_text) # 直接渲染高亮后的文本

    with c_tool2:
        # 📋 一键复制修复版
        # 使用 st.code 显示最后一段生成的内容，自带复制按钮
        last_ai_msg = ""
        for m in reversed(current_msgs):
            if m["role"] == "assistant":
                last_ai_msg = m["content"]
                break
        
        if last_ai_msg:
            with st.expander("📋 一键复制 (最新段落)", expanded=True):
                st.caption("点击右上角📄图标即可复制")
                st.code(last_ai_msg, language=None)

    # 输入区
    c_input, c_btn = st.columns([5, 1])
    with c_input:
        manual_plot = st.text_input("💡 剧情指令", placeholder="例如：反派突然出现，手里拿着枪")
    with c_btn:
        st.write("")
        st.write("")
        btn_cont = st.button("🔄 续写", use_container_width=True)

    if prompt := st.chat_input("输入剧情..."):
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user").write(prompt)
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True, temperature=1.3)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    if btn_cont:
        p = f"接着写。{manual_plot}" if manual_plot else "接着上文继续写，保持连贯，多写细节。"
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":p})
        with container:
            st.chat_message("user").write(p)
            with st.chat_message("assistant"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}] + current_msgs, stream=True, temperature=1.3)
                response = st.write_stream(stream)
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 流水线 (大纲修复版) ---
with tab_pipeline:
    st.info("AI 策划师模式")
    
    # 修复：明确要求标题格式
    planner_prompt = "你是一个网文策划。**输出必须结构清晰**。不要写正文。"

    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        idea = st.text_input("核心梗")
        if st.button("✨ 生成梗"):
            p = f"为{novel_type}构思一个梗：{idea}。要求：新奇、有冲突。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_idea"] = r.choices[0].message.content
    if st.session_state["pipe_idea"]: st.text_area("结果", st.session_state["pipe_idea"])

    with st.expander("Step 2: 大纲 (已修复标题丢失)", expanded=True):
        if st.button("📜 生成细纲"):
            # 🔥 这里的 Prompt 修改了，强制要求格式
            p = (
                f"核心梗：{st.session_state['pipe_idea']}。\n"
                "请生成前3章的详细细纲。\n"
                "**重要格式要求**：\n"
                "每一章必须有具体的章节名！格式如下：\n"
                "**第一章：[章节名]**\n"
                "1. [剧情点1]\n"
                "2. [剧情点2]\n\n"
                "**第二章：[章节名]**\n"
                "..."
            )
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_prompt}, {"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)

# --- TAB 3: 外挂 ---
with tab_tools:
    st.write("🔧 实用工具")
    if st.button("🧹 清理缓存 (重置)"):
        st.session_state.clear()
        st.rerun()