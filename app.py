import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import datetime

# ==========================================
# 0. 全局配置 & 初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 核心记忆库初始化
if "init_done" not in st.session_state:
    # 基础数据
    st.session_state["chapters"] = {1: []} # 章节内容
    st.session_state["current_chapter"] = 1
    st.session_state["history_snapshots"] = [] # 🔄 时光机快照
    
    # 设定与流水线
    st.session_state["pipe_idea"] = ""
    st.session_state["pipe_char"] = ""
    st.session_state["pipe_world"] = ""
    st.session_state["pipe_outline"] = ""
    
    # 工具状态
    st.session_state["codex"] = {} # 📕 设定集
    st.session_state["scrap_yard"] = [] # 🗑️ 废稿
    st.session_state["mimic_analysis"] = "" 
    st.session_state["logged_in"] = False
    
    # 统计
    st.session_state["daily_target"] = 3000
    st.session_state["init_done"] = True

# ==========================================
# 1. 样式美化 (CSS)
# ==========================================
st.markdown("""
<style>
    /* 全局字体与配色 */
    .stApp {background-color: #ffffff; color: #1a1a1a;}
    
    /* 侧边栏优化 */
    section[data-testid="stSidebar"] {background-color: #f7f9fb; border-right: 1px solid #e0e0e0;}
    
    /* 按钮：微立体感 */
    .stButton>button {
        background-color: #007bff; color: white !important; 
        border-radius: 6px; border: none; font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,123,255,0.2);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #0056b3; transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,123,255,0.3);
    }
    
    /* 输入框优化 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput input {
        background-color: #fff; border: 1px solid #ced4da; border-radius: 6px;
    }
    .stTextInput>div>div>input:focus {border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,.25);}

    /* 聊天气泡优化 */
    .stChatMessage {background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; margin-bottom: 10px;}
    
    /* 红色高亮 */
    .alert-word {color: #d93025; font-weight: bold; background-color: #ffe6e6; padding: 0 4px; border-radius: 3px;}
    
    /* 系统面板风格 */
    .system-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border: 2px solid #2196f3; border-radius: 8px; padding: 15px;
        color: #0d47a1; font-family: monospace; box-shadow: 0 4px 10px rgba(33, 150, 243, 0.15);
    }
    
    /* 隐藏水印 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录门禁
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666")
                if st.form_submit_button("🚀 启动创作引擎", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：指挥塔
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 神经网络：在线")
    else:
        st.error("🔴 请配置 API Key")
        st.stop()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # --- 📊 码字仪表盘 (新增) ---
    st.divider()
    current_text_len = len("".join([m["content"] for m in st.session_state["chapters"][st.session_state["current_chapter"]] if m["role"]=="assistant"]))
    progress = min(current_text_len / st.session_state["daily_target"], 1.0)
    st.markdown(f"**🔥 今日成就** ({current_text_len} / {st.session_state['daily_target']} 字)")
    st.progress(progress)
    if progress >= 1.0: st.balloons()

    st.divider()

    # --- 📖 章节导航 ---
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2:
        st.caption(f"第 {st.session_state.current_chapter} 章")
    
    # --- 🔄 时光机 (新增) ---
    if st.button("⏪ 撤销上一步 (时光机)", use_container_width=True):
        if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
            # 移除最后一次问答
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.session_state["chapters"][st.session_state.current_chapter].pop()
            st.toast("已回溯到上一步", icon="↩️")
            st.rerun()
        else:
            st.warning("已经是起点了！")

    st.divider()

    # --- 📕 设定集 / 词条 (新增) ---
    with st.expander("📕 设定集 (Codex)"):
        new_term = st.text_input("新词条名", placeholder="如：青莲地心火")
        new_desc = st.text_input("描述", placeholder="排名19的异火...")
        if st.button("➕ 收录"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已收录")
        
        st.caption("已收录词条：")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    # --- 🗑️ 废稿回收站 ---
    with st.expander("🗑️ 废稿回收站"):
        scrap = st.text_area("存入片段", height=60, placeholder="粘贴不要的文字...")
        if st.button("📥 存入废稿"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("已保存")
        if st.session_state["scrap_yard"]:
            st.divider()
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")

    # --- 🔍 查找替换 ---
    with st.expander("🔍 查找替换"):
        fw = st.text_input("查找")
        rw = st.text_input("替换为")
        if st.button("🔄 全局替换") and fw:
            count = 0
            for ch, msgs in st.session_state["chapters"].items():
                for m in msgs:
                    if fw in m["content"]: m["content"] = m["content"].replace(fw, rw); count+=1
            st.toast(f"已替换 {count} 处", icon="✅")
            st.rerun()

    # --- 🛡️ 违禁词雷达 ---
    with st.expander("🛡️ 违禁词雷达"):
        if st.button("🔴 扫描本章"):
            risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "爆炸"]
            txt = "".join([m["content"] for m in st.session_state["chapters"][st.session_state.current_chapter]])
            found = []
            for w in risky:
                if w in txt: found.append(w)
            if found: st.error(f"发现敏感词: {list(set(found))}")
            else: st.success("内容安全")

    st.divider()
    
    # --- ⚙️ 核心参数 ---
    all_types = ["末世 | 囤货基地", "末世 | 丧尸围城", "末世 | 废土进化", "玄幻 | 东方玄幻", "都市 | 异术超能", "都市 | 战神赘婿", "历史 | 架空历史", "科幻 | 赛博朋克", "无限流 | 诸天万界", "悬疑 | 规则怪谈", "女频 | 豪门总裁", "女频 | 宫斗宅斗", "自定义"]
    t_sel = st.selectbox("小说类型", all_types)
    novel_type = st.text_input("输入类型", "克苏鲁修仙") if t_sel == "自定义" else t_sel
    word_target = st.number_input("单次生成字数", 100, 5000, 800, 100)
    burst_mode = st.toggle("强力扩写模式", value=True)

# ==========================================
# 4. 主工作区
# ==========================================
tab_write, tab_pipeline, tab_edit, tab_tools, tab_export = st.tabs(["✍️ 沉浸写作", "🚀 创作流水线", "✨ 精修与微操", "🔮 灵感外挂", "💾 导出发布"])

# --- TAB 1: 沉浸写作 (核心流式) ---
with tab_write:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章")
    
    # 上下文拼装
    context_prompt = ""
    if st.session_state["pipe_char"]: context_prompt += f"\n【角色档案】{st.session_state['pipe_char']}"
    if st.session_state["pipe_world"]: context_prompt += f"\n【世界观】{st.session_state['pipe_world']}"
    if st.session_state["pipe_outline"]: context_prompt += f"\n【大纲】{st.session_state['pipe_outline']}"
    if st.session_state["mimic_analysis"]: context_prompt += f"\n【文风模仿】{st.session_state['mimic_analysis']}"
    if st.session_state["codex"]: 
        context_prompt += f"\n【已收录设定】{str(st.session_state['codex'])}" # 把设定集喂给 AI

    instruction = f"字数目标：{word_target}。" + ("【强力扩写】请进行详细描写，注重心理、环境、动作细节。" if burst_mode else "")
    
    system_prompt = f"""
    你是由DeepSeek驱动的网文大神。类型：{novel_type}。
    {context_prompt}
    {instruction}
    禁止输出任何客套话（如“好的”），直接输出正文。
    """

    # 聊天记录显示
    container = st.container(height=500)
    current_msgs = st.session_state.chapters[st.session_state.current_chapter]
    
    with container:
        if not current_msgs: st.info("✨ 准备就绪，输入第一句开始创作...")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            content = msg["content"]
            # 长文折叠优化
            if len(content) > 800 and "前文" in content: content = content[:200] + "...\n(已折叠前文)"
            st.chat_message(msg["role"], avatar=avatar).write(content)

    # 剧情微操栏
    st.markdown("---")
    c1, c2 = st.columns([5, 1])
    with c1:
        manual_plot = st.text_input("💡 剧情定向 (微操)", placeholder="例如：主角在转角处突然遇到前女友... (留空则 AI 自由发挥)")
    with c2:
        st.write("")
        st.write("")
        btn_continue = st.button("🔄 继续写", use_container_width=True)

    # 输入处理
    if prompt := st.chat_input("输入对话或剧情指令..."):
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}] + current_msgs, stream=True, temperature=1.2)
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # 继续写逻辑
    if btn_continue:
        next_prompt = f"接着上文写。注意：{manual_plot}。" if manual_plot else "接着上文继续写，保持连贯。"
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":next_prompt})
        with container:
            st.chat_message("user", avatar="🧑‍💻").write(next_prompt)
            with st.chat_message("assistant", avatar="🖊️"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}] + current_msgs, stream=True, temperature=1.2)
                response = st.write_stream(stream)
        st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":response})

# --- TAB 2: 创作流水线 (逻辑加固版) ---
with tab_pipeline:
    st.info("Step by Step 打造世界。支持手动修改，AI 会自动读取最新修改。")
    
    # 1. 脑洞
    with st.expander("Step 1: 脑洞", expanded=not st.session_state["pipe_idea"]):
        c1, c2 = st.columns([3,1])
        idea = c1.text_input("点子")
        if c2.button("✨ 生成梗"):
            p = f"基于点子“{idea}”，为{novel_type}生成核心梗。100字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_idea"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_idea"]:
        st.session_state["pipe_idea"] = st.text_area("✅ 脑洞 (可修改)", st.session_state["pipe_idea"], height=100)

    # 2. 人设
    with st.expander("Step 2: 人设", expanded=bool(st.session_state["pipe_idea"])):
        if st.button("👥 生成人设"):
            p = f"基于梗“{st.session_state['pipe_idea']}”，生成主角反派。200字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_char"]:
        st.session_state["pipe_char"] = st.text_area("✅ 人设 (可修改)", st.session_state["pipe_char"], height=200)

    # 3. 世界
    with st.expander("Step 3: 世界", expanded=bool(st.session_state["pipe_char"])):
        if st.button("🌍 生成世界"):
            p = f"基于{novel_type}，生成简要世界观。150字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_world"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_world"]:
        st.session_state["pipe_world"] = st.text_area("✅ 世界 (可修改)", st.session_state["pipe_world"], height=150)

    # 4. 大纲
    with st.expander("Step 4: 大纲", expanded=bool(st.session_state["pipe_world"])):
        if st.button("📜 生成细纲"):
            p = f"梗：{st.session_state['pipe_idea']}。人设：{st.session_state['pipe_char']}。世界：{st.session_state['pipe_world']}。生成前三章细纲。严禁输出废话。"
            st.markdown("**AI 推演中...**")
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.session_state["pipe_outline"] = st.write_stream(stream)
            st.rerun()
    if st.session_state["pipe_outline"]:
        st.session_state["pipe_outline"] = st.text_area("✅ 大纲 (可修改)", st.session_state["pipe_outline"], height=300)

# --- TAB 3: 精修与微操 (整合版) ---
with tab_edit:
    st.markdown("### 🛠️ 章节精修工厂")
    
    t1, t2, t3 = st.tabs(["📋 全文复制/查看", "✍️ 局部润色", "💥 整章重写"])
    
    with t1:
        st.caption("右上角一键复制纯文本 👇")
        full_text = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
        st.code(full_text if full_text else "暂无内容", language="text")
        
    with t2:
        c1, c2 = st.columns(2)
        with c1: bad = st.text_area("粘贴不满意的片段", height=150)
        with c2: req = st.text_area("修改要求", height=150, placeholder="例：写得更有画面感一点")
        if st.button("✨ 润色片段"):
            if bad and req:
                p = f"修改片段：{bad}\n要求：{req}\n直接输出修改后内容。"
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                st.write_stream(stream)
                
    with t3:
        req_full = st.text_input("整章重写意见")
        if st.button("💥 推翻重写"):
            if full_text:
                p = f"重写本章，要求：{req_full}。保留核心逻辑。"
                st.session_state.chapters[st.session_state.current_chapter].append({"role":"user", "content":p})
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":system_prompt}]+current_msgs, stream=True)
                st.session_state.chapters[st.session_state.current_chapter].append({"role":"assistant", "content":""}) # 占位
                st.rerun() # 实际使用建议跳转回写作Tab看流式，这里简化

# --- TAB 4: 灵感外挂 (全家桶) ---
with tab_tools:
    st.markdown("### 🔮 创意军火库")
    
    # 1. 战斗演算 + 过桥
    c1, c2 = st.columns(2)
    with c1:
        st.info("⚔️ 战斗场面生成")
        fighter = st.text_input("对战双方 & 招式")
        if st.button("👊 生成打斗"):
            p = f"描写一场战斗：{fighter}。要求：画面炸裂，招式细节，300字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
    with c2:
        st.info("🌉 剧情过桥 (水文神器)")
        bridge = st.text_input("从哪里过渡到哪里？")
        if st.button("🚶 生成过渡段"):
            p = f"写一段过渡剧情：{bridge}。要求：描写环境、心理、赶路，300字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
            
    st.divider()
    
    # 2. 语音速记 + 绘图
    c3, c4 = st.columns(2)
    with c3:
        st.info("🗣️ 粗纲/语音 润色")
        raw_talk = st.text_area("输入大白话/语音转文字内容", height=100)
        if st.button("✨ 润色成正文"):
            p = f"将这段口语/大纲扩写成小说正文：{raw_talk}"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)
    with c4:
        st.info("🎨 封面提示词")
        desc = st.text_area("画面描述", height=100)
        if st.button("🖼️ 生成 Prompt"):
            p = f"Translate to Midjourney Prompt: {desc}. High quality."
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.code(r.choices[0].message.content)

    st.divider()
    
    # 3. 系统生成 + 风格提取
    c5, c6 = st.columns(2)
    with c5:
        st.info("📟 系统面板")
        sys_txt = st.text_input("获得奖励内容")
        if st.button("生成面板"):
            st.markdown(f"""<div class="system-box">【系统提示】<br>⚡ 触发：{sys_txt}</div>""", unsafe_allow_html=True)
    with c6:
        st.info("🧬 风格提取")
        f = st.file_uploader("上传样本", type=["txt"])
        if f and st.button("分析"):
            raw = f.getvalue().decode("utf-8")[:1000]
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"分析文风:{raw}"}])
            st.session_state["mimic_analysis"] = r.choices[0].message.content
            st.success("已提取并应用")

# --- TAB 5: 导出发布 (Smart Export) ---
with tab_export:
    st.markdown("### 💾 发布中心")
    
    # 1. 纯文本打包
    full_book_text = ""
    for ch, msgs in st.session_state["chapters"].items():
        ch_txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        full_book_text += f"\n\n### 第 {ch} 章 ###\n\n{ch_txt}"
    
    # 清洗 Markdown (去除 ** 等符号)
    clean_text = full_book_text.replace("**", "").replace("##", "").replace("`", "")
    
    st.download_button(
        label="📥 导出全书 (纯净TXT版)",
        data=clean_text,
        file_name=f"novel_full_clean.txt",
        mime="text/plain"
    )
    
    st.divider()
    
    # 2. 备份 JSON
    st.caption("备份数据 (包含设定、大纲、废稿)")
    backup_data = {
        "chapters": st.session_state["chapters"],
        "codex": st.session_state["codex"],
        "pipeline": {
            "idea": st.session_state["pipe_idea"],
            "outline": st.session_state["pipe_outline"]
        }
    }
    st.download_button("📥 导出完整备份 (.json)", json.dumps(backup_data, ensure_ascii=False), "backup.json")