import streamlit as st
from openai import OpenAI
import time
import json

# ==========================================
# 0. 全局配置 (赛博 UI 版)
# ==========================================
st.set_page_config(
    page_title="创世笔 GENESIS", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 核心美化 CSS 注入 (这是整容的关键) ---
st.markdown("""
<style>
    /* 1. 全局背景与字体 */
    .stApp {
        background-color: #0e1117; /* 深空灰背景 */
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #ffffff;
        font-weight: 700;
    }
    
    /* 2. 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background-color: #161b22; /* 稍微亮一点的深色 */
        border-right: 1px solid #30363d;
    }
    
    /* 3. 按钮变成“霓虹风格” */
    .stButton>button {
        background: linear-gradient(45deg, #2b5876, #4e4376);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(78, 67, 118, 0.6);
        background: linear-gradient(45deg, #4e4376, #2b5876);
    }

    /* 4. 输入框“毛玻璃”效果 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #0d1117;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #58a6ff;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.3);
    }

    /* 5. 聊天气泡美化 */
    .stChatMessage {
        background-color: #161b22;
        border-radius: 15px;
        padding: 10px;
        border: 1px solid #30363d;
        margin-bottom: 10px;
    }
    
    /* 6. Tabs 标签页美化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #161b22;
        border-radius: 5px;
        color: #8b949e;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important; /* 选中变绿 */
        color: white !important;
        font-weight: bold;
    }

    /* 隐藏右上角菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# 初始化记忆库
if "chapters" not in st.session_state:
    st.session_state["chapters"] = {1: []}
if "current_chapter" not in st.session_state:
    st.session_state["current_chapter"] = 1
if "characters" not in st.session_state:
    st.session_state["characters"] = [] 
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "style_sample" not in st.session_state:
    st.session_state["style_sample"] = ""

# ==========================================
# 1. 登录系统 (UI 美化版)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 

def check_login():
    if not st.session_state["logged_in"]:
        # 使用空的 container 居中布局
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; color: #58a6ff;'>⚡ GENESIS · 创世笔</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #8b949e;'>ULTIMATE WRITING ENGINE</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.markdown("### 身份验证")
                pwd = st.text_input("ACCESS KEY", type="password", placeholder="请输入密钥...")
                submit = st.form_submit_button("🚀 启动引擎 / LAUNCH")
                
                if submit:
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("⛔ ACCESS DENIED")
        st.stop()

check_login()

# ==========================================
# 2. 侧边栏 (控制台)
# ==========================================
with st.sidebar:
    st.markdown("## 🎛️ 控制中心")
    
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.caption("🟢 SYSTEM ONLINE")
    else:
        st.error("🔴 SYSTEM OFFLINE")
        st.stop()
    
    st.divider()
    
    # 章节导航
    col_c1, col_c2 = st.columns([2,1])
    with col_c1:
        chap_list = list(st.session_state.chapters.keys())
        selected_chap = st.selectbox("章节 / CHAPTER", chap_list, index=chap_list.index(st.session_state.current_chapter))
        if selected_chap != st.session_state.current_chapter:
            st.session_state.current_chapter = selected_chap
            st.rerun()
    with col_c2:
        st.markdown("<br>", unsafe_allow_html=True) # 稍微对齐一下
        if st.button("➕"):
            new = len(st.session_state.chapters)+1
            st.session_state.chapters[new] = []
            st.session_state.current_chapter = new
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⚙️ 参数设定")
    novel_type = st.selectbox("类型 / GENRE", ["玄幻爽文", "都市异能", "克苏鲁悬疑", "赛博朋克", "历史权谋"])
    temp = st.slider("疯魔指数 / TEMP", 0.1, 1.5, 1.2)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 3. 主界面 (Tabs)
# ==========================================
# 使用 emoji 增加视觉效果
tabs = st.tabs([
    "✍️ 写作", 
    "👁️ 感官", 
    "📊 节奏", 
    "🧬 风格", 
    "👨‍🏫 审稿", 
    "💾 数据"
])

# --- TAB 1: 沉浸写作 ---
with tabs[0]:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    char_info = "\n".join(st.session_state.characters) if st.session_state.characters else "暂无"
    style_prompt = f"【强制模仿文风】\n{st.session_state['style_sample']}" if st.session_state['style_sample'] else ""
    
    system_prompt = f"""
    你是由DeepSeek驱动的【创世笔】。
    【类型】{novel_type}
    【角色】{char_info}
    {style_prompt}
    【铁律】拒绝废话，拒绝AI味，直接写故事，要有爽点！
    """

    container = st.container(height=550) # 固定高度，让它像个聊天软件
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs:
            st.info("✨ 等待指令... (Waiting for input)")
        for msg in current_msgs:
            av = "🧑‍💻" if msg["role"] == "user" else "⚡"
            st.chat_message(msg["role"], avatar=av).write(msg["content"])

    # 输入框
    if prompt := st.chat_input("在此输入剧情指令..."):
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="⚡"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":system_prompt}] + current_msgs,
                    stream=True,
                    temperature=temp
                )
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 五感核弹 ---
with tabs[1]:
    st.markdown("#### 👁️ 五感扩写核弹")
    st.caption("输入一句平淡的描述，炸出 5 种感官细节。")
    
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        raw_text = st.text_input("输入句子", placeholder="例如：他很生气", label_visibility="collapsed")
    with col_btn:
        boom = st.button("💣 轰炸", use_container_width=True)
    
    if boom and raw_text:
        with st.spinner("🚀 核弹发射中..."):
            s_prompt = f"""
            用户输入："{raw_text}"
            扩写为5个维度的描写（不要解释，直接写句子）：
            1.【视觉】 2.【听觉】 3.【嗅觉/味觉】 4.【触觉】 5.【环境烘托】
            文风：{novel_type}
            """
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":s_prompt}])
            st.success("🎯 命中目标")
            st.markdown(res.choices[0].message.content)

# --- TAB 3: 节奏大师 ---
with tabs[2]:
    st.markdown("#### 📊 节奏与大纲")
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.info("📜 **黄金三章生成**")
        book_name = st.text_input("书名/脑洞")
        if st.button("生成开篇细纲", use_container_width=True):
            p_prompt = f"书名：{book_name}\n类型：{novel_type}\n生成网文黄金三章细纲，期待感拉满。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_prompt}])
            st.markdown(res.choices[0].message.content)
            
    with col_p2:
        st.info("🧱 **卡文急救**")
        if st.button("推演后续 3 种走向", use_container_width=True):
            last_text = current_msgs[-1]["content"] if current_msgs else "无前文"
            p_prompt2 = f"前文：{last_text[-200:]}\n给出三个后续：1.稳健流 2.反转流 3.虐主流"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_prompt2}])
            st.markdown(res.choices[0].message.content)

# --- TAB 4: 风格克隆 ---
with tabs[3]:
    st.markdown("#### 🧬 风格 DNA")
    user_sample = st.text_area("在此粘贴样本 (AI 将学习此文风):", value=st.session_state["style_sample"], height=200)
    if st.button("💉 注入文风 DNA", use_container_width=True):
        st.session_state["style_sample"] = user_sample
        st.toast("✅ 风格已融合！AI 现在的笔触跟你一样了。")

# --- TAB 5: 毒舌主编 ---
with tabs[4]:
    st.markdown("#### 👨‍🏫 毒舌主编")
    if st.button("🔍 审判当前章节", use_container_width=True):
        full_text = "\n".join([m["content"] for m in current_msgs if m["role"] == "assistant"])
        if len(full_text) < 50:
            st.warning("字数太少，写多点再来。")
        else:
            e_prompt = f"毒舌点评：\n{full_text}\n给评分(S/A/B/C)，指出3个硬伤，给建议。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":e_prompt}])
            st.markdown(res.choices[0].message.content)

# --- TAB 6: 数据中心 ---
with tabs[5]:
    st.markdown("#### 💾 资产管理")
    
    with st.expander("🦸‍♂️ RPG 角色卡生成", expanded=True):
        c_name = st.text_input("角色名")
        if st.button("✨ 生成属性面板"):
            c_prompt = f"为{novel_type}生成角色【{c_name}】面板。含：阵营、能力值、必杀技。用Emoji装饰。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":c_prompt}])
            st.session_state.characters.append(res.choices[0].message.content)
            st.success("已录入")
    
    if st.session_state.characters:
        st.code("\n\n".join(st.session_state.characters))

    st.divider()
    profile = {"style": st.session_state["style_sample"], "chars": st.session_state.characters, "history": st.session_state.chapters}
    st.download_button("📤 备份数据 (.json)", json.dumps(profile, ensure_ascii=False), "genesis_backup.json", use_container_width=True)
    
    uf = st.file_uploader("📥 恢复数据", type="json")
    if uf:
        d = json.load(uf)
        st.session_state.chapters = {int(k):v for k,v in d["history"].items()}
        st.session_state["style_sample"] = d["style"]
        st.session_state.characters = d["chars"]
        st.toast("数据已复活！")
