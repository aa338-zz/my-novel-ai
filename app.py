import streamlit as st
from openai import OpenAI
import json
import random

# ==========================================
# 0. 全局配置 (UI 颜值天花板)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 注入 CSS 魔法 (深空流光主题) ---
st.markdown("""
<style>
    /* 1. 全局深色背景 */
    .stApp {
        background: #0e1117; /* 深空黑 */
        color: #e0e0e0;
    }
    
    /* 2. 侧边栏：高级灰 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* 3. 标题美化 */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }
    
    /* 4. 按钮：流光渐变特效 (核心颜值) */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); /* 紫罗兰极光 */
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(118, 75, 162, 0.6);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* 5. 输入框：毛玻璃质感 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.05); /* 半透明 */
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #764ba2;
        background-color: rgba(255, 255, 255, 0.1);
        box-shadow: 0 0 10px rgba(118, 75, 162, 0.5);
    }
    
    /* 6. 聊天气泡：悬浮卡片 */
    .stChatMessage {
        background-color: #1f242d;
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stChatMessage[data-testid="user-message"] {
        background-color: #2b313a;
    }
    
    /* 7. Tabs 标签页 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #161b22;
        border-radius: 8px;
        color: #8b949e;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white !important;
        font-weight: bold;
        border: none;
    }
    
    /* 隐藏杂项 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# 初始化 Session
if "chapters" not in st.session_state: st.session_state["chapters"] = {1: []}
if "current_chapter" not in st.session_state: st.session_state["current_chapter"] = 1
if "characters" not in st.session_state: st.session_state["characters"] = [] 
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "style_sample" not in st.session_state: st.session_state["style_sample"] = ""
if "memo" not in st.session_state: st.session_state["memo"] = ""

# ==========================================
# 1. 赛博登录界面
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            # 使用 HTML 渲染一个发光的标题
            st.markdown("""
            <h1 style='text-align: center; font-size: 60px; 
            background: -webkit-linear-gradient(#eee, #333); 
            -webkit-background-clip: text; color: white; text-shadow: 0 0 20px #764ba2;'>
            ⚡ GENESIS
            </h1>
            <p style='text-align: center; color: #aaa; letter-spacing: 4px;'>ULTIMATE WRITING ENGINE</p>
            """, unsafe_allow_html=True)
            
            with st.form("login"):
                pwd = st.text_input("ACCESS KEY", type="password", placeholder="输入密钥: 666")
                if st.form_submit_button("🚀 启动引擎 / LAUNCH", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("⛔ ACCESS DENIED")
        st.stop()
check_login()

# ==========================================
# 2. 侧边栏 (指挥塔)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 控制台")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("🟢 神经网络：在线")
    else:
        st.error("🔴 神经网络：离线")
        st.stop()
    
    st.divider()
    
    # 便签
    st.markdown("**📝 灵感速记 (Memo)**")
    st.session_state["memo"] = st.text_area("memo", value=st.session_state["memo"], height=120, label_visibility="collapsed", placeholder="在此记录你的脑洞...")
    
    st.divider()
    
    # 章节与字数
    c1, c2 = st.columns([2,1])
    with c1:
        chap_list = list(st.session_state.chapters.keys())
        curr = st.session_state.current_chapter
        sel = st.selectbox("当前章节", chap_list, index=chap_list.index(curr))
        if sel != curr:
            st.session_state.current_chapter = sel
            st.rerun()
    with c2:
        st.write("")
        st.write("")
        if st.button("➕", help="新章"):
            new = len(st.session_state.chapters)+1
            st.session_state.chapters[new] = []
            st.session_state.current_chapter = new
            st.rerun()
            
    # 字数统计
    txt = "".join([m["content"] for m in st.session_state["chapters"][curr] if m["role"]=="assistant"])
    st.caption(f"📊 当前字数: {len(txt)}")

    st.divider()
    
    # 🔥 全网最全分类库
    st.markdown("### 📚 题材设定")
    novel_types = [
        "--- 🔥 男频热血 ---",
        "玄幻 | 东方玄幻", "玄幻 | 异世大陆", "玄幻 | 王朝争霸",
        "仙侠 | 古典仙侠", "仙侠 | 现代修真", "仙侠 | 神话修真",
        "都市 | 异术超能", "都市 | 战神赘婿", "都市 | 官场商战",
        "历史 | 架空历史", "历史 | 穿越大唐", "历史 | 谍战特工",
        "科幻 | 末世危机", "科幻 | 星际文明", "科幻 | 赛博朋克",
        "游戏 | 虚拟网游", "游戏 | 电竞直播", "游戏 | 全球数据化",
        
        "--- 🌸 女频言情 ---",
        "现言 | 豪门总裁", "现言 | 娱乐明星", "现言 | 甜宠日常",
        "古言 | 宫斗宅斗", "古言 | 穿越种田", "古言 | 女尊女强",
        "幻情 | 仙侠奇缘", "幻情 | 西幻魔法",
        "快穿 | 系统攻略", "快穿 | 打脸虐渣",
        
        "--- 🧠 脑洞与衍生 ---",
        "悬疑 | 诡秘探险", "悬疑 | 规则怪谈", "悬疑 | 刑侦破案",
        "无限流 | 诸天万界", "无限流 | 恐怖解密",
        "同人 | 火影海贼", "同人 | 漫威DC", "同人 | 哈利波特",
        
        "--- 🧟‍♂️ 末世专项 (热门) ---",
        "末世 | 丧尸围城", "末世 | 囤货基地", "末世 | 废土进化", "末世 | 天灾求生"
    ]
    novel_type = st.selectbox("类型", novel_types, index=13) # 默认选个末世
    temp = st.slider("思维发散度", 0.5, 1.5, 1.2)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 3. 主界面
# ==========================================
# 使用 emoji 增加高级感
tab_write, tab_tools, tab_review = st.tabs(["✍️ 沉浸写作", "🧰 神级工具箱", "💾 审稿/导出"])

# --- TAB 1: 沉浸写作 (含导入) ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 🔥 文件导入
    with st.expander("📂 导入旧稿 / 续写 (Drop File Here)", expanded=False):
        uploaded_file = st.file_uploader("上传 .txt 文件", type=["txt"])
        if uploaded_file is not None:
            stringio = uploaded_file.getvalue().decode("utf-8")
            if st.button("📥 确认导入并续写"):
                st.session_state.chapters[st.session_state.current_chapter].append({
                    "role": "user", 
                    "content": f"前文内容：\n\n{stringio}"
                })
                st.session_state.chapters[st.session_state.current_chapter].append({
                    "role": "assistant", 
                    "content": "✅ 前文已读取。请指示下一步剧情。"
                })
                st.toast("导入成功！AI 已记忆。")
                st.rerun()

    # System Prompt
    char_info = "\n".join(st.session_state.characters) if st.session_state.characters else "暂无"
    system_prompt = f"""
    你是由DeepSeek驱动的【创世笔】。
    类型：{novel_type} | 角色：{char_info}
    {f"模仿文风：{st.session_state['style_sample']}" if st.session_state['style_sample'] else ""}
    要求：情节紧凑，画面感强，拒绝AI味。
    """

    container = st.container(height=550) # 加高高度，更沉浸
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: 
            st.info(f"✨ 题材：{novel_type}。输入指令开始创作。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "⚡"
            content_show = msg["content"]
            if len(content_show) > 500 and "前文内容" in content_show:
                content_show = content_show[:200] + "...\n(已折叠长文)"
            st.chat_message(msg["role"], avatar=avatar).write(content_show)

    # 底部输入栏
    if prompt := st.chat_input("输入剧情指令..."):
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="⚡"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":system_prompt}] + current_msgs,
                    stream=True, temperature=temp
                )
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 神级工具箱 (Pro) ---
with tab_tools:
    st.info("💡 这是一个可以随意调用的武器库，不会打断你的写作思路。")
    
    # 🔥 功能1: 命运扭蛋机
    with st.expander("🎲 命运扭蛋机 (Fate Gacha)", expanded=True):
        c1, c2, c3 = st.columns(3)
        if c1.button("💥 抽取【神转折】", use_container_width=True):
            with st.spinner("命运正在重组..."):
                p = f"为{novel_type}生成一个神转折。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.success(f"🔥 {res.choices[0].message.content}")     
        if c2.button("💎 抽取【金手指】", use_container_width=True):
            p = f"为{novel_type}生成一个独特道具/能力。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.info(f"💎 {res.choices[0].message.content}")   
        if c3.button("😈 抽取【危机】", use_container_width=True):
            p = f"为{novel_type}生成一个突发危机。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.error(f"⚠️ {res.choices[0].message.content}")

    # 🔥 功能2: 战斗导演
    with st.expander("⚔️ 动作戏导演 (Action Director)"):
        col_act1, col_act2 = st.columns([3, 1])
        act_input = col_act1.text_input("动作指令", placeholder="如：主角一刀砍掉了丧尸的头")
        if col_act2.button("🎬 Action", use_container_width=True):
            p = f"将动作“{act_input}”扩写为极具画面感的打斗描写。类型：{novel_type}。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.markdown(res.choices[0].message.content)

    # 🔥 功能3: 逻辑桥
    with st.expander("🌉 逻辑桥 (Plot Bridge)"):
        b1, b2 = st.columns(2)
        start = b1.text_input("起点", placeholder="如：主角被困")
        end = b2.text_input("终点", placeholder="如：主角逃脱")
        if st.button("🚧 生成过渡", use_container_width=True):
            p = f"起点：{start}，终点：{end}。生成中间过渡剧情。类型：{novel_type}。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.markdown(res.choices[0].message.content)

    # 其他工具
    col_x1, col_x2 = st.columns(2)
    with col_x1:
        with st.expander("🦸‍♂️ 深度人设"):
            desc = st.text_area("输入描述", height=70)
            if st.button("生成"):
                p = f"基于描述'{desc}'生成{novel_type}人设：姓名、外貌、性格(MBTI)、秘密。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state.characters.append(res.choices[0].message.content)
                st.markdown(res.choices[0].message.content)
    with col_x2:
        with st.expander("🎭 潜台词润色"):
            raw = st.text_input("直白的话")
            if st.button("润色"):
                p = f"将'{raw}'改为Show Don't Tell的高级描写。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.markdown(res.choices[0].message.content)

# --- TAB 3: 审稿 ---
with tab_review:
    st.markdown("### 💾 数据中心")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("让 AI 像主编一样审视你的稿子")
        if st.button("🔍 毒舌审稿", use_container_width=True):
            txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            if len(txt)<50: st.warning("字数太少")
            else:
                p = f"毒舌点评：\n{txt}\n给出评分、硬伤、建议。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.info(res.choices[0].message.content)
    with c2:
        st.caption("备份你的心血")
        data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
        st.download_button("📥 导出全书 (.json)", json.dumps(data, ensure_ascii=False), "genesis_novel.json", use_container_width=True)
    
    if st.session_state.characters:
        st.divider()
        st.caption("已收录角色卡")
        for char in st.session_state.characters:
            st.code(char[:100]+"...")