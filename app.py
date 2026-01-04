import streamlit as st
from openai import OpenAI
import json
import random
import re

# ==========================================
# 0. 全局配置
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="🖊️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

if "init_done" not in st.session_state:
    st.session_state["chapters"] = {1: []}
    st.session_state["current_chapter"] = 1
    st.session_state["characters"] = [] 
    st.session_state["logged_in"] = False
    st.session_state["style_sample"] = ""
    st.session_state["memo"] = ""
    st.session_state["mimic_style"] = "" 
    st.session_state["mimic_analysis"] = ""
    st.session_state["pipe_idea"] = ""
    st.session_state["pipe_char"] = ""
    st.session_state["pipe_world"] = ""
    st.session_state["pipe_outline"] = ""
    st.session_state["init_done"] = True

# ==========================================
# 1. 样式 (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #ffffff; color: #000000;}
    section[data-testid="stSidebar"] {background-color: #f8f9fa; border-right: 1px solid #e9ecef;}
    
    .stButton>button {
        background-color: #007bff; color: white !important; border-radius: 6px; border: none; font-weight: 600;
    }
    .stButton>button:hover {background-color: #0056b3; transform: translateY(-1px);}
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput input {
        background-color: #fff; border: 1px solid #ced4da; border-radius: 6px;
    }
    .stTextInput>div>div>input:focus {border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);}

    .stChatMessage {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px;}
    
    .sensitive-word {background-color: #ffe6e6; color: #d93025; font-weight: bold; padding: 2px 4px; border-radius: 4px;}
    .alert-card {background-color: #fff5f5; border-left: 4px solid #fc8181; padding: 10px; margin-bottom: 8px;}
    .alert-word {color: #e53e3e; font-weight: bold; background-color: #fed7d7; padding: 0 4px; border-radius: 2px;}

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.markdown("<br><br><h1 style='text-align: center; color:#333;'>🖊️ 创世笔 Pro</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("请输入通行密钥", type="password", placeholder="666")
                if st.form_submit_button("🚀 进入工作室", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 控制台")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎连接正常")
    else:
        st.error("🔴 未配置 Secrets")
        st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    st.divider()

    # 章节
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.number_input("章号", min_value=1, value=st.session_state.current_chapter, label_visibility="collapsed")
        if target != st.session_state.current_chapter:
            if target not in st.session_state.chapters: st.session_state.chapters[target] = []
            st.session_state.current_chapter = target
            st.rerun()
    with c2:
        st.caption(f"第 {st.session_state.current_chapter} 章")
    
    current_text_raw = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
    st.caption(f"字数: {len(current_text_raw)}")
    st.divider()

    # 工具
    with st.expander("🎲 取名神器"):
        name_cat = st.selectbox("类型", ["玄幻古风", "现代都市", "西方奇幻", "末世废土", "日式轻小说"], label_visibility="collapsed")
        if st.button("🎲 生成"):
            if name_cat == "玄幻古风": pool = ["萧炎", "叶凡", "林动", "楚晚宁", "云韵", "纳兰", "风清扬", "厉飞雨", "韩立"]
            elif name_cat == "现代都市": pool = ["陆薄言", "顾漫", "苏明玉", "林风", "陈孝正", "江莱", "安迪"]
            elif name_cat == "末世废土": pool = ["雷恩", "V", "强尼", "爱丽丝", "007号", "猎鹰", "黑狼"]
            elif name_cat == "西方奇幻": pool = ["亚瑟", "兰斯洛特", "梅林", "哈利", "罗恩", "赫敏"]
            else: pool = ["桐人", "亚丝娜", "五条悟", "炭治郎", "利威尔"]
            st.info(f"名字：{random.choice(pool)}")
        if st.button("🤖 AI 现编"):
            try:
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"生成5个好听的{name_cat}人名，逗号隔开。"}])
                st.success(r.choices[0].message.content)
            except: st.error("AI 忙碌")

    with st.expander("🛡️ 违禁词雷达"):
        if st.button("🔴 开始扫描"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "爆炸", "尸体"]
            found_issues = []
            if not current_text_raw:
                st.warning("没内容！")
            else:
                for word in risky:
                    if word in current_text_raw:
                        sentences = re.split(r'[。！？\n]', current_text_raw)
                        for sent in sentences:
                            if word in sent:
                                clean_sent = sent.strip()
                                if clean_sent:
                                    hl_sent = clean_sent.replace(word, f"<span class='alert-word'>{word}</span>")
                                    found_issues.append(hl_sent)
                if found_issues:
                    st.error(f"发现 {len(found_issues)} 处风险！")
                    for issue in found_issues[:5]:
                        st.markdown(f"<div class='alert-card'>📍 ...{issue}...</div>", unsafe_allow_html=True)
                else:
                    st.success("✅ 安全")

    st.divider()
    all_types = ["末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化", "玄幻 | 东方玄幻", "都市 | 异术超能", "都市 | 战神赘婿", "历史 | 架空历史", "科幻 | 赛博朋克", "无限流 | 诸天万界", "悬疑 | 规则怪谈", "女频 | 豪门总裁", "女频 | 宫斗宅斗", "自定义"]
    t_sel = st.selectbox("类型", all_types)
    novel_type = st.text_input("输入类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel
    word_target = st.number_input("单次字数", 100, 5000, 800, 100)
    burst_mode = st.toggle("强力扩写", value=True)

# ==========================================
# 4. 主界面
# ==========================================
tab_write, tab_clone, tab_pipeline, tab_review, tab_extra = st.tabs(["✍️ 沉浸写作", "🧬 风格克隆", "🚀 创作流水线", "💾 审稿/导出", "🔮 扩展/周边"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    pipe_ctx = ""
    if st.session_state["pipe_char"]: pipe_ctx += f"\n【角色】{st.session_state["pipe_char"]}"
    if st.session_state["pipe_world"]: pipe_ctx += f"\n【世界】{st.session_state["pipe_world"]}"
    if st.session_state["pipe_outline"]: pipe_ctx += f"\n【大纲】{st.session_state['pipe_outline']}"
    style_ctx = f"【模仿文风】\n{st.session_state['mimic_analysis']}" if st.session_state['mimic_analysis'] else ""
    instruction = f"字数目标：{word_target}。" + ("【强力扩写】详细描写。" if burst_mode else "")
    
    system_prompt = f"""
    你是由DeepSeek驱动的专业作家。
    类型：{novel_type}
    {pipe_ctx}
    {style_ctx}
    {instruction}
    禁止说“好的”。
    """

    container = st.container(height=400) # 留出空间给底部操作
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info(f"✨ 准备就绪。")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            if len(content) > 500 and "前文" in content: content = content[:200] + "...\n(已折叠)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # ==========================
    # 🔥 核心更新：剧情微操区
    # ==========================
    st.markdown("---")
    c_in, c_btn = st.columns([6, 1])
    
    user_input = None
    manual_plot = None # 剧情定向
    
    # 1. 正常的对话框 (Chat Input)
    # Streamlit 的 chat_input 是固定的，这里我们用普通的 text_area 代替，为了布局
    # 但为了体验好，我们还是用 chat_input 放在最下面
    
    # 2. 剧情定向输入框 (Plot Injection)
    col_plot, col_action = st.columns([5, 1])
    with col_plot:
        manual_plot = st.text_input("💡 下一段剧情走向 (留空则 AI 自由发挥)", placeholder="例如：主角在转角处遇到了前女友，场面一度尴尬...")
    with col_action:
        st.write("") 
        st.write("") 
        btn_continue = st.button("🔄 继续写", use_container_width=True, help="点击后，AI将根据左侧的指示继续生成")

    # 处理输入
    if prompt := st.chat_input("输入对话/指令..."):
        user_input = prompt

    # 逻辑判断
    final_instruction = ""
    if user_input:
        final_instruction = user_input
    elif btn_continue:
        if manual_plot:
            final_instruction = f"接着上文写。注意：{manual_plot}。请自然地过渡到这个情节。"
        else:
            final_instruction = "接着上文继续写，保持连贯。"

    # 执行生成
    if final_instruction:
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":final_instruction})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(final_instruction)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":system_prompt}] + current_msgs,
                    stream=True, temperature=1.2
                )
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # ==========================
    # 🛠️ 底部工具栏
    # ==========================
    st.markdown("### 🛠️ 章节操作")
    action_tab1, action_tab2, action_tab3 = st.tabs(["📋 一键复制全章", "✍️ 整章重写", "✂️ 局部精修"])
    
    with action_tab1:
        st.caption("👇 鼠标悬停在下方黑色区域，点击右上角【复制图标】即可全选。")
        # 拼接全章内容
        full_chapter_text = ""
        for m in current_msgs:
            if m["role"] == "assistant":
                full_chapter_text += m["content"] + "\n\n"
        st.code(full_chapter_text if full_chapter_text else "暂无内容", language="text")

    with action_tab2:
        rewrite_instruction = st.text_input("重写意见", placeholder="例如：氛围再恐怖一点。")
        if st.button("💥 重写本章"):
            if not current_text_raw:
                st.warning("没内容。")
            else:
                p = f"【指令】重写本章：{rewrite_instruction}。"
                st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content": p})
                with container:
                    st.chat_message("user", avatar="🧑‍💻").write(p)
                    with st.chat_message("assistant", avatar="🖊️"):
                        stream = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role":"system","content":system_prompt}] + current_msgs,
                            stream=True, temperature=1.2
                        )
                        response = st.write_stream(stream)
                st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})
                st.rerun()

    with action_tab3:
        c_edit1, c_edit2 = st.columns(2)
        with c_edit1:
            bad_part = st.text_area("粘贴片段", height=100)
        with c_edit2:
            edit_instruction = st.text_area("怎么改？", height=100)
        if st.button("✨ 润色"):
            if bad_part and edit_instruction:
                p = f"修改片段：{bad_part}\n要求：{edit_instruction}\n只输出修改后的内容。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                st.write_stream(stream)

# --- TAB 2-5 保持原样 (逻辑加固版) ---
# (为了节省篇幅，这里复用之前的稳定逻辑，主要是写作区的UI交互变动)
# ... [TAB 2, 3, 4, 5 代码与上一版相同，直接复制即可] ...
# 为了保证完整性，我把剩下的 TAB 代码也贴上：

with tab_clone:
    st.info("上传样本，提取文风。")
    up, res = st.columns(2)
    with up:
        f = st.file_uploader("上传样本txt", type=["txt"])
        if f and st.button("🧠 提取"):
            raw = f.getvalue().decode("utf-8")[:3000]
            with st.spinner("分析中..."):
                p = f"分析这段文字的文风：\n{raw}\n总结其叙事视角、用词习惯。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["mimic_style"] = raw
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.rerun()
    with res:
        if st.session_state["mimic_analysis"]: st.text_area("特征", st.session_state["mimic_analysis"], height=300)

with tab_pipeline:
    st.info("Step by Step。流式生成。")
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3, 1])
        idea = c1.text_input("点子：")
        if c2.button("生成梗"):
            p = f"基于点子“{idea}”，为{novel_type}生成核心梗。100字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_idea"]: st.session_state["pipe_idea"] = st.text_area("✅ 脑洞", st.session_state["pipe_idea"], height=100)

    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        if st.button("生成人设"):
            p = f"基于梗“{st.session_state['pipe_idea']}”，生成主角反派。200字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_char"]: st.session_state["pipe_char"] = st.text_area("✅ 人设", st.session_state["pipe_char"], height=200)

    with st.expander("Step 3: 世界", expanded=bool(st.session_state["pipe_char"])):
        if st.button("生成世界"):
            p = f"基于{novel_type}，生成简要世界观。150字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_world"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_world"]: st.session_state["pipe_world"] = st.text_area("✅ 世界", st.session_state["pipe_world"], height=150)

    with st.expander("Step 4: 大纲", expanded=bool(st.session_state["pipe_world"])):
        if st.button("生成细纲"):
            p = f"""核心梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。世界：{st.session_state['pipe_world']}。生成前三章细纲。严禁输出废话。"""
            st.markdown("**推演中...**")
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_outline"]: st.session_state["pipe_outline"] = st.text_area("✅ 大纲", st.session_state["pipe_outline"], height=300)

with tab_review:
    if st.button("🔍 毒舌审稿"):
        txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        if len(txt)<50: st.warning("字数太少")
        else:
            p = f"毒舌点评：\n{txt}"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
    data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
    st.download_button("📥 导出全书", json.dumps(data, ensure_ascii=False), "novel.json")

with tab_extra:
    st.markdown("### 🔮 扩展")
    c1, c2 = st.columns(2)
    with c1:
        st.info("🎨 绘图提示词")
        d = st.text_area("画面描述", height=100)
        if st.button("✨ 生成咒语"):
            p = f"翻译为MJ/SD提示词(Prompt)：{d}"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
    with c2:
        st.info("👾 虚拟书评")
        if st.button("💬 生成评论"):
            txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            if len(txt)<100: st.warning("字数太少")
            else:
                p = f"扮演5个读者评论：{txt[:1000]}"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                st.write_stream(stream)
    
    with st.expander("🧹 一键排版"):
        raw = st.text_area("粘贴乱文本", height=150)
        if st.button("排版"):
            clean = re.sub(r'\n\s*\n', '\n', raw.strip())
            lines = [f"    {l.strip()}" for l in clean.split('\n') if l.strip()]
            st.text_area("结果", "\n\n".join(lines), height=200)