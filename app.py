import streamlit as st
from openai import OpenAI
import json

# ==========================================
# 0. 全局配置 (极简白金版)
# ==========================================
st.set_page_config(
    page_title="创世笔 GENESIS", 
    page_icon="🖊️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 极简主义 CSS (Apple/Notion 风格) ---
st.markdown("""
<style>
    /* 1. 强制亮色模式优化 */
    .stApp {
        background-color: #ffffff; /* 纯白背景 */
        color: #333333;
    }
    
    /* 2. 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #f7f9fb; /* 极淡的灰蓝色 */
        border-right: 1px solid #e0e0e0;
    }
    
    /* 3. 按钮：清爽的蓝色 */
    .stButton>button {
        background-color: #007aff;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #005ecb;
        box-shadow: 0 4px 12px rgba(0,122,255,0.2);
    }
    
    /* 4. 输入框：更柔和的边框 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        color: #333333;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #007aff;
        box-shadow: 0 0 0 2px rgba(0,122,255,0.1);
    }

    /* 5. 聊天气泡优化 */
    .stChatMessage {
        background-color: #f8f9fa;
        border-radius: 12px;
        border: 1px solid #eaeaea;
    }

    /* 隐藏杂项 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 初始化
if "chapters" not in st.session_state: st.session_state["chapters"] = {1: []}
if "current_chapter" not in st.session_state: st.session_state["current_chapter"] = 1
if "characters" not in st.session_state: st.session_state["characters"] = [] 
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "style_sample" not in st.session_state: st.session_state["style_sample"] = ""

# ==========================================
# 1. 极简登录页
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 

def check_login():
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; color: #333;'>🖊️ 创世笔</h1>", unsafe_allow_html=True)
            st.caption("<p style='text-align: center;'>极简 · 专注 · 智能</p>", unsafe_allow_html=True)
            
            with st.form("login"):
                pwd = st.text_input("请输入通行密钥", type="password", placeholder="例如：666")
                if st.form_submit_button("进入工作室", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()

check_login()

# ==========================================
# 2. 侧边栏 (设置区)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 工作台设置")
    
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎就绪")
    else:
        st.error("🔴 未配置 Key")
        st.stop()
    
    st.divider()
    
    # 章节管理
    c1, c2 = st.columns([2,1])
    with c1:
        chap_list = list(st.session_state.chapters.keys())
        curr = st.session_state.current_chapter
        sel = st.selectbox("当前章节", chap_list, index=chap_list.index(curr))
        if sel != curr:
            st.session_state.current_chapter = sel
            st.rerun()
    with c2:
        st.write("") # 占位
        st.write("") 
        if st.button("➕", help="新建一章"):
            new = len(st.session_state.chapters)+1
            st.session_state.chapters[new] = []
            st.session_state.current_chapter = new
            st.rerun()

    st.divider()
    
    # 📚 类型大扩容 (包含末世加强版)
    st.markdown("### 📚 作品设定")
    novel_types = [
        # --- 🔥 热门末世流 (你点的) ---
        "末世 | 丧尸围城", "末世 | 废土进化", "末世 | 天灾求生", "末世 | 囤货基地",
        
        # --- 其他经典分类 ---
        "玄幻 | 东方玄幻", "玄幻 | 异世大陆", 
        "仙侠 | 修真文明", "仙侠 | 古典仙侠",
        "都市 | 异术超能", "都市 | 豪门世家", "都市 | 职场商战",
        "科幻 | 赛博朋克", "科幻 | 星际文明", 
        "悬疑 | 诡秘探险", "悬疑 | 侦探推理", "悬疑 | 规则怪谈",
        "历史 | 架空历史", "历史 | 穿越重生",
        "游戏 | 虚拟网游", "游戏 | 电竞直播",
        "无限流 | 诸天万界",
        "轻小说 | 二次元同人", "轻小说 | 系统流",
        "女频 | 宫斗宅斗", "女频 | 种田经营"
    ]
    novel_type = st.selectbox("选择小说类型", novel_types)
    
    temp = st.slider("AI 活跃度 (0.5严谨 - 1.5发散)", 0.5, 1.5, 1.2)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 3. 主界面 (极简三段式)
# ==========================================

tab_write, tab_tools, tab_review = st.tabs(["✍️ 沉浸写作", "🛠️ 灵感工具箱", "💾 审稿与导出"])

# --- TAB 1: 沉浸写作 (最干净的界面) ---
with tab_write:
    st.markdown(f"#### 📖 第 {st.session_state.current_chapter} 章")
    
    # 核心 Prompt 构建
    char_info = "\n".join(st.session_state.characters) if st.session_state.characters else "暂无"
    style_info = f"【文风模仿】{st.session_state['style_sample'][:100]}..." if st.session_state['style_sample'] else "默认风格"
    
    system_prompt = f"""
    你是由DeepSeek驱动的专业小说助手。
    当前类型：{novel_type}
    当前已知角色：{char_info}
    {f"请模仿此文风：{st.session_state['style_sample']}" if st.session_state['style_sample'] else ""}
    要求：情节紧凑，画面感强，拒绝AI味废话。
    """

    # 聊天区域
    container = st.container(height=500)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs:
            st.info(f"👋 欢迎来到极简创作模式。当前题材：{novel_type}。输入指令开始创作。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    if prompt := st.chat_input("输入剧情指令..."):
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":system_prompt}] + current_msgs,
                    stream=True,
                    temperature=temp
                )
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 灵感工具箱 (折叠收纳) ---
with tab_tools:
    st.info("💡 这里汇集了所有辅助工具，点击展开使用。")
    
    # 工具 1：五感扩写
    with st.expander("👁️ 五感描写核弹 (拒绝流水账)"):
        c1, c2 = st.columns([3, 1])
        raw_text = c1.text_input("输入一句平淡的描述", placeholder="如：丧尸冲了过来")
        if c2.button("💥 扩写", use_container_width=True):
            p = f"将'{raw_text}'扩写为视觉、听觉、嗅觉、触觉、环境烘托5个维度的句子。类型：{novel_type}。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.markdown(res.choices[0].message.content)

    # 工具 2：风格 DNA
    with st.expander("🧬 个人文风克隆"):
        sample = st.text_area("粘贴你喜欢的段落 (AI会自动模仿)", value=st.session_state["style_sample"])
        if st.button("💾 保存文风"):
            st.session_state["style_sample"] = sample
            st.success("已保存，AI 写作时将自动应用此风格。")

    # 工具 3：角色卡生成
    with st.expander("🦸‍♂️ 快速生成人设"):
        name = st.text_input("角色名")
        if st.button("✨ 生成档案"):
            p = f"为{novel_type}生成角色【{name}】的详细档案：性格、外貌、能力、秘密。用Markdown列表格式。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state.characters.append(res.choices[0].message.content)
            st.success("角色已存入记忆库")
    
    # 工具 4：大纲生成
    with st.expander("📜 黄金三章/大纲生成"):
        idea = st.text_input("核心脑洞/书名")
        if st.button("🚀 生成开篇大纲"):
            p = f"书名{idea}，类型{novel_type}。请生成极具吸引力的开篇黄金三章细纲。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.markdown(res.choices[0].message.content)

# --- TAB 3: 审稿与导出 ---
with tab_review:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👨‍🏫 毒舌主编")
        st.caption("AI 将作为严厉的主编审视你的稿子")
        if st.button("🔍 审判当前章节"):
            full_text = "\n".join([m["content"] for m in current_msgs if m["role"] == "assistant"])
            if len(full_text) < 50:
                st.warning("字数太少。")
            else:
                p = f"点评以下小说内容：\n{full_text}\n给出评分、硬伤分析和修改建议。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.info(res.choices[0].message.content)
                
    with col2:
        st.markdown("### 💾 数据备份")
        st.caption("下载你的心血，防止丢失")
        
        # 准备数据
        data = {
            "history": st.session_state.chapters,
            "chars": st.session_state.characters,
            "style": st.session_state["style_sample"]
        }
        st.download_button(
            "📥 下载全书数据 (.json)", 
            json.dumps(data, ensure_ascii=False), 
            "my_novel.json",
            use_container_width=True
        )
        
        # 显示已存角色
        if st.session_state.characters:
            with st.popover("查看已存角色"):
                for c in st.session_state.characters:
                    st.text(c[:50]+"...")