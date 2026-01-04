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

# 初始化
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
    
    # 获取当前章节纯文本 (用于统计和复制)
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

    with st.expander("🛡️ 违禁词高亮"):
        if st.button("扫描本章"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "爆炸", "尸体"]
            found = set()
            hl_text = current_text_raw
            for w in risky:
                if w in hl_text:
                    found.add(w)
                    hl_text = hl_text.replace(w, f"<span class='sensitive-word'>{w}</span>")
            if found:
                st.markdown(f"<div style='background:#f9f9f9; padding:10px; border-radius:8px; height:300px; overflow-y:scroll;'>{hl_text}</div>", unsafe_allow_html=True)
            else:
                st.success("✅ 安全")

    st.divider()
    # 参数
    all_types = ["末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化", "玄幻 | 东方玄幻", "都市 | 异术超能", "都市 | 战神赘婿", "历史 | 架空历史", "科幻 | 赛博朋克", "无限流 | 诸天万界", "悬疑 | 规则怪谈", "女频 | 豪门总裁", "女频 | 宫斗宅斗", "自定义"]
    t_sel = st.selectbox("类型", all_types)
    novel_type = st.text_input("输入类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel
    word_target = st.number_input("单次字数", 100, 5000, 800, 100)
    burst_mode = st.toggle("强力扩写", value=True)

# ==========================================
# 4. 主界面
# ==========================================
tab_write, tab_clone, tab_pipeline, tab_review, tab_extra = st.tabs(["✍️ 沉浸写作", "🧬 风格克隆", "🚀 创作流水线", "💾 审稿/导出", "🔮 扩展/周边"])

# --- TAB 1: 沉浸写作 (核心升级区) ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 上下文组装
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

    container = st.container(height=450)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info(f"✨ 准备就绪。")
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
        if st.button("🔄 继续写", use_container_width=True): user_input = "接着上文继续写。"

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

    # =========================================================
    # 🔥🔥🔥 核心升级：底部精修工具栏 (Toolbar) 🔥🔥🔥
    # =========================================================
    st.divider()
    st.markdown("### 🛠️ 章节精修与操作")
    
    # 使用 Tabs 区分不同操作，避免界面混乱
    action_tab1, action_tab2, action_tab3 = st.tabs(["📋 一键复制", "✍️ 不满意？整章重写", "✂️ 局部精修 (选中重写)"])
    
    # 1. 一键复制
    with action_tab1:
        st.caption("全选复制下方内容：")
        # st.code 自带复制按钮，最方便
        st.code(current_text_raw, language="text")

    # 2. 整章重写
    with action_tab2:
        st.info("对现在的剧情走向不满意？提出意见，AI 推翻重写。")
        rewrite_instruction = st.text_input("你想怎么改？", placeholder="例如：把这一章的氛围改得更恐怖一点，主角要受伤。")
        if st.button("💥 按要求重写本章"):
            if not current_text_raw:
                st.warning("还没写内容呢！")
            else:
                with st.spinner("正在推翻重写..."):
                    p = f"""
                    【指令】用户对当前章节不满意，请根据以下意见重写整章。
                    意见：{rewrite_instruction}
                    
                    注意：保持上下文逻辑，但根据意见大幅修改。
                    """
                    # 为了不丢失历史，我们把这次重写作为一次新的生成的
                    r = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"system","content":system_prompt}] + current_msgs + [{"role":"user", "content":p}]
                    )
                    new_content = r.choices[0].message.content
                    
                    # 更新 Session，追加一条“重写版”
                    st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content": f"重写指令：{rewrite_instruction}"})
                    st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content": new_content})
                    st.rerun()

    # 3. 局部精修 (选中重写)
    with action_tab3:
        st.info("复制你不满意的那一段话，告诉 AI 怎么润色。")
        c_edit1, c_edit2 = st.columns(2)
        with c_edit1:
            bad_part = st.text_area("粘贴不满意的片段", height=100, placeholder="粘贴你觉得写得烂的那几句...")
        with c_edit2:
            edit_instruction = st.text_area("你想怎么改？", height=100, placeholder="例如：这段打斗太水了，写出拳拳到肉的感觉。")
        
        if st.button("✨ 润色片段"):
            if bad_part and edit_instruction:
                with st.spinner("正在做手术..."):
                    p = f"""
                    请修改以下小说片段。
                    原片段：{bad_part}
                    修改要求：{edit_instruction}
                    
                    请只输出修改后的片段，不要输出其他废话。
                    """
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    refined_text = r.choices[0].message.content
                    
                    st.success("润色完成！")
                    st.markdown("**修改后：**")
                    st.code(refined_text, language="text")
            else:
                st.warning("请填好内容")

# --- TAB 2: 风格克隆 ---
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
        if st.session_state["mimic_analysis"]:
            st.text_area("特征", st.session_state["mimic_analysis"], height=300)

# --- TAB 3: 流水线 ---
with tab_pipeline:
    st.info("Step by Step。已优化速度。")
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3, 1])
        idea = c1.text_input("点子：")
        if c2.button("生成梗"):
            with st.spinner("极速生成..."):
                p = f"基于点子“{idea}”，为{novel_type}生成核心梗。要求：简练、有爽点。100字。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_idea"] = r.choices[0].message.content
                st.rerun()
    if st.session_state["pipe_idea"]: st.session_state["pipe_idea"] = st.text_area("✅ 脑洞", st.session_state["pipe_idea"])

    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        if st.button("生成人设"):
            with st.spinner("极速生成..."):
                p = f"基于梗“{st.session_state['pipe_idea']}”，生成主角反派。200字。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_char"] = r.choices[0].message.content
                st.rerun()
    if st.session_state["pipe_char"]: st.session_state["pipe_char"] = st.text_area("✅ 人设", st.session_state["pipe_char"])

    with st.expander("Step 3: 世界", expanded=bool(st.session_state["pipe_char"])):
        if st.button("生成世界"):
            with st.spinner("极速生成..."):
                p = f"基于{novel_type}，生成简要世界观。150字。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_world"] = r.choices[0].message.content
                st.rerun()
    if st.session_state["pipe_world"]: st.session_state["pipe_world"] = st.text_area("✅ 世界", st.session_state["pipe_world"])

    with st.expander("Step 4: 大纲", expanded=bool(st.session_state["pipe_world"])):
        if st.button("生成细纲"):
            with st.spinner("推演大纲..."):
                p = f"梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。世界：{st.session_state['pipe_world']}。生成前三章细纲。"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["pipe_outline"] = r.choices[0].message.content
                st.rerun()
    if st.session_state["pipe_outline"]: st.session_state["pipe_outline"] = st.text_area("✅ 大纲", st.session_state["pipe_outline"])

# --- TAB 4: 审稿 ---
with tab_review:
    if st.button("🔍 毒舌审稿"):
        txt = "\n".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        if len(txt)<50: st.warning("字数太少")
        else:
            with st.spinner("审稿中..."):
                p = f"毒舌点评：\n{txt}"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.info(r.choices[0].message.content)
    data = {"history": st.session_state.chapters, "chars": st.session_state.characters}
    st.download_button("📥 导出全书", json.dumps(data, ensure_ascii=False), "novel.json")

# --- TAB 5: 周边 ---
with tab_extra:
    st.markdown("### 🔮 扩展")
    c1, c2 = st.columns(2)
    with c1:
        st.info("🎨 绘图提示词")
        d = st.text_area("画面描述", height=100)
        if st.button("✨ 生成咒语"):
            with st.spinner("翻译中..."):
                p = f"翻译为MJ/SD提示词(Prompt)：{d}"
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.code(r.choices[0].message.content)
    with c2:
        st.info("👾 虚拟书评")
        if st.button("💬 生成评论"):
            txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
            if len(txt)<100: st.warning("字数太少")
            else:
                with st.spinner("生成中..."):
                    p = f"扮演5个读者评论：{txt[:1000]}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.markdown(r.choices[0].message.content)
    
    with st.expander("🧹 一键排版"):
        raw = st.text_area("粘贴乱文本", height=150)
        if st.button("排版"):
            clean = re.sub(r'\n\s*\n', '\n', raw.strip())
            lines = [f"    {l.strip()}" for l in clean.split('\n') if l.strip()]
            st.text_area("结果", "\n\n".join(lines), height=200)