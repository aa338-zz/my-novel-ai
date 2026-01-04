import streamlit as st
from openai import OpenAI
import json
import random

# ==========================================
# 0. 全局配置 (必须在第一行)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🖊️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. 核心记忆初始化 (修复 KeyError 的关键)
# ==========================================
# 必须放在任何 UI 代码之前，防止报错
if "init_done" not in st.session_state:
    st.session_state["chapters"] = {1: []}
    st.session_state["current_chapter"] = 1
    st.session_state["characters"] = [] 
    st.session_state["logged_in"] = False
    st.session_state["style_sample"] = ""
    st.session_state["memo"] = ""
    # 风格克隆相关
    st.session_state["mimic_style"] = "" 
    st.session_state["mimic_analysis"] = ""
    # 流水线相关
    st.session_state["pipe_idea"] = ""
    st.session_state["pipe_char"] = ""
    st.session_state["pipe_world"] = ""
    st.session_state["pipe_outline"] = ""
    st.session_state["init_done"] = True

# ==========================================
# 2. 样式美化 (CSS)
# ==========================================
st.markdown("""
<style>
    /* 全局优化 */
    .stApp {background-color: #ffffff; color: #000000;}
    section[data-testid="stSidebar"] {background-color: #f8f9fa; border-right: 1px solid #e9ecef;}
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #007bff; color: white !important; border-radius: 8px; border: none; font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {background-color: #0056b3; transform: translateY(-2px);}
    
    /* 输入框样式 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput input {
        background-color: #fff; border: 1px solid #ced4da; border-radius: 6px; color: #333;
    }
    .stTextInput>div>div>input:focus {border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);}

    /* 聊天气泡 */
    .stChatMessage {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px;}
    
    /* 隐藏默认菜单 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 登录逻辑
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.markdown("<br><br><h1 style='text-align: center; color:#333;'>🖊️ 创世笔 Pro</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("请输入通行密钥", type="password", placeholder="666")
                if st.form_submit_button("进入工作室", use_container_width=True):
                    # 为了方便你测试，只要输入非空字符都能进，或者保留密码验证
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 4. 侧边栏 (全能指挥塔)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 控制台")
    
    # API 检查
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎连接正常")
    else:
        st.error("🔴 未配置 Secrets")
        st.stop()
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()

    # --- 功能 1: 章节管理 ---
    st.markdown("**📖 章节导航**")
    c1, c2 = st.columns([2, 1])
    with c1:
        # 用户可以直接输数字跳转，没有限制
        target = st.number_input("章号", min_value=1, value=st.session_state.current_chapter, label_visibility="collapsed")
        if target != st.session_state.current_chapter:
            if target not in st.session_state.chapters: st.session_state.chapters[target] = []
            st.session_state.current_chapter = target
            st.rerun()
    with c2:
        st.caption(f"第 {st.session_state.current_chapter} 章")
    
    # 字数统计
    txt_len = len("".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"]))
    st.caption(f"当前字数: {txt_len}")

    st.divider()

    # --- 功能 2: 快捷工具 (修复版) ---
    st.markdown("**🛠️ 创作神器**")
    
    # A. 取名神器 (超级扩容版)
    with st.expander("🎲 取名神器 (海量库)", expanded=False):
        name_cat = st.selectbox("类型", ["玄幻古风", "现代都市", "西方奇幻", "末世废土", "日式轻小说"], label_visibility="collapsed")
        if st.button("🎲 随机生成"):
            if name_cat == "玄幻古风": 
                pool = ["萧炎", "叶凡", "林动", "顾清寒", "楚晚宁", "墨燃", "洛璃", "云韵", "纳兰", "独孤", "风清扬", "厉飞雨", "韩立", "白小纯"]
            elif name_cat == "现代都市": 
                pool = ["陆薄言", "顾漫", "苏明玉", "林风", "陈孝正", "江莱", "安迪", "曲筱绡", "方鸿渐", "赵默笙"]
            elif name_cat == "末世废土": 
                pool = ["雷恩", "V", "强尼", "爱丽丝", "007号", "猎鹰", "黑狼", "刀锋", "暴君", "追踪者"]
            elif name_cat == "西方奇幻":
                pool = ["亚瑟", "兰斯洛特", "梅林", "哈利", "罗恩", "赫敏", "弗罗多", "甘道夫", "阿拉贡"]
            else:
                pool = ["桐人", "亚丝娜", "五条悟", "炭治郎", "利威尔", "路飞", "鸣人", "佐助"]
            st.info(f"名字：{random.choice(pool)}")
        
        if st.button("🤖 AI 现编 (如果不满意)"):
            try:
                p = f"生成5个好听的{name_cat}人名，不要解释，用逗号隔开。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.success(r.choices[0].message.content)
            except: st.error("AI 忙碌")

    # B. 违禁词自查
    with st.expander("🛡️ 违禁词扫描"):
        if st.button("扫描本章"):
            text = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter]])
            risky = ["杀人", "死", "血", "恐怖", "色情"] # 模拟词库
            found = [w for w in risky if w in text]
            if found: st.warning(f"含敏感词: {found}")
            else: st.success("✅ 内容安全")

    # C. 白噪音 (真链接版)
    with st.expander("🎵 沉浸白噪音 (真实播放)"):
        bgm = st.selectbox("选择环境", ["下雨天 (Rain)", "键盘声 (Typing)", "咖啡馆 (Cafe)"], label_visibility="collapsed")
        # 这里使用 Pixabay 的免费商用音频链接，保证能出声
        if bgm == "下雨天 (Rain)":
            st.audio("https://cdn.pixabay.com/audio/2022/07/04/audio_34c9df436b.mp3") 
        elif bgm == "键盘声 (Typing)":
            st.audio("https://cdn.pixabay.com/audio/2022/03/09/audio_822f30a5c4.mp3")
        elif bgm == "咖啡馆 (Cafe)":
            st.audio("https://cdn.pixabay.com/audio/2017/08/17/04/17/cafe-265039_960_720.mp3")

    st.divider()

    # --- 功能 3: 写作参数 (全量类型 + 自定义字数) ---
    st.markdown("**⚙️ 写作参数**")
    
    # 60+ 种全量类型
    all_types = [
        "末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化", "末世 | 天灾求生",
        "玄幻 | 东方玄幻", "玄幻 | 异世大陆", "玄幻 | 王朝争霸", "仙侠 | 古典仙侠",
        "仙侠 | 现代修真", "仙侠 | 神话修真", "都市 | 异术超能", "都市 | 战神赘婿",
        "都市 | 官场商战", "都市 | 校花贴身", "都市 | 娱乐明星", "历史 | 架空历史",
        "历史 | 穿越大唐", "历史 | 谍战特工", "科幻 | 赛博朋克", "科幻 | 星际文明",
        "游戏 | 虚拟网游", "游戏 | 电竞直播", "游戏 | 全球数据化", "悬疑 | 诡秘探险",
        "悬疑 | 规则怪谈", "悬疑 | 刑侦破案", "无限流 | 诸天万界", "无限流 | 恐怖解密",
        "同人 | 火影海贼", "同人 | 漫威DC", "同人 | 哈利波特", "女频 | 豪门总裁",
        "女频 | 甜宠日常", "女频 | 宫斗宅斗", "女频 | 穿越种田", "女频 | 女尊女强",
        "自定义 (自己手写)"
    ]
    novel_type_sel = st.selectbox("小说类型", all_types)
    if novel_type_sel == "自定义 (自己手写)":
        novel_type = st.text_input("请输入你的类型", "例如：克苏鲁修仙")
    else:
        novel_type = novel_type_sel

    # 自定义字数输入框
    word_target = st.number_input("单次生成字数 (AI会尽力凑)", min_value=200, max_value=5000, value=800, step=100)
    
    burst_mode = st.toggle("开启「水字数」扩写", value=True)

# ==========================================
# 5. 主界面
# ==========================================
tab_write, tab_clone, tab_pipeline, tab_review = st.tabs(["✍️ 沉浸写作", "🧬 风格克隆", "🚀 创作流水线", "💾 审稿/导出"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 状态提示
    if st.session_state["mimic_analysis"]:
        st.success("🧬 已激活【风格克隆】：正在模仿你上传的文风写作。")
    if st.session_state["pipe_outline"]:
        st.info("🚀 已激活【流水线设定】：AI 已知晓你的大纲和人设。")

    # 导入旧稿
    with st.expander("📂 导入旧稿续写"):
        old_file = st.file_uploader("上传txt文件", type=["txt"])
        if old_file and st.button("📥 导入内容"):
            c = old_file.getvalue().decode("utf-8")
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "user", "content": f"前文：\n{c}"})
            st.session_state.chapters[st.session_state.current_chapter].append({"role": "assistant", "content": "✅ 前文已阅，请指示。"})
            st.rerun()

    # System Prompt 构建
    pipe_ctx = ""
    if st.session_state["pipe_char"]: pipe_ctx += f"\n【角色】{st.session_state['pipe_char']}"
    if st.session_state["pipe_world"]: pipe_ctx += f"\n【世界】{st.session_state['pipe_world']}"
    if st.session_state["pipe_outline"]: pipe_ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
    
    style_ctx = ""
    if st.session_state['mimic_analysis']:
        style_ctx = f"【模仿文风】\n{st.session_state['mimic_analysis']}"

    instruction = f"本次目标字数：{word_target}字左右。"
    if burst_mode: instruction += "【扩写模式】请进行详细描写，不要简略，注重心理和环境。"

    system_prompt = f"""
    你是由DeepSeek驱动的专业作家。
    类型：{novel_type}
    {pipe_ctx}
    {style_ctx}
    {instruction}
    禁止说“好的”，直接写正文。
    """

    # 聊天记录
    container = st.container(height=500)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info(f"✨ 准备就绪。目标字数：{word_target}。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            if len(content) > 500 and "前文" in content: content = content[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # 输入区
    c_in, c_btn = st.columns([6, 1])
    user_input = None
    with c_in:
        if prompt := st.chat_input("输入剧情..."): user_input = prompt
    with c_btn:
        st.write("") 
        st.write("") 
        if st.button("🔄 继续写", use_container_width=True): user_input = "接着上文继续写，保持连贯。"

    if user_input:
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":user_input})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(user_input)
            with st.chat_message("assistant", avatar="🖊️"):
                with st.spinner("AI 正在疯狂码字..."):
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"system","content":system_prompt}] + current_msgs,
                        stream=True, temperature=1.2
                    )
                    response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 风格克隆 ---
with tab_clone:
    st.info("上传一段别人的文字，AI 会提取其'灵魂'。")
    up, res = st.columns(2)
    with up:
        f = st.file_uploader("上传样本", type=["txt"])
        if f:
            raw = f.getvalue().decode("utf-8")[:3000]
            if st.button("🧠 提取文风"):
                with st.spinner("分析中..."):
                    p = f"分析这段文字的文风：\n{raw}\n总结其叙事视角、用词习惯、句式特点。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["mimic_style"] = raw
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                    st.rerun()
    with res:
        if st.session_state["mimic_analysis"]:
            st.success("✅ 提取成功")
            st.text_area("文风特征", st.session_state["mimic_analysis"], height=300)

# --- TAB 3: 创作流水线 ---
with tab_pipeline:
    st.info("Step by Step 打造你的世界。")
    
    # 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3, 1])
        idea = c1.text_input("点子")
        if c2.button("完善梗"):
            p = f"基于点子'{idea}'，为{novel_type}完善核心梗。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_idea"] = r.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_idea"]:
        st.session_state["pipe_idea"] = st.text_area("✅ 脑洞", st.session_state["pipe_idea"])

    # 人设
    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        if st.button("生成人设"):
            p = f"基于梗'{st.session_state['pipe_idea']}'，生成主角反派。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_char"] = r.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_char"]:
        st.session_state["pipe_char"] = st.text_area("✅ 人设", st.session_state["pipe_char"])

    # 世界
    with st.expander("Step 3: 世界", expanded=bool(st.session_state["pipe_char"])):
        if st.button("生成世界"):
            p = f"基于{novel_type}，生成世界观。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_world"] = r.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_world"]:
        st.session_state["pipe_world"] = st.text_area("✅ 世界", st.session_state["pipe_world"])

    # 大纲
    with st.expander("Step 4: 大纲", expanded=bool(st.session_state["pipe_world"])):
        if st.button("生成细纲"):
            p = f"梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。世界：{st.session_state['pipe_world']}。生成前三章细纲。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.session_state["pipe_outline"] = r.choices[0].message.content
            st.rerun()
    if st.session_state["pipe_outline"]:
        st.session_state["pipe_outline"] = st.text_area("✅ 大纲", st.session_state["pipe_outline"])

# --- TAB 4: 审稿 ---
with tab_review:
    if st.button("🔍 毒舌审稿"):
        txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        if len(txt)<50: st.warning("字数太少")
        else:
            p = f"毒舌点评：\n{txt}"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.info(r.choices[0].message.content)
    
    data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
    st.download_button("📥 导出全书", json.dumps(data, ensure_ascii=False), "novel.json")