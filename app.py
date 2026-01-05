import streamlit as st
from openai import OpenAI
import json
import io
import zipfile

# ==========================================
# 0. 全局配置 & 初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="✒️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        "chapters": {1: []},
        "current_chapter": 1,
        # 流水线数据 (这些现在是可编辑的文本)
        "pipe_idea": "", 
        "pipe_cheat": "", 
        "pipe_level": "", 
        "pipe_char": "", 
        "pipe_outline": "",
        # 工具数据
        "codex": {}, "scrap_yard": [], "mimic_analysis": "",
        "logged_in": False, "first_visit": True, "daily_target": 3000,
        # 全局参数
        "global_novel_type": "玄幻", 
        "global_pov": "第三人称", 
        "global_tone": "正常",
        "global_pace": "快节奏",
        "global_word_limit": 1500,
        "global_burst_mode": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 🎨 视觉系统 (米白护眼 + 汉化)
# ==========================================
st.markdown("""
<style>
    /* 1. 背景：暖米白，护眼，高级 */
    .stApp {
        background-color: #fdfbf7; 
        color: #2c3e50;
    }
    
    /* 2. 侧边栏：纯白 + 极简边框 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #efebe9;
    }

    /* 3. 强力汉化补丁 */
    [data-testid='stFileUploader'] section { background-color: #fcfcfc; border: 1px dashed #b0a8a0; }
    [data-testid='stFileUploader'] section > input + div { display: none !important; }
    [data-testid='stFileUploader'] section::after {
        content: "📄 点击上传本地 TXT"; color: #8c7b70; display: block; text-align: center; padding: 10px;
    }
    [data-testid='stFileUploader'] small { display: none; }

    /* 4. 按钮美化 (深空灰蓝) */
    .stButton>button {
        background-color: #2c3e50; 
        color: #fdfbf7 !important; 
        border-radius: 4px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1a252f; transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* 5. 登录页火箭 */
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .rocket-logo {
        font-size: 80px; text-align: center; margin-bottom: 20px;
        animation: bounce 2s infinite ease-in-out; cursor: default;
    }

    /* 6. 卡片容器 */
    .card-box {
        background: #ffffff;
        padding: 30px; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #efebe9;
        margin-bottom: 20px;
    }
    
    /* 7. 文本域优化 (看起来更像编辑器) */
    .stTextArea textarea {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        font-family: 'PingFang SC', sans-serif;
        line-height: 1.6;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (火箭保留，背景干净)
# ==========================================
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><div class='rocket-logo'>🚀</div>", unsafe_allow_html=True)
        st.markdown('<div class="card-box" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h2 style='color:#333; margin:0;'>创世笔 GENESIS</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#888; font-size:14px; margin-bottom:20px;'>专业网文生产力工具</p>", unsafe_allow_html=True)
        
        with st.form("login"):
            pwd = st.text_input("密钥", type="password", placeholder="请输入 666", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🖊️ 提笔创作", use_container_width=True):
                if str(pwd).strip() == "666":
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("密钥错误 (666)")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. 侧边栏 (类型大扩容)
# ==========================================
with st.sidebar:
    st.markdown("### ✒️ 创世笔 `Pro`")
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: st.error("配置 API Key"); st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 1. 全局参数 (扩容版)
    with st.expander("⚙️ 全局设定 (影响所有生成)", expanded=True):
        # 真正够用的网文类型库
        all_genres = [
            "玄幻 | 东方玄幻", "玄幻 | 异世大陆", "玄幻 | 王朝争霸",
            "修仙 | 凡人流", "修仙 | 洪荒流", "修仙 | 无敌流",
            "都市 | 异术超能", "都市 | 赘婿打脸", "都市 | 官场职场", "都市 | 娱乐明星",
            "科幻 | 赛博朋克", "科幻 | 进化变异", "科幻 | 星际文明",
            "末世 | 囤货求生", "末世 | 丧尸围城", "末世 | 天灾降临",
            "悬疑 | 诡秘复苏", "悬疑 | 规则怪谈", "悬疑 | 侦探破案",
            "无限流 | 诸天综漫", "游戏 | 第四天灾", "历史 | 穿越种田",
            "女频 | 豪门总裁", "女频 | 宫斗宅斗", "女频 | 大女主",
            "自定义"
        ]
        t_sel = st.selectbox("📚 小说类型", all_genres)
        if t_sel == "自定义":
            st.session_state["global_novel_type"] = st.text_input("输入类型", "克苏鲁蒸汽朋克")
        else:
            st.session_state["global_novel_type"] = t_sel.split("|")[0]
            
        st.session_state["global_pov"] = st.selectbox("👁️ 视角", ["第三人称 (上帝)", "第一人称 (我)", "女主视角", "男主视角"])
        st.session_state["global_tone"] = st.select_slider("🎭 基调", ["严肃", "正常", "幽默", "暗黑", "爽文"], value="正常")
        st.session_state["global_pace"] = st.radio("⏱️ 节奏", ["快 (无脑爽)", "正常", "慢 (细节控)"], index=1)
        st.session_state["global_word_limit"] = st.number_input("单次字数", 500, 5000, 1500, step=100)
        st.session_state["global_burst_mode"] = st.toggle("🔥 强力扩写 (注水)", value=True)

    # 2. 档案室
    with st.expander("📂 档案室"):
        t1, t2 = st.tabs(["导入", "文风"])
        with t1:
            up_draft = st.file_uploader("传TXT续写", type=["txt"])
            if up_draft and st.button("确认导入"):
                c = up_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"旧稿：\n{c}"})
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":"✅ 已读取，请指示。"})
                st.success("导入成功")
        with t2:
            up_style = st.file_uploader("文风样本", type=["txt"])
            if up_style and st.button("学习"):
                c = up_style.getvalue().decode("utf-8")[:1500]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风：{c}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("已学习")

    # 3. 废稿篓
    with st.expander("🗑️ 废稿篓"):
        sc = st.text_area("暂存片段", height=60)
        if st.button("📥"): st.session_state["scrap_yard"].append(sc)
        if st.session_state["scrap_yard"]:
            st.caption("点击复制：")
            for i, txt in enumerate(st.session_state["scrap_yard"]):
                st.code(txt, language="text")

# ==========================================
# 4. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 流水线 (5步)", "🔮 灵感外挂", "💾 导出"])

# --- TAB 1: 沉浸写作 (核心) ---
with tab_write:
    # 组装 Prompt (这里会读取你在流水线里修改后的最终结果！)
    p = st.session_state
    ctx = f"类型：{p['global_novel_type']}。视角：{p['global_pov']}。基调：{p['global_tone']}。节奏：{p['global_pace']}。"
    
    # 只有当用户在流水线里填了内容，才会加进 Prompt
    if p["pipe_char"]: ctx += f"\n【角色档案】{p['pipe_char']}"
    if p["pipe_cheat"]: ctx += f"\n【金手指】{p['pipe_cheat']}"
    if p["pipe_level"]: ctx += f"\n【等级体系】{p['pipe_level']}"
    if p["pipe_outline"]: ctx += f"\n【大纲】{p['pipe_outline']}"
    if p["mimic_analysis"]: ctx += f"\n【文风模仿】{p['mimic_analysis']}"
    if p["codex"]: ctx += f"\n【设定集】{str(p['codex'])}"
    
    sys_p = f"你是由DeepSeek驱动的网文大神。{ctx}\n字数目标：{p['global_word_limit']}。{'【强力扩写】注重环境光影、动作细节。' if p['global_burst_mode'] else ''}\n禁止客套，直接输出正文。"

    # 聊天显示
    container = st.container(height=500)
    history = st.session_state["chapters"][st.session_state.current_chapter]
    with container:
        if not history: st.info(f"✨ 准备就绪。当前类型：{p['global_novel_type']}。请下达第一个指令。")
        for msg in history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "✒️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 工具栏
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.expander("🛠️ 润色/体检"):
            bad = st.text_area("片段", height=60, placeholder="粘贴不满意的片段")
            if st.button("✨ 润色"):
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                st.write_stream(s)
            if st.button("🩺 全文体检"):
                full = "".join([m["content"] for m in history if m["role"]=="assistant"])
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析这章的节奏和爽点：{full}"}], stream=True)
                st.write_stream(s)
    with c2:
        with st.expander("🛡️ 敏感词雷达"):
            if st.button("🔍 扫描"):
                txt = "".join([m["content"] for m in history])
                risky = ["杀人", "死", "血", "色情", "政治"]
                found = [w for w in risky if w in txt]
                if found: st.error(f"发现敏感词：{found}")
                else: st.success("内容安全")

    # 输入区
    st.divider()
    c_in, c_btn = st.columns([5, 1])
    with c_in: 
        manual = st.text_input("💡 剧情微操 (选填)", placeholder="导演指令：如'主角突然发现宝箱'...")
    with c_btn:
        st.write(""); st.write("")
        if st.button("🔄 继续写", use_container_width=True):
            p_text = f"接着写。{'注意：'+manual if manual else ''}"
            history.append({"role":"user", "content":p_text})
            with container:
                st.chat_message("user", avatar="🧑‍💻").write(p_text)
                with st.chat_message("assistant", avatar="✒️"):
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                    r = st.write_stream(s)
            history.append({"role":"assistant", "content":r})

    if prompt := st.chat_input("输入剧情指令..."):
        history.append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="✒️"):
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                r = st.write_stream(s)
        history.append({"role":"assistant", "content":r})

# --- TAB 2: 流水线 (可编辑、可重来、可微调) ---
with tab_pipeline:
    st.info(f"正在策划：{st.session_state['global_novel_type']}。觉得不满意可以随时修改文本框内容，或者点击重新生成。")
    planner = "你是一个网文策划。只写设定，不写正文。"
    
    # 统一的生成逻辑函数
    def generate_step(step_key, prompt, label):
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button(f"✨ 生成{label}", key=f"btn_{step_key}"):
                with st.spinner("AI 正在头脑风暴..."):
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":prompt}])
                    st.session_state[step_key] = r.choices[0].message.content
                    st.rerun()
        with c2:
            refine = st.text_input(f"对{label}不满意？输入修改意见：", key=f"refine_{step_key}", placeholder="例如：再黑暗一点，反派再强一点")
            if refine and st.button(f"🛠️ 微调{label}", key=f"adj_{step_key}"):
                 with st.spinner("AI 正在修改..."):
                    p_refine = f"原内容：{st.session_state[step_key]}。修改要求：{refine}。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":p_refine}])
                    st.session_state[step_key] = r.choices[0].message.content
                    st.rerun()
        
        # 核心：可编辑的文本框
        st.session_state[step_key] = st.text_area(f"📄 {label} (可直接编辑)", value=st.session_state[step_key], height=150, key=f"area_{step_key}")

    # Step 1: 脑洞
    with st.expander("Step 1: 脑洞 (必填)", expanded=True):
        idea_input = st.text_input("输入核心创意/点子", placeholder="例如：重生回高考前，但我有了透视眼")
        generate_step("pipe_idea", f"类型：{st.session_state['global_novel_type']}。基于点子生成核心梗：{idea_input}", "脑洞")

    # Step 2: 金手指
    with st.expander("Step 2: 金手指 (选填)", expanded=False):
        st.caption("如果不生成，AI将按凡人流处理。")
        generate_step("pipe_cheat", f"基于脑洞：{st.session_state['pipe_idea']}。设计一个爽感强的金手指（系统/宝物/天赋）。", "金手指")

    # Step 3: 世界观
    with st.expander("Step 3: 世界/等级 (选填)", expanded=False):
        st.caption("如果不生成，AI将按该类型的默认设定处理。")
        generate_step("pipe_level", f"基于类型：{st.session_state['global_novel_type']}。设计等级体系（从低到高）和世界势力分布。", "世界观")

    # Step 4: 人设
    with st.expander("Step 4: 人设 (建议生成)", expanded=False):
        generate_step("pipe_char", f"基于脑洞：{st.session_state['pipe_idea']}。生成主角（姓名、性格、外貌）和主要反派档案。", "人设")

    # Step 5: 大纲
    with st.expander("Step 5: 大纲 (建议生成)", expanded=False):
        generate_step("pipe_outline", f"综合以上设定，生成前三章细纲，要有爽点和钩子。", "大纲")

# --- TAB 3: 灵感外挂 ---
with tab_tools:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🎬 万能场面")
        t = st.selectbox("类型", ["打斗", "感情", "装逼", "景色"])
        d = st.text_input("描述")
        if st.button("生成场面"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"写一段{t}：{d}"}], stream=True)
            st.write_stream(s)
    with c2:
        st.markdown("#### 🎲 起名器")
        nt = st.selectbox("起名", ["人名", "宗门", "功法", "地名"])
        if st.button("生成名字"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"生成5个{st.session_state['global_novel_type']}风格的{nt}"}])
            st.code(r.choices[0].message.content)
            
    st.divider()
    if st.button("🃏 命运卡牌：解决卡文"):
        r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":"给一个意想不到的剧情转折灵感，一句话。"}])
        st.info(f"💡 灵感：{r.choices[0].message.content}")

# --- TAB 4: 导出 ---
with tab_publish:
    at = ""
    for ch, msgs in st.session_state["chapters"].items():
        t = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        at += f"\n\n### 第 {ch} 章 ###\n\n{t}"
    
    st.download_button("📥 下载纯净TXT", at.replace("**","").replace("##",""), "novel.txt")
    if st.button("📦 打包ZIP"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                c = "".join([m["content"] for m in msgs if m["role"]=="assistant"]).replace("**","")
                z.writestr(f"Chapter_{ch}.txt", c)
        st.download_button("📥 下载ZIP", buf.getvalue(), "chapters.zip", mime="application/zip")