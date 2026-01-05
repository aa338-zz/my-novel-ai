import streamlit as st
from openai import OpenAI
import json
import io
import zipfile
import time

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
        # 构思蓝图 (6步)
        "pipe_hook": "", "pipe_cheat": "", "pipe_world": "", 
        "pipe_char": "", "pipe_plot": "", "pipe_trial": "",
        # 工具
        "codex": {}, "scrap_yard": [], "mimic_analysis": "",
        "logged_in": False, "first_visit": True,
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
# 1. 🎨 视觉系统 (米白护眼 + 火箭登录)
# ==========================================
st.markdown("""
<style>
    /* 1. 背景：暖米白 */
    .stApp { background-color: #fdfbf7; color: #2c3e50; }
    
    /* 2. 侧边栏 */
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #efebe9; }

    /* 3. 汉化补丁 */
    [data-testid='stFileUploader'] section { background-color: #fcfcfc; border: 1px dashed #b0a8a0; }
    [data-testid='stFileUploader'] section > input + div { display: none !important; }
    [data-testid='stFileUploader'] section::after { content: "📄 点击上传本地 TXT"; color: #8c7b70; display: block; text-align: center; padding: 10px; }
    [data-testid='stFileUploader'] small { display: none; }

    /* 4. 按钮美化 */
    .stButton>button {
        background-color: #2c3e50; color: #fdfbf7 !important; 
        border-radius: 4px; border: none; font-weight: 600; padding: 0.6rem 1.2rem;
        transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #1a252f; transform: translateY(-1px); }
    
    /* 5. 火箭动画 */
    @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    .rocket-logo { font-size: 80px; text-align: center; margin-bottom: 20px; animation: bounce 2s infinite ease-in-out; cursor: default; }

    /* 6. 手机预览框 */
    .mobile-frame {
        width: 320px; height: 500px; background: #fff; border: 8px solid #333; border-radius: 20px;
        margin: 0 auto; padding: 15px; overflow-y: scroll; font-size: 14px; line-height: 1.6; color: #333;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    
    /* 7. 复制专用框 (伪装成代码块以获得复制按钮) */
    .copy-box { border-left: 4px solid #2ecc71; background: #f0fff4; padding: 10px; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑
# ==========================================
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br><div class='rocket-logo'>🚀</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#333;'>创世笔 GENESIS</h2>", unsafe_allow_html=True)
        with st.form("login"):
            pwd = st.text_input("密钥", type="password", placeholder="请输入 666", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🖊️ 提笔创作", use_container_width=True):
                if str(pwd).strip() == "666": st.session_state["logged_in"] = True; st.rerun()
                else: st.error("密钥错误 (666)")
    st.stop()

# ==========================================
# 3. 侧边栏 (全局参数)
# ==========================================
with st.sidebar:
    st.markdown("### ✒️ 创世笔 `Pro`")
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key: st.error("需配置 API Key"); st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    with st.expander("⚙️ 全局设定", expanded=True):
        all_genres = [
            "玄幻 | 东方玄幻", "修仙 | 凡人流", "都市 | 爽文", "科幻 | 赛博", 
            "末世 | 囤货", "悬疑 | 诡秘", "无限 | 综漫", "女频 | 豪门", "自定义"
        ]
        t_sel = st.selectbox("📚 类型", all_genres)
        st.session_state["global_novel_type"] = st.text_input("输入类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel.split("|")[0]
        
        st.session_state["global_pov"] = st.selectbox("👁️ 视角", ["第三人称", "第一人称", "女主视角"])
        st.session_state["global_tone"] = st.select_slider("🎭 基调", ["严肃", "正常", "幽默", "暗黑", "爽文"], value="正常")
        st.session_state["global_pace"] = st.radio("⏱️ 节奏", ["快 (爽文)", "正常", "慢 (细节)"], index=1)
        st.session_state["global_word_limit"] = st.number_input("字数/次", 500, 5000, 1500, 100)
        st.session_state["global_burst_mode"] = st.toggle("🔥 强力扩写", value=True)

    with st.expander("🗑️ 废稿篓"):
        sc = st.text_area("暂存", height=60)
        if st.button("📥"): st.session_state["scrap_yard"].append(sc)

# ==========================================
# 4. 主工作区
# ==========================================
tab_write, tab_plan, tab_lib, tab_pub = st.tabs(["✍️ 沉浸写作", "🏗️ 构思蓝图", "📖 素材库", "💾 发书中心"])

# --- TAB 1: 沉浸写作 (集大成者) ---
with tab_write:
    # 1. 顶部：档案室 (用户要求的：放在这里！)
    with st.expander("📂 导入 / 续写 / 文风 (已移至此处)", expanded=False):
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            st.markdown("#### 📝 上传旧稿续写")
            up_draft = st.file_uploader("上传TXT", type=["txt"], key="draft_new")
            if up_draft and st.button("开始续写"):
                c = up_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":f"这是我之前写的内容，请读取并准备续写：\n\n{c}"})
                st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":f"✅ 已读取 {len(c)} 字旧稿。请告诉我接下来剧情怎么发展？"})
                st.success("导入成功！")
                st.rerun()
        with c_a2:
            st.markdown("#### 🧬 模仿大神文风")
            up_style = st.file_uploader("上传样本", type=["txt"], key="style_new")
            if up_style and st.button("分析文风"):
                c = up_style.getvalue().decode("utf-8")[:1500]
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风：{c}"}])
                st.session_state["mimic_analysis"] = r.choices[0].message.content
                st.success("学习完成！")

    # 2. 核心 Prompt
    p = st.session_state
    ctx = f"类型：{p['global_novel_type']}。视角：{p['global_pov']}。基调：{p['global_tone']}。节奏：{p['global_pace']}。"
    if p["pipe_char"]: ctx += f"\n【人设】{p['pipe_char']}"
    if p["pipe_cheat"]: ctx += f"\n【金手指】{p['pipe_cheat']}"
    if p["pipe_world"]: ctx += f"\n【世界】{p['pipe_world']}"
    if p["pipe_trial"]: ctx += f"\n【前文试写】{p['pipe_trial']}"
    if p["mimic_analysis"]: ctx += f"\n【模仿】{p['mimic_analysis']}"
    if p["codex"]: ctx += f"\n【设定】{str(p['codex'])}"
    
    sys_p = f"你是由DeepSeek驱动的网文大神。{ctx}\n字数目标：{p['global_word_limit']}。{'【强力扩写】注重画面、心理、细节。' if p['global_burst_mode'] else ''}\n禁止客套，直接输出正文。"

    # 3. 聊天显示
    container = st.container(height=500)
    history = st.session_state["chapters"][st.session_state.current_chapter]
    with container:
        if not history: st.info(f"✨ 准备就绪。当前类型：{p['global_novel_type']}。")
        for msg in history:
            avatar = "🧑‍💻" if msg["role"] == "user" else "✒️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 4. 底部工具栏
    c_t1, c_t2 = st.columns([1, 1])
    with c_t1:
        # 一键复制功能：利用 st.code 的右上角复制按钮
        if history and history[-1]["role"] == "assistant":
            st.caption("📋 一键复制下方内容：")
            st.code(history[-1]["content"], language="text") # Hack: 文本代码块
    with c_t2:
        with st.popover("🛠️ 精修工具箱"):
            t1, t2 = st.tabs(["润色", "重写"])
            with t1:
                bad = st.text_area("片段")
                if st.button("✨ 润色"):
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色：{bad}"}], stream=True)
                    st.write_stream(s)
            with t2:
                if st.button("💥 本章推翻重写"):
                    history.append({"role":"user", "content":"重写本章"})
                    s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                    r = st.write_stream(s)
                    history.append({"role":"assistant", "content":r})

    # 5. 输入区
    st.divider()
    c_in, c_btn = st.columns([5, 1])
    with c_in: manual = st.text_input("💡 剧情微操", placeholder="导演指令...")
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

    if prompt := st.chat_input("输入剧情..."):
        history.append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="✒️"):
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys_p}]+history, stream=True)
                r = st.write_stream(s)
        history.append({"role":"assistant", "content":r})

# --- TAB 2: 构思蓝图 (6步法) ---
with tab_plan:
    st.info(f"正在构思：{st.session_state['global_novel_type']}。所有内容均可手动修改。")
    planner = "你是一个网文策划。只写设定。"
    
    def step_gen(key, prompt, label):
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button(f"✨ 生成{label}", key=f"b_{key}"):
                s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner},{"role":"user","content":prompt}], stream=True)
                st.session_state[key] = st.write_stream(s)
                st.rerun()
        with c2:
            st.session_state[key] = st.text_area(f"{label} (可编辑)", st.session_state[key], height=100, key=f"t_{key}")

    # 1. 卖点
    with st.expander("Step 1: 卖点与书名", expanded=True):
        idea = st.text_input("原始脑洞")
        step_gen("pipe_hook", f"基于脑洞：{idea}。生成3个爆款书名、一句话核心梗、简介。", "卖点")
    
    # 2. 金手指
    with st.expander("Step 2: 金手指", expanded=False):
        step_gen("pipe_cheat", f"基于{st.session_state['pipe_hook']}。设计外挂机制和代价。", "金手指")

    # 3. 世界
    with st.expander("Step 3: 世界与等级", expanded=False):
        step_gen("pipe_world", f"基于类型{st.session_state['global_novel_type']}。设计等级体系和势力。", "世界")
    
    # 4. 人设
    with st.expander("Step 4: 人物关系", expanded=False):
        step_gen("pipe_char", f"基于前文。设计主角、反派、CP档案。", "人设")
    
    # 5. 大纲
    with st.expander("Step 5: 爽点大纲", expanded=False):
        step_gen("pipe_plot", f"综合设定。生成前三章细纲，标注爽点。", "大纲")
    
    # 6. 试写
    with st.expander("Step 6: 开篇试写 (Trial)", expanded=False):
        step_gen("pipe_trial", f"基于所有设定。试写第一章开头500字。", "试写")

# --- TAB 3: 素材库 ---
with tab_lib:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📖 描写词典")
        k = st.text_input("关键词", placeholder="如：愤怒、打斗、环境阴森")
        if st.button("查询描写素材"):
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"针对关键词'{k}'，写3段不同风格的神态、动作、环境描写素材。"}], stream=True)
            st.write_stream(s)
    with c2:
        st.markdown("#### ⚖️ 逻辑质检")
        if st.button("扫描全书逻辑漏洞"):
            txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
            s = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于设定检查正文逻辑漏洞：{txt[:2000]}"}], stream=True)
            st.write_stream(s)

# --- TAB 4: 发书中心 (4大金刚) ---
with tab_pub:
    txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter] if m["role"]=="assistant"])
    word_count = len(txt)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("当前字数", word_count)
        if word_count < 2000: st.error("🔴 字数不足 2000")
        elif word_count > 4000: st.warning("🟡 建议分章")
        else: st.success("🟢 字数完美")
        st.download_button("📥 导出 TXT", txt, "novel.txt")
    
    with c2:
        st.markdown("#### 🎨 封面生成")
        if st.button("生成 AI 绘画提示词"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于小说类型{st.session_state['global_novel_type']}，生成一段英文 AI 绘画 Prompt，用于做封面。"}])
            st.code(r.choices[0].message.content)
            
    with c3:
        st.markdown("#### 📢 推广文案")
        if st.button("生成抖音推书文案"):
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"为这本小说写一段抖音推书文案，开头要吸引人。"}])
            st.info(r.choices[0].message.content)

    st.divider()
    with st.expander("📱 手机端阅读预览", expanded=True):
        st.markdown(f"""
        <div class="mobile-frame">
            <h3 style="text-align:center;">{st.session_state.get('pipe_hook', '小说预览')}</h3>
            {txt.replace('\n', '<br>')}
        </div>
        """, unsafe_allow_html=True)