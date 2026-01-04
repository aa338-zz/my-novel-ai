import streamlit as st
from openai import OpenAI
import json
import io
import zipfile
import re
import time
import random

# ==========================================
# 0. 全局配置 (System Configuration)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 (完整旗舰版)", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 强制初始化 Session State，确保所有变量都在内存中
# 这里我不做任何删减，保留你之前可能需要的每一个变量位
def init_session():
    defaults = {
        "chapters": {1: []},           # 存储章节内容
        "current_chapter": 1,          # 当前章节
        "history_snapshots": [],       # 历史快照（预留功能）
        "pipe_idea": "",               # 流水线：脑洞
        "pipe_char": "",               # 流水线：人设
        "pipe_world": "",              # 流水线：世界观
        "pipe_outline": "",            # 流水线：大纲
        "codex": {},                   # 设定集字典
        "scrap_yard": [],              # 废稿篓列表
        "mimic_analysis": "",          # 文风分析缓存
        "logged_in": False,            # 登录状态
        "daily_target": 3000,          # 每日字数目标
        "first_visit": True,           # 是否首次访问
        "last_generated_content": "",  # 【新增】专门用于一键复制的缓存
        "init_done": True              # 初始化完成标记
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (CSS Injection)
# ==========================================
# 保留原本的蓝色主题，增加高亮样式
st.markdown("""
<style>
    /* 全局背景与字体 */
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    
    /* 侧边栏样式优化 */
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    /* 按钮样式增强 */
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 违禁词高亮样式 (红色背景+加粗) */
    .risky-word {
        background-color: #ffe3e3;
        color: #e03131;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #ffa8a8;
        margin: 0 2px;
    }
    
    /* 系统提示框 */
    .system-box {
        background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%);
        border: 2px solid #339af0; border-radius: 8px; padding: 15px;
        color: #1864ab; font-family: 'Courier New', monospace; font-weight: bold;
    }
    
    /* 登录页动画 */
    @keyframes breathe {
        0% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
        50% { transform: scale(1.1); opacity: 1; text-shadow: 0 0 25px #228be6; }
        100% { transform: scale(1); opacity: 0.8; text-shadow: 0 0 10px #228be6; }
    }
    .login-logo {
        font-size: 80px; text-align: center; margin-bottom: 20px;
        animation: breathe 3s infinite ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (Authentication)
# ==========================================
# 这是一个简易的密码验证，实际部署可对接数据库
USERS = {"vip": "666", "admin": "admin"} 

def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown('<div class="login-logo">⚡</div>', unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>GENESIS · 创世笔</h2>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.info("请输入通行密钥以解锁完整功能")
                # 使用 label_visibility="collapsed" 隐藏标签，保持界面简洁
                user_input = st.text_input("账号", placeholder="用户名 (任意)", label_visibility="collapsed")
                st.write("")
                pwd_input = st.text_input("密码", type="password", placeholder="请输入密钥 (666)", label_visibility="collapsed")
                st.write("")
                
                submitted = st.form_submit_button("🚀 启动引擎", use_container_width=True)
                if submitted:
                    if pwd_input in USERS.values():
                        st.session_state["logged_in"] = True
                        st.toast("身份验证成功！欢迎回来。", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("密钥错误，请重试。")
        st.stop() # 阻止后续代码运行

check_login()

# ==========================================
# 3. 侧边栏：指挥塔 (Sidebar Control)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔 (Control Tower)")
    
    # 3.1 API 配置区
    with st.expander("🔌 引擎设置 (API)", expanded=True):
        if "DEEPSEEK_API_KEY" in st.secrets:
            api_key = st.secrets["DEEPSEEK_API_KEY"]
            st.success("✅ 神经网络：已连接 (Secret)")
        else:
            api_key = st.text_input("DeepSeek API Key", type="password", placeholder="sk-...")
            if not api_key:
                st.warning("🔴 请输入 API Key 才能使用")
                st.stop()
            else:
                st.success("✅ API Key 已输入")
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    st.divider()
    
    # 3.2 章节导航与进度
    st.markdown("#### 📅 写作进度")
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    # 计算当前章节的 AI 生成字数
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    target_val = st.session_state['daily_target']
    progress_val = min(current_text_len / target_val, 1.0)
    
    st.write(f"当前第 **{st.session_state.current_chapter}** 章 | 字数: **{current_text_len}** / {target_val}")
    st.progress(progress_val)

    # 章节跳转控件
    c_nav1, c_nav2 = st.columns([2, 1])
    with c_nav1:
        target_chap = st.number_input("跳转到章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: 
                st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c_nav2:
        if st.button("⏪ 撤销", help="删除最新的一轮对话"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.toast("时光倒流成功", icon="↩️")
                st.rerun()

    st.divider()

    # 3.3 档案室 (保留导入和文风功能)
    with st.expander("📂 档案室 (导入/文风)", expanded=False):
        t_imp1, t_imp2 = st.tabs(["📥 导入", "🧬 文风"])
        with t_imp1:
            uploaded_draft = st.file_uploader("上传TXT续写", type=["txt"])
            if uploaded_draft and st.button("📥 确认读取"):
                content = uploaded_draft.getvalue().decode("utf-8")
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "user", "content": f"【导入旧稿】\n{content}"}
                )
                st.session_state["chapters"][st.session_state.current_chapter].append(
                    {"role": "assistant", "content": "✅ 旧稿已读取，请下达续写指令。"}
                )
                st.success("导入成功！")
                st.rerun()
        with t_imp2:
            style_file = st.file_uploader("上传大神作品(TXT)", type=["txt"])
            if style_file and st.button("🧠 提取文风"):
                text = style_file.getvalue().decode("utf-8")[:3000] # 只取前3000字分析
                with st.spinner("正在分析文风特征..."):
                    r = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"user", "content": f"请专业分析以下文本的文风（包括用词习惯、句式长短、描写偏好、情感基调）：\n\n{text}"}]
                    )
                    st.session_state["mimic_analysis"] = r.choices[0].message.content
                    st.success("文风基因已提取！")

    # 3.4 设定集 (Codex)
    with st.expander("📕 设定集 (Codex)", expanded=False):
        new_term = st.text_input("设定名称", placeholder="例如：青莲地心火")
        new_desc = st.text_input("设定描述", placeholder="例如：异火榜排名第19...")
        if st.button("➕ 添加设定"):
            if new_term and new_desc:
                st.session_state["codex"][new_term] = new_desc
                st.success(f"已收录：{new_term}")
        
        if st.session_state["codex"]:
            st.markdown("---")
            st.caption("已收录设定：")
            for k, v in st.session_state["codex"].items():
                st.markdown(f"**{k}**: {v}")

    st.divider()

    # ==========================================
    # 🔥 核心增强：大脑控制台 (Brain Console)
    # ==========================================
    st.markdown("### 🧠 大脑控制台 (Brain)")
    
    # 1. 扩充后的类型库 (20种+)
    # 你要求的类型太少，这里我直接给你加满
    full_genres = [
        "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世囤货 | 天灾求生", 
        "无限流 | 诸天副本", "悬疑刑侦 | 规则怪谈", "赛博朋克 | 机械飞升",
        "历史穿越 | 王朝争霸", "克苏鲁 | 诡秘复苏", "西方奇幻 | 剑与魔法",
        "游戏竞技 | 第四天灾", "科幻星际 | 太空歌剧", "武侠仙侠 | 江湖恩怨",
        "女频 | 豪门总裁", "女频 | 宫斗宅斗", "女频 | 大女主爽文",
        "同人 | 动漫影视", "轻小说 | 校园日常", "灵异 | 捉鬼驱邪",
        "自定义类型"
    ]
    
    selected_genre_raw = st.selectbox("📚 小说类型", full_genres)
    
    if "自定义" in selected_genre_raw:
        novel_type = st.text_input("请输入自定义类型", "暗黑修仙")
    else:
        novel_type = selected_genre_raw.split("|")[0].strip()

    # 2. 叙事视角 (你要求的)
    perspective = st.selectbox(
        "👁️ 叙事视角", 
        ["第三人称 (上帝视角)", "第一人称 (我)", "第二人称 (你 - 跑团模式)"],
        index=0
    )

    st.markdown("---")

    # 3. 核心参数 (文风、节奏、创意)
    st.caption("写作参数微调")
    
    writing_style = st.select_slider(
        "🎭 文笔风格", 
        options=["极简白话", "幽默玩梗", "正常通俗", "细腻唯美", "辞藻华丽", "暗黑深沉", "古风晦涩"], 
        value="正常通俗"
    )
    
    rhythm = st.radio(
        "⏱️ 叙事节奏", 
        ["快速推进 (重剧情/少废话)", "平衡", "慢速沉浸 (重环境/心理)"], 
        index=1
    )
    
    creativity = st.slider(
        "🔥 创意温度 (Temperature)", 
        min_value=0.1, max_value=1.5, value=1.2, step=0.1,
        help="数值越高，AI 越容易发散思维（可能神来之笔，也可能胡言乱语）；数值越低，逻辑越严密。"
    )

    word_target = st.number_input("🎯 单次生成字数", 500, 8000, 1500, 100)
    
    # 强力扩写模式开关
    burst_mode = st.toggle("💥 强力注水模式", value=True, help="开启后，强制 AI 进行环境描写和心理描写，防止字数太少。")


# ==========================================
# 4. 主工作区 (Main Workspace)
# ==========================================
tab_write, tab_pipeline, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🚀 策划流水线", "🔮 灵感外挂", "💾 发布中心"])

# --- TAB 1: 沉浸写作 (核心功能区) ---
with tab_write:
    st.subheader(f"📖 第 {st.session_state.current_chapter} 章：正文编辑")
    
    # 1. 动态构建 System Prompt
    # 将侧边栏的所有参数打包进 Prompt
    context_block = ""
    if st.session_state.get("pipe_outline"): 
        context_block += f"\n\n【本章大纲】\n{st.session_state['pipe_outline']}"
    if st.session_state.get("codex"): 
        context_block += f"\n\n【世界观设定字典】\n{str(st.session_state['codex'])}"
    if st.session_state.get("mimic_analysis"): 
        context_block += f"\n\n【模仿文风要求】\n{st.session_state['mimic_analysis']}"
    
    # 构建具体的写作指令
    length_instruction = ""
    if burst_mode:
        length_instruction = (
            "【强力扩写指令】\n"
            "1. 必须大量使用视觉、听觉、嗅觉等感官描写。\n"
            "2. 每一个动作都要配合一段心理描写或微表情描写。\n"
            "3. 严禁流水账，严禁一句话跳过战斗或过程。\n"
        )
    
    system_prompt = (
        f"你是一名顶尖的网文作家。当前写作类型：{novel_type}。\n"
        f"叙事视角：{perspective}。\n"
        f"文风要求：{writing_style}。\n"
        f"节奏控制：{rhythm}。\n"
        f"{context_block}\n\n"
        f"【输出格式要求】\n"
        f"1. 每次输出必须以Markdown格式的章节标题开头，例如：**### 第X章 标题**\n"
        f"2. 单次输出字数目标：{word_target}字左右。\n"
        f"{length_instruction}\n"
        f"3. 不要输出任何客套话（如'好的'），直接开始写正文。"
    )

    # 2. 聊天记录显示容器
    chat_container = st.container(height=500) # 固定高度，滚动显示
    current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
    
    with chat_container:
        if not current_msgs:
            st.info("✨ 空白章节。在下方输入框输入第一段剧情，开始创作吧！")
        for msg in current_msgs:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
            st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    # 3. 功能区：雷达检测 & 一键复制 (你要求的重点)
    st.markdown("---")
    c_tool_1, c_tool_2 = st.columns([1, 1])
    
    # === 功能 A: 违禁词雷达 (带高亮) ===
    with c_tool_1:
        with st.expander("🛡️ 违禁词雷达 (点击扫描)", expanded=False):
            if st.button("🔍 扫描本章全文"):
                # 这是一个基础违禁词库，你可以自行扩充
                risky_words = [
                    "杀人", "死", "血", "尸体", "恐怖", "色情", "肉体", 
                    "政府", "政治", "自杀", "爆炸", "毒品", "违禁", "裸露"
                ]
                # 获取本章所有 AI 生成的内容
                full_text = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                
                # 查找逻辑
                found_risks = list(set([w for w in risky_words if w in full_text]))
                
                if not found_risks:
                    st.success("✅ 扫描完成，未发现高风险词汇。")
                else:
                    st.error(f"⚠️ 发现敏感词：{', '.join(found_risks)}")
                    st.caption("▼ 下方显示高亮位置（红色加粗）：")
                    
                    # ⚡ 正则替换实现高亮
                    # 将敏感词替换为 HTML/Markdown 样式
                    highlighted_text = full_text
                    for word in found_risks:
                        # 使用 Streamlit 支持的颜色语法 :red[text]
                        highlighted_text = highlighted_text.replace(word, f":red[**{word}**]")
                    
                    # 在 Expander 内部显示高亮后的文本
                    st.markdown(highlighted_text)

    # === 功能 B: 一键复制 (修复版) ===
    with c_tool_2:
        # 获取最后一条 AI 回复用于显示
        last_ai_msg = ""
        for m in reversed(current_msgs):
            if m["role"] == "assistant":
                last_ai_msg = m["content"]
                break
        
        with st.expander("📋 一键复制 (最新段落)", expanded=True):
            if last_ai_msg:
                st.caption("点击代码块右上角的 📄 图标即可复制：")
                # 利用 st.code 的原生复制功能，这是最稳定的实现方式
                st.code(last_ai_msg, language=None)
            else:
                st.caption("暂无内容可复制")

    # 4. 输入控制区
    st.markdown("### ✍️ 继续创作")
    c_input, c_btn = st.columns([4, 1])
    
    with c_input:
        manual_instruction = st.text_input(
            "💡 剧情指令 (导演模式)", 
            placeholder="例如：反派突然破门而入，主角拔剑迎敌...",
            help="留空则让 AI 自由续写；填入内容则强制 AI 按照你的剧本写。"
        )
    with c_btn:
        st.write("") # 占位对齐
        st.write("") 
        continue_btn = st.button("🔄 智能续写", use_container_width=True)

    # 封装生成逻辑，避免代码重复
    def run_generation(prompt_text):
        # 1. 记录用户指令
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt_text})
        
        # 2. 显示在界面上
        with chat_container:
            st.chat_message("user", avatar="🧑‍💻").write(prompt_text)
            with st.chat_message("assistant", avatar="🖊️"):
                placeholder = st.empty()
                full_response = ""
                
                # 3. 调用 API (流式)
                stream = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=[{"role":"system","content":system_prompt}] + current_msgs, 
                    stream=True, 
                    temperature=creativity, # 使用侧边栏的温度
                    max_tokens=4000
                )
                
                # 4. 实时渲染
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        placeholder.markdown(full_response + "▌") # 打字机光标
                
                placeholder.markdown(full_response)
        
        # 5. 存入历史
        st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":full_response})
        st.rerun() # 刷新以更新复制区

    # 触发方式 1: 回车输入
    if user_prompt := st.chat_input("输入对话或剧情..."):
        run_generation(user_prompt)

    # 触发方式 2: 点击按钮
    if continue_btn:
        final_prompt = f"接着上文继续写。{manual_instruction}" if manual_instruction else "接着上文继续写，保持情节连贯，注重细节描写。"
        run_generation(final_prompt)


# --- TAB 2: 策划流水线 (Pipeline) ---
with tab_pipeline:
    st.info("🏭 AI 策划师模式：这里只生成设定和大纲，不写正文。")
    planner_sys_prompt = "你是一个专业的网文主编和策划。你的任务是提供创意、设定和大纲。**输出必须结构清晰，逻辑严密**。"

    # 第一步：脑洞风暴
    with st.expander("Step 1: 核心脑洞 (Idea)", expanded=not st.session_state["pipe_idea"]):
        raw_idea = st.text_input("输入一个简单的点子", placeholder="例如：在修仙世界里搞工业革命")
        if st.button("✨ 生成核心梗概"):
            p = f"基于点子“{raw_idea}”，为{novel_type}类型设计一个爆款核心梗。要求：有冲突、有金手指、有爽点。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys_prompt}, {"role":"user","content":p}])
            st.session_state["pipe_idea"] = r.choices[0].message.content
            st.rerun()
            
    if st.session_state["pipe_idea"]:
        st.text_area("✅ 核心梗结果", st.session_state["pipe_idea"], height=150)

    # 第二步：角色卡
    with st.expander("Step 2: 主角人设 (Character)", expanded=bool(st.session_state["pipe_idea"])):
        c1, c2 = st.columns(2)
        if c1.button("👥 生成人设档案"):
            p = f"基于梗概：\n{st.session_state['pipe_idea']}\n\n设计主角和反派的人设档案（姓名、性格、外貌、金手指）。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys_prompt}, {"role":"user","content":p}])
            st.session_state["pipe_char"] = r.choices[0].message.content
            st.rerun()
        
    if st.session_state["pipe_char"]:
        st.text_area("✅ 人设结果", st.session_state["pipe_char"], height=200)

    # 第三步：分章大纲 (已修复标题问题)
    with st.expander("Step 3: 剧情大纲 (Outline)", expanded=bool(st.session_state["pipe_char"])):
        if st.button("📜 生成分章细纲"):
            # 强制要求格式的 Prompt
            outline_prompt = (
                f"核心梗：{st.session_state['pipe_idea']}。\n"
                f"人设：{st.session_state['pipe_char']}。\n"
                "请生成前 3 章的详细细纲。\n"
                "**【重要格式要求】**\n"
                "每一章必须严格按照以下格式输出：\n"
                "**第一章：[这里必须写出具体的章节标题]**\n"
                "1. [剧情点1]\n"
                "2. [剧情点2]\n"
                "...\n\n"
                "**第二章：[这里必须写出具体的章节标题]**\n"
                "..."
            )
            stream = client.chat.completions.create(
                model="deepseek-chat", 
                messages=[{"role":"system","content":planner_sys_prompt}, {"role":"user","content":outline_prompt}], 
                stream=True
            )
            st.session_state["pipe_outline"] = st.write_stream(stream)


# --- TAB 3: 灵感外挂 (Tools) ---
with tab_tools:
    st.write("🔧 写作辅助工具箱")
    c_tools_1, c_tools_2 = st.columns(2)
    
    with c_tools_1:
        st.markdown("#### 🎬 万能场面生成器")
        scene_type = st.selectbox("选择场面类型", ["打斗/战斗", "感情/暧昧", "恐怖/惊悚", "装逼/打脸", "悲剧/煽情"])
        scene_desc = st.text_input("简单描述", placeholder="例如：主角在雨夜拔刀")
        if st.button("生成场面描写"):
            p = f"写一段【{scene_type}】的场面。内容：{scene_desc}。要求：画面感极强，多用修辞，字数300字。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
            st.write_stream(stream)

    with c_tools_2:
        st.markdown("#### 🎲 取名神器")
        name_type = st.radio("取名类型", ["人名", "地名", "功法名", "武器名"], horizontal=True)
        if st.button("随机生成一组名字"):
            p = f"为{novel_type}类型的小说，生成10个好听的{name_type}。不要解释，只列出名字。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.write(r.choices[0].message.content)


# --- TAB 4: 发布中心 (Publish) ---
with tab_publish:
    st.info("💾 准备好了吗？这里可以将你的作品导出为文件。")
    
    # 拼接全书
    full_book_text = ""
    for ch_num, msgs in st.session_state["chapters"].items():
        # 只提取 AI 回复的内容
        ch_txt = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
        if ch_txt:
            full_book_text += f"\n\n{ch_txt}\n"
    
    if not full_book_text:
        st.warning("⚠️ 暂无内容可导出")
    else:
        c_p1, c_p2, c_p3 = st.columns(3)
        
        # 1. 纯净文本下载
        with c_p1:
            st.markdown("#### 📄 纯文本 (TXT)")
            # 清理 Markdown 符号，适合直接发文
            clean_text = full_book_text.replace("**", "").replace("##", "")
            st.download_button(
                label="📥 下载全书.txt",
                data=clean_text,
                file_name=f"Novel_Export_{int(time.time())}.txt",
                mime="text/plain"
            )

        # 2. 分章压缩包
        with c_p2:
            st.markdown("#### 📦 分章打包 (ZIP)")
            if st.button("🎁 生成 ZIP 压缩包"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for ch_num, msgs in st.session_state["chapters"].items():
                        ch_content = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
                        # 简单清理
                        ch_content = ch_content.replace("**", "")
                        zip_file.writestr(f"Chapter_{ch_num}.txt", ch_content)
                
                st.download_button(
                    label="📥 点击下载 ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="chapters_pack.zip",
                    mime="application/zip"
                )

        # 3. 数据备份 (JSON)
        with c_p3:
            st.markdown("#### 💊 完整备份 (JSON)")
            st.caption("包含：正文、设定集、大纲、废稿")
            backup_data = {
                "chapters": st.session_state["chapters"],
                "codex": st.session_state["codex"],
                "scrap_yard": st.session_state["scrap_yard"],
                "pipe_idea": st.session_state["pipe_idea"],
                "pipe_outline": st.session_state["pipe_outline"]
            }
            st.download_button(
                label="📥 导出备份数据",
                data=json.dumps(backup_data, ensure_ascii=False, indent=2),
                file_name="genesis_backup.json",
                mime="application/json"
            )

    st.markdown("---")
    if st.button("🧹 删档重来 (危险操作)"):
        st.session_state.clear()
        st.rerun()