import streamlit as st
from openai import OpenAI
import json
import random

# ==========================================
# 0. 全局配置
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🖊️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 极简高对比度 CSS ---
st.markdown("""
<style>
    .stApp {background-color: #ffffff; color: #000000;}
    section[data-testid="stSidebar"] {background-color: #f5f5f7; border-right: 1px solid #d1d1d6;}
    
    .stButton>button {
        background-color: #0071e3; color: white !important; border-radius: 8px; border: none; font-weight: 600;
    }
    .stButton>button:hover {background-color: #0077ed; transform: translateY(-1px);}
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput input {
        background-color: #ffffff; color: #000000; border: 1px solid #c7c7cc; border-radius: 8px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0,113,227,0.2);
    }

    .stChatMessage {background-color: #fbfbfb; border: 1px solid #e5e5ea; border-radius: 12px; padding: 15px;}
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {background-color: #f2f2f7; border-radius: 6px; border: none; font-weight: 600;}
    .stTabs [aria-selected="true"] {background-color: #0071e3 !important; color: white !important;}

    /* 侧边栏小工具样式 */
    .sidebar-tool {
        background: #eef1f5; padding: 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #ddd;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 初始化
if "chapters" not in st.session_state: st.session_state["chapters"] = {1: []}
if "current_chapter" not in st.session_state: st.session_state["current_chapter"] = 1
if "characters" not in st.session_state: st.session_state["characters"] = [] 
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "style_sample" not in st.session_state: st.session_state["style_sample"] = ""
if "memo" not in st.session_state: st.session_state["memo"] = ""

# 风格与流水线暂存
if "mimic_style" not in st.session_state: st.session_state["mimic_style"] = "" 
if "mimic_analysis" not in st.session_state: st.session_state["mimic_analysis"] = ""
if "pipe_idea" not in st.session_state: st.session_state["pipe_idea"] = ""
if "pipe_char" not in st.session_state: st.session_state["pipe_char"] = ""
if "pipe_world" not in st.session_state: st.session_state["pipe_world"] = ""
if "pipe_outline" not in st.session_state: st.session_state["pipe_outline"] = ""

# ==========================================
# 1. 登录
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.markdown("<br><br><h1 style='text-align: center; color:#333;'>🖊️ 创世笔 Pro</h1>", unsafe_allow_html=True)
            with st.form("login"):
                if st.form_submit_button("进入工作室", use_container_width=True):
                    st.session_state["logged_in"] = True
                    st.rerun()
        st.stop()
check_login()

# ==========================================
# 2. 侧边栏 (升级版：全能指挥塔)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 核心控制")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎在线")
    else:
        st.error("🔴 未配置 Key")
        st.stop()
    
    st.divider()

    # --- 功能 1: 章节导航 ---
    col_nav1, col_nav2 = st.columns([2, 1])
    with col_nav1:
        target_chap = st.number_input("章节跳转", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with col_nav2:
        st.caption(f"当前: 第{st.session_state.current_chapter}章")
        txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
        st.caption(f"{len(txt)} 字")

    st.divider()

    # --- 🔥 功能 2: 侧边栏小工具集 (Toolbox) ---
    st.markdown("### 🛠️ 快捷工具")
    
    with st.expander("📝 灵感便签 (Memo)", expanded=True):
        st.session_state["memo"] = st.text_area("memo", value=st.session_state["memo"], height=120, label_visibility="collapsed", placeholder="记录伏笔、灵感、待办...")

    with st.expander("🎲 取名神器 (随机)"):
        name_type = st.selectbox("风格", ["玄幻古风", "现代都市", "西方奇幻"], label_visibility="collapsed")
        if st.button("生成名字"):
            # 简单的本地随机库，不浪费 API
            if name_type == "玄幻古风":
                names = ["萧炎", "林动", "叶凡", "顾清寒", "楚晚宁", "墨燃", "洛璃", "云韵"]
                st.info(f"名字：{random.choice(names)}")
            elif name_type == "现代都市":
                names = ["陆薄言", "顾漫", "苏明玉", "安迪", "陈孝正", "郑微"]
                st.info(f"名字：{random.choice(names)}")
            else:
                names = ["哈利", "赫敏", "克莱恩", "奥黛丽", "阿尔萨斯", "吉安娜"]
                st.info(f"名字：{random.choice(names)}")
    
    with st.expander("🛡️ 违禁词自查"):
        # 简单的模拟检测
        check_text = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
        if st.button("扫描本章"):
            risky_words = ["杀人", "血腥", "恐怖", "死"] # 模拟词库
            found = [w for w in risky_words if w in check_text]
            if found:
                st.warning(f"⚠️ 发现敏感词：{', '.join(found)}")
            else:
                st.success("✅ 本章内容安全")

    with st.expander("🎵 沉浸白噪音"):
        sound_type = st.radio("环境音", ["雨夜", "咖啡馆", "键盘声"], index=0)
        # 这里用模拟的文字展示，因为没有真实音频文件链接
        if st.toggle("播放 (模拟)"):
            st.caption(f"正在播放：{sound_type}.mp3 ... 🌧️")
            st.progress(100)

    st.divider()
    
    # 设定区
    st.markdown("### ⚙️ 参数")
    novel_types = [
        "末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化",
        "玄幻 | 东方玄幻", "都市 | 异术超能", "历史 | 架空历史",
        "悬疑 | 规则怪谈", "无限流 | 诸天万界", "女频 | 宫斗"
    ]
    novel_type = st.selectbox("类型", novel_types)
    word_target = st.select_slider("字数", options=["短", "中", "长"], value="中")
    burst_mode = st.toggle("水字数模式", value=True)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 3. 主界面
# ==========================================
tab_write, tab_clone, tab_pipeline, tab_review = st.tabs(["✍️ 沉浸写作", "🧬 风格克隆", "🚀 创作流水线", "💾 审稿/导出"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 顶部状态
    if st.session_state["mimic_analysis"]:
        st.success(f"🧬 文风模仿已开启")

    with st.expander("📂 导入 / 续写"):
        old_file = st.file_uploader("上传旧稿续写", type=["txt"])
        if old_file and st.button("📥 导入"):
            content = old_file.getvalue().decode("utf-8")
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "user", "content": f"前文：\n{content}"})
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "assistant", "content": "✅ 前文已阅。"})
            st.rerun()

    # System Prompt
    pipeline_context = ""
    if st.session_state["pipe_char"]: pipeline_context += f"\n【角色】{st.session_state['pipe_char']}"
    if st.session_state["pipe_world"]: pipeline_context += f"\n【世界】{st.session_state['pipe_world']}"
    if st.session_state["pipe_outline"]: pipeline_context += f"\n【大纲】{st.session_state['pipe_outline']}"
    
    instruction = f"字数目标：{word_target}。"
    if burst_mode: instruction += "【扩写模式】必须详细描写。"
    style_instruction = ""
    if st.session_state['mimic_analysis']:
        style_instruction = f"【模仿文风】\n{st.session_state['mimic_analysis']}"

    system_prompt = f"""
    你是由DeepSeek驱动的专业作家。
    类型：{novel_type}
    {pipeline_context}
    {style_instruction}
    {instruction}
    禁止说“好的”，直接写正文。
    """

    container = st.container(height=500)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content_show = msg["content"]
            if len(content_show) > 500 and "前文" in content_show: content_show = content_show[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content_show)

    c_input, c_btn = st.columns([6, 1])
    user_input = None
    with c_input:
        if prompt := st.chat_input("输入剧情..."): user_input = prompt
    with c_btn:
        st.write("") 
        st.write("") 
        if st.button("🔄 继续写", use_container_width=True): user_input = "接着写，保持连贯。"

    if user_input:
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":user_input})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(user_input)
            with st.chat_message("assistant", avatar="🖊️"):
                with st.spinner("码字中..."):
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"system","content":system_prompt}] + current_msgs,
                        stream=True, temperature=1.2
                    )
                    response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 风格克隆 ---
with tab_clone:
    st.info("上传样本，提取文风。")
    col_up, col_res = st.columns(2)
    with col_up:
        style_file = st.file_uploader("上传样本 (.txt)", type=["txt"])
        if style_file:
            raw_text = style_file.getvalue().decode("utf-8")[:3000]
            if st.button("🧠 提取灵魂"):
                with st.spinner("分析中..."):
                    p = f"分析风格：\n{raw_text}\n总结叙事视角、句式节奏、用词习惯。"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["mimic_style"] = raw_text
                    st.session_state["mimic_analysis"] = res.choices[0].message.content
                    st.rerun()
    with col_res:
        if st.session_state["mimic_analysis"]:
            st.success("✅ 提取成功")
            st.text_area("特征", value=st.session_state["mimic_analysis"], height=300)

# --- TAB 3: 创作流水线 ---
with tab_pipeline:
    st.info("生成 -> 修改 -> 确认。")
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3, 1])
        raw_idea = c1.text_input("点子：")
        if c2.button("生成梗"):
            p = f"基于点子“{raw_idea}”，为{novel_type}完善核心梗。100字。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_idea"] = res.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_idea"]:
        st.session_state["pipe_idea"] = st.text_area("✅ 脑洞", value=st.session_state["pipe_idea"], height=100)

    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        if st.button("生成人设"):
            p = f"基于梗“{st.session_state['pipe_idea']}”，生成主角和反派。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_char"] = res.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_char"]:
        st.session_state["pipe_char"] = st.text_area("✅ 人设", value=st.session_state["pipe_char"], height=200)

    with st.expander("Step 3: 世界", expanded=bool(st.session_state["pipe_char"])):
        if st.button("生成世界"):
            p = f"基于{novel_type}，生成世界观。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_world"] = res.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_world"]:
        st.session_state["pipe_world"] = st.text_area("✅ 世界", value=st.session_state["pipe_world"], height=150)

    with st.expander("Step 4: 大纲", expanded=bool(st.session_state["pipe_world"])):
        if st.button("生成细纲"):
            p = f"梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。世界：{st.session_state['pipe_world']}。生成黄金三章细纲。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_outline"] = res.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_outline"]:
        st.session_state["pipe_outline"] = st.text_area("✅ 大纲", value=st.session_state["pipe_outline"], height=300)

# --- TAB 4: 审稿 ---
with tab_review:
    if st.button("🔍 毒舌审稿"):
        txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        if len(txt)<50: st.warning("字数太少")
        else:
            p = f"毒舌点评：\n{txt}"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.info(res.choices[0].message.content)
    data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
    st.download_button("📥 导出全书", json.dumps(data, ensure_ascii=False), "novel.json")