import streamlit as st
from openai import OpenAI
import json

# ==========================================
# 0. 全局配置 (极简白金版)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🖊️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 极简高对比度 CSS (护眼白) ---
st.markdown("""
<style>
    /* 全局纯白 */
    .stApp {background-color: #ffffff; color: #000000;}
    section[data-testid="stSidebar"] {background-color: #f5f5f7; border-right: 1px solid #d1d1d6;}
    
    /* 按钮：克莱因蓝 */
    .stButton>button {
        background-color: #0071e3; color: white !important; border-radius: 8px; border: none; font-weight: 600;
    }
    .stButton>button:hover {background-color: #0077ed; transform: translateY(-1px);}
    
    /* 输入框加深边框 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput input {
        background-color: #ffffff; color: #000000; border: 1px solid #c7c7cc; border-radius: 8px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #0071e3; box-shadow: 0 0 0 3px rgba(0,113,227,0.2);
    }

    /* 聊天气泡 */
    .stChatMessage {background-color: #fbfbfb; border: 1px solid #e5e5ea; border-radius: 12px; padding: 15px;}
    .stChatMessage[data-testid="user-message"] {background-color: #f2f2f7;}

    /* Tabs 优化 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {background-color: #f2f2f7; border-radius: 6px; border: none; font-weight: 600;}
    .stTabs [aria-selected="true"] {background-color: #0071e3 !important; color: white !important;}

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 初始化 Session (增加 pipeline 记忆)
if "chapters" not in st.session_state: st.session_state["chapters"] = {1: []}
if "current_chapter" not in st.session_state: st.session_state["current_chapter"] = 1
if "characters" not in st.session_state: st.session_state["characters"] = [] 
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "style_sample" not in st.session_state: st.session_state["style_sample"] = ""
if "memo" not in st.session_state: st.session_state["memo"] = ""

# 流水线数据暂存
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
# 2. 侧边栏
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 控制台")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎就绪 (DeepSeek)")
    else:
        st.error("🔴 未配置 Key")
        st.stop()
    
    st.divider()
    
    # 章节管理
    st.markdown("### 📖 章节管理")
    col_num, col_info = st.columns([2, 1])
    with col_num:
        target_chap = st.number_input("跳转/新建章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters:
                st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
            
    with col_info:
        st.write("")
        st.write("")
        st.caption(f"当前: {st.session_state.current_chapter}章")

    txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
    st.info(f"📊 本章字数: {len(txt)}")

    st.divider()
    st.markdown("### 📝 便签")
    st.session_state["memo"] = st.text_area("memo", value=st.session_state["memo"], height=150, label_visibility="collapsed", placeholder="随手记...")

    st.divider()
    novel_types = [
        "末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化",
        "玄幻 | 东方玄幻", "都市 | 异术超能", "历史 | 架空",
        "悬疑 | 规则怪谈", "无限流 | 诸天", "女频 | 宫斗"
    ]
    novel_type = st.selectbox("类型", novel_types)
    
    st.markdown("### 🌊 扩写模式")
    burst_mode = st.toggle("开启「水字数」模式", value=True)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 3. 主界面 (Tab 2 是核心改动)
# ==========================================
tab_write, tab_pipeline, tab_review = st.tabs(["✍️ 沉浸写作", "🚀 创作流水线 (新手引导)", "💾 审稿/导出"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 导入旧稿
    with st.expander("📂 导入旧稿 (txt)", expanded=False):
        uploaded_file = st.file_uploader("拖入文件", type=["txt"])
        if uploaded_file and st.button("确认导入"):
            stringio = uploaded_file.getvalue().decode("utf-8")
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "user", "content": f"前文：\n{stringio}"})
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "assistant", "content": "✅ 前文已阅。请继续。"})
            st.rerun()

    # System Prompt (结合流水线生成的内容)
    # 这里我们把流水线生成的内容，拼接到 System Prompt 里，让 AI 记住
    pipeline_context = ""
    if st.session_state["pipe_char"]: pipeline_context += f"\n【角色设定】{st.session_state['pipe_char']}"
    if st.session_state["pipe_world"]: pipeline_context += f"\n【世界设定】{st.session_state['pipe_world']}"
    if st.session_state["pipe_outline"]: pipeline_context += f"\n【大纲】{st.session_state['pipe_outline']}"
    
    char_info = "\n".join(st.session_state.characters) if st.session_state.characters else ""
    
    if burst_mode:
        instruction = "【⚠️ 强力扩写模式开启】用户给你一个简单的动作或剧情点，你必须将其扩写成一段**至少300字**的详细小说正文。包含心理描写、环境烘托、动作细节。"
    else:
        instruction = "正常写作模式，根据用户指令推进剧情。"

    system_prompt = f"""
    你是由DeepSeek驱动的专业网文作家。
    类型：{novel_type}
    
    {pipeline_context}
    {char_info}
    {f"模仿文风：{st.session_state['style_sample']}" if st.session_state['style_sample'] else ""}
    
    {instruction}
    禁止事项：不要说“好的”、“明白”，直接开始写小说正文。
    """

    container = st.container(height=550)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: 
            if pipeline_context:
                st.success("✨ 已检测到【创作流水线】生成的设定，AI 已自动装载！可以直接开始写正文了。")
            else:
                st.info(f"✨ 准备就绪。建议先去「创作流水线」生成人设和大纲。")
                
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content_show = msg["content"]
            if len(content_show) > 500 and "前文" in content_show: content_show = content_show[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content_show)

    if prompt := st.chat_input("输入剧情..."):
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":system_prompt}] + current_msgs,
                    stream=True, temperature=1.2
                )
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 创作流水线 (Step by Step) ---
with tab_pipeline:
    st.info("💡 按照步骤一步步来，哪怕你现在只有一个点子，也能生成一本书！")
    
    # 步骤 1
    with st.expander("Step 1: 💡 脑洞孵化 (第一步)", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3, 1])
        raw_idea = c1.text_input("你只有一个模糊的想法？写在这里：", placeholder="例如：重生回末世前一个月，疯狂借钱囤货")
        if c2.button("✨ 完善脑洞"):
            p = f"基于点子“{raw_idea}”，为{novel_type}小说完善核心梗、爽点和卖点。100字以内。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_idea"] = res.choices[0].message.content
            st.rerun()
            
    if st.session_state["pipe_idea"]:
        st.success(f"✅ 核心脑洞：{st.session_state['pipe_idea']}")

    # 步骤 2 (自动读取步骤1)
    with st.expander("Step 2: 🦸‍♂️ 核心人设 (第二步)", expanded=bool(st.session_state["pipe_idea"]) and not st.session_state["pipe_char"]):
        if not st.session_state["pipe_idea"]:
            st.warning("请先完成 Step 1")
        else:
            if st.button("👥 基于脑洞生成主角 & 反派"):
                p = f"基于核心梗“{st.session_state['pipe_idea']}”，生成男女主角档案（姓名/性格/金手指）和一个主要反派。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_char"] = res.choices[0].message.content
                st.rerun()

    if st.session_state["pipe_char"]:
        st.info(f"✅ 人设已就位 (详情折叠)")

    # 步骤 3
    with st.expander("Step 3: 🗺️ 世界观 & 体系 (第三步)", expanded=bool(st.session_state["pipe_char"]) and not st.session_state["pipe_world"]):
        if not st.session_state["pipe_char"]:
            st.warning("请先完成 Step 2")
        else:
            if st.button("🌍 补全世界规则"):
                p = f"基于{novel_type}，为上述人设生成世界观背景、力量体系等级、货币单位。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_world"] = res.choices[0].message.content
                st.rerun()
                
    if st.session_state["pipe_world"]:
        st.info(f"✅ 世界观已建立")

    # 步骤 4
    with st.expander("Step 4: 📜 黄金三章大纲 (最后一步)", expanded=bool(st.session_state["pipe_world"])):
        if not st.session_state["pipe_world"]:
            st.warning("请先完成 Step 3")
        else:
            if st.button("🚀 生成开篇大纲"):
                p = f"""
                核心梗：{st.session_state['pipe_idea']}
                人设：{st.session_state['pipe_char']}
                世界：{st.session_state['pipe_world']}
                
                请生成极具吸引力的前三章大纲（黄金三章），包含每章的爽点和断章悬念。
                """
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_outline"] = res.choices[0].message.content
                st.rerun()
                
    if st.session_state["pipe_outline"]:
        st.markdown("### 🎉 大纲预览")
        st.text_area("大纲内容", value=st.session_state["pipe_outline"], height=200)
        st.success("恭喜！所有准备工作已完成。现在，你的 AI 助手已经完全记住了这本小说的所有设定。")
        st.caption("请点击上方「✍️ 沉浸写作」标签页开始正文创作。")

# --- TAB 3: 审稿 ---
with tab_review:
    st.markdown("### 💾 审稿与导出")
    if st.button("🔍 毒舌审稿"):
        txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        if len(txt)<50: st.warning("字数太少")
        else:
            p = f"毒舌点评：\n{txt}"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.info(res.choices[0].message.content)
            
    data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
    st.download_button("📥 导出全书", json.dumps(data, ensure_ascii=False), "novel.json")