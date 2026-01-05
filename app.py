import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 强力初始化 (恢复原版详细配置)
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    # 包含了你原始代码的所有变量，加上我新增的变量，一个都不少
    defaults = {
        # --- 原版基础数据 ---
        "chapters": {1: []},
        "current_chapter": 1,
        "history_snapshots": [],
        "codex": {},            # 设定集
        "scrap_yard": [],       # 废稿篓
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        "init_done": True,
        
        # --- 原版流水线数据 (现改为创世蓝图) ---
        "pipe_idea": "",
        "pipe_char": "",
        "pipe_world": "",
        "pipe_outline": "",
        
        # --- 新增：备战区 & 导演台数据 ---
        "context_buffer": "",   # 续写的前文缓存
        "mimic_style": "",      # 仿写的文风缓存
        "mimic_analysis": "",   # (保留旧版变量以防万一)
        
        # --- 新增：全局设置默认值 ---
        "global_genre": "东方玄幻",
        "global_tone": "热血 / 王道",
        "global_naming": "东方中文名",
        "global_world_bg": ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (CSS) - (完全恢复你原版的长代码，并追加新样式)
# ==========================================
st.markdown("""
<style>
    /* === 原版样式区 (保留) === */
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 8px; border: none; font-weight: 600; padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
    }
    
    .guide-card {
        background: white; border: 1px solid #e0e0e0; border-radius: 16px; padding: 24px;
        text-align: center; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .guide-icon {font-size: 48px; margin-bottom: 16px; display: block;}
    .guide-title {font-size: 20px; font-weight: 700; color: #343a40; margin-bottom: 8px;}
    .guide-desc {color: #868e96; font-size: 14px; line-height: 1.5;}
    
    .system-box {
        background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%);
        border: 2px solid #339af0; border-radius: 8px; padding: 15px;
        color: #1864ab; font-family: 'Courier New', monospace; font-weight: bold;
    }
    
    /* === 新增样式区 (为了新功能) === */
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    .global-setting-box {
        background-color: #fff0f6; border: 1px solid #fcc2d7; 
        padding: 15px; border-radius: 8px; margin-bottom: 15px;
    }
    
    .director-control-box {
        background-color: #e7f5ff; border-left: 4px solid #339af0;
        padding: 10px 15px; border-radius: 4px; margin-bottom: 10px;
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑 (恢复原版)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>V 3.0 全功能增强版</p>", unsafe_allow_html=True)
            with st.form("login"):
                pwd = st.text_input("🔑 通行密钥", type="password", placeholder="输入 666")
                if st.form_submit_button("🚀 启动引擎", use_container_width=True):
                    if pwd in USERS.values():
                        st.session_state["logged_in"] = True
                        st.rerun()
                    else:
                        st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：指挥塔 (重构：全局设置置顶 + 保留设定集/废稿篓)
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ 指挥塔")
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        st.success("✅ 神经网络：在线")
    else:
        st.error("🔴 请配置 API Key")
        st.stop()
    
    st.divider()

    # --- 1. 全局书籍设置 (NEW: 最醒目) ---
    st.markdown("### 📚 世界观基石 (Global Config)")
    with st.container():
        st.info("在此定义本书的底层逻辑，影响所有 AI 生成内容。")
        
        # 小说类型 (扩展版)
        genre_list = [
            "东方玄幻 | 练气筑基", "都市异能 | 灵气复苏", "末世 | 囤货求生", 
            "无限流 | 诸天万界", "悬疑 | 规则怪谈", "赛博朋克 | 机械飞升",
            "历史 | 穿越争霸", "同人 | 动漫影视", "西幻 | 领主种田",
            "游戏 | 第四天灾", "女频 | 豪门爽文", "女频 | 宫斗宅斗", "自定义"
        ]
        s_genre = st.selectbox("小说类型", genre_list, index=0)
        st.session_state["global_genre"] = s_genre.split("|")[0] if "|" in s_genre else s_genre
        
        # 核心基调 (NEW)
        tone_opts = ["热血 / 王道 / 爽文", "暗黑 / 压抑 / 生存", "轻松 / 搞笑 / 吐槽", "悬疑 / 烧脑 / 反转", "治愈 / 情感 / 细腻"]
        st.session_state["global_tone"] = st.selectbox("核心基调", tone_opts, index=0)
        
        # 世界背景 (NEW)
        st.session_state["global_world_bg"] = st.text_input("世界背景 (简述)", placeholder="如：蒸汽朋克大明，灵气复苏的东京...")
        
        # 起名风格 (NEW)
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名 (萧炎)", "西方译名 (艾伦)", "日式轻小说 (佐藤)", "古风雅韵 (纳兰)"])

    st.divider()

    # --- 2. 仪表盘 & 导航 (保留原版) ---
    curr_chap_data = st.session_state["chapters"].get(st.session_state["current_chapter"], [])
    current_text_len = len("".join([m["content"] for m in curr_chap_data if m["role"]=="assistant"]))
    st.markdown(f"**🔥 今日码字** ({current_text_len} / {st.session_state['daily_target']})")
    st.progress(min(current_text_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target_chap = st.number_input("跳转章节", min_value=1, value=st.session_state.current_chapter, step=1)
        if target_chap != st.session_state.current_chapter:
            if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = []
            st.session_state.current_chapter = target_chap
            st.rerun()
    with c2: 
        if st.button("⏪ 撤销"):
            if len(st.session_state["chapters"][st.session_state.current_chapter]) >= 2:
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.session_state["chapters"][st.session_state.current_chapter].pop()
                st.toast("时光倒流成功", icon="↩️")
                st.rerun()

    st.divider()

    # --- 3. 设定集 (保留原版逻辑 + 放在侧边栏底部) ---
    with st.expander("📕 设定集 (Codex)"):
        st.caption("防止 AI 吃书，在此记录专有名词")
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕ 录入设定"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已录")
        st.markdown("---")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    # --- 4. 废稿篓 (保留原版逻辑) ---
    with st.expander("🗑️ 废稿篓 (Scrap Yard)"):
        scrap = st.text_area("暂存", height=60, placeholder="写废的段落扔这里...")
        if st.button("📥 存入"):
            if scrap: st.session_state["scrap_yard"].append(scrap); st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"片段 {i+1}", s, height=60, key=f"scr_{i}")
                if st.button(f"❌ 删 {i+1}", key=f"del_{i}"):
                    st.session_state["scrap_yard"].pop(i)
                    st.rerun()

    # 注意：档案室已按要求移除侧边栏，移动到写作区

# ==========================================
# 4. 新手引导 (恢复原版长代码)
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #228be6;'>✨ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #868e96;'>功能全开 · 续写神器 · 格式无忧</p><br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">📂</span>
            <div class="guide-title">备战与设定</div>
            <div class="guide-desc"><b>[侧边栏]</b> 配置世界观基调。<br><b>[写作区顶部]</b> 投喂旧稿或样章。</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">✍️</span>
            <div class="guide-title">沉浸与外挂</div>
            <div class="guide-desc"><b>[写作区]</b> 开启分栏模式。<br>左边写书，右边实时获取<b>剧情预测</b>与<b>润色灵感</b>。</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="guide-card">
            <span class="guide-icon">💾</span>
            <div class="guide-title">发布神器</div>
            <div class="guide-desc"><b>[发书控制台]</b>。<br>自动清洗 Markdown 符号，支持<b>一键分章打包</b>，发书不求人。</div>
        </div>
        """, unsafe_allow_html=True)

    c_center = st.columns([1, 2, 1])
    with c_center[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 开始创作 (Feature Complete)", type="primary", use_container_width=True):
            st.session_state["first_visit"] = False
            st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_blueprint, tab_tools, tab_publish = st.tabs(["✍️ 沉浸写作", "🗺️ 创世蓝图 (原流水线)", "🔮 灵感工具箱", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 (集大成者) ---
with tab_write:
    
    # >>> 区域 1：导演级备战区 (原档案室功能移至此处) <<<
    with st.expander("🎬 备战区：素材投喂 (续写/仿写)", expanded=True):
        c_prep1, c_prep2 = st.columns([1, 1])
        
        # 功能 A：续写 (原导入旧稿)
        with c_prep1:
            st.markdown("#### 📄 导入旧稿续写")
            st.caption("上传写了一半的 TXT，AI 自动读取最后 2000 字作为记忆。")
            uploaded_ctx = st.file_uploader("上传续写文件", type=["txt"], key="ctx_up_main")
            if uploaded_ctx:
                raw_text = uploaded_ctx.getvalue().decode("utf-8")
                # 自动截取最后 2000 字
                st.session_state["context_buffer"] = raw_text[-2000:]
                st.success(f"✅ 已装载旧稿！AI 将紧接：...{raw_text[-50:]}")

        # 功能 B：仿写 (原文风克隆)
        with c_prep2:
            st.markdown("#### 🧬 导入大神样章仿写")
            st.caption("上传你喜欢的文章，AI 学习其用词和节奏。")
            uploaded_sty = st.file_uploader("上传样章文件", type=["txt"], key="sty_up_main")
            if uploaded_sty and st.button("🧠 提取文风 DNA"):
                with st.spinner("正在深度解构文风..."):
                    sample_txt = uploaded_sty.getvalue().decode("utf-8")[:3000]
                    # 调用 AI 分析
                    r = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"user", "content":f"请专业分析这段文字的文风（句式长短、形容词密度、叙事视角、心理描写占比），总结为一段简短的写作指南：\n\n{sample_txt}"}]
                    )
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风滤镜已激活！接下来的写作将模仿此风格。")

    # >>> 区域 2：导演控制台 (新增非必选逻辑) <<<
    st.markdown("<div class='director-control-box'>", unsafe_allow_html=True)
    st.markdown("#### 🎚️ 导演控制台 (Director Control)")
    c_dir1, c_dir2, c_dir3, c_dir4 = st.columns(4)
    with c_dir1:
        # 增加默认选项 "AI 自动把控"
        plot_phase = st.selectbox("当前剧情状态", ["✨ AI 自动把控节奏", "🌊 铺垫/日常 (慢)", "🔥 推进/解谜 (中)", "💥 高潮/冲突 (快)", "❤️ 情感/收尾 (柔)"], index=0)
    with c_dir2:
        # 增加默认选项 "均衡/随机"
        desc_focus = st.selectbox("描写侧重", ["🎲 均衡/随机", "👁️ 画面/光影", "🗣️ 对话/交锋", "🧠 心理/内省", "👊 动作/招式"], index=0)
    with c_dir3:
        view_point = st.selectbox("叙事视角", ["第三人称 (上帝)", "第一人称 (我)"])
    with c_dir4:
        # 注水功能
        burst_mode = st.toggle("💥 强力注水模式", value=True, help="开启后 AI 会疯狂扩写细节")
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # >>> 区域 3：分栏模式开关 (解决灵感外挂位置问题) <<<
    use_split_view = st.toggle("📖 开启对照模式 (左侧写作 | 右侧灵感外挂)", value=True)
    
    if use_split_view:
        col_write, col_assist = st.columns([7, 3])
    else:
        col_write = st.container()
        col_assist = st.empty() # 隐藏

    # --- 左侧：核心写作区 ---
    with col_write:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        
        # 消息容器
        msg_container = st.container(height=600)
        current_msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        with msg_container:
            if not current_msgs: 
                st.info(f"✨ 笔锋已至。当前世界观：{st.session_state['global_genre']} | 基调：{st.session_state['global_tone']}")
            
            for msg in current_msgs:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🖊️"
                content = msg["content"]
                # 折叠过长的前文引用
                if len(content) > 1000 and "前文" in content: 
                    content = content[:200] + "...\n(已自动折叠长引文)"
                st.chat_message(msg["role"], avatar=avatar).write(content)

        # 随手精修面板 (保留原版功能)
        with st.expander("🛠️ 快速精修面板 (润色/重写)"):
            t_fix1, t_fix2 = st.tabs(["✍️ 局部润色", "💥 本章重写"])
            with t_fix1:
                c_f1, c_f2 = st.columns(2)
                bad_frag = c_f1.text_area("粘贴片段", height=100, placeholder="粘贴写得不好的句子...")
                fix_req = c_f2.text_area("要求", height=100, placeholder="如：写得更恐怖一点")
                if st.button("✨ 润色片段") and bad_frag:
                    p = f"修改片段：{bad_frag}\n要求：{fix_req}\n风格：{st.session_state['global_tone']}。\n直接输出修改后的内容。"
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], stream=True)
                    st.write_stream(stream)
            with t_fix2:
                re_req = st.text_input("重写要求", placeholder="如：节奏太慢了，直接进入高潮")
                if st.button("💥 推翻重写本章"):
                    # 逻辑：添加一条重写指令
                    st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content": f"【指令】重写本章，要求：{re_req}。"})
                    st.rerun()

        # === 违禁词雷达 & 复制 (保留原版) ===
        c_tool1, c_tool2 = st.columns([1, 1])
        with c_tool1:
            if st.button("🛡️ 扫描违禁词"):
                risky = ["杀人", "死", "血", "恐怖", "色情", "政府", "自杀", "爆炸"] 
                txt = "".join([m["content"] for m in current_msgs if m["role"]=="assistant"])
                found = [w for w in risky if w in txt]
                if found:
                    st.error(f"发现敏感词：{found}")
                else:
                    st.success("✅ 内容安全")
        with c_tool2:
            last_ai_msg = ""
            for m in reversed(current_msgs):
                if m["role"] == "assistant": last_ai_msg = m["content"]; break
            if last_ai_msg:
                st.download_button("📋 复制本条回复", last_ai_msg)

        st.markdown("---")
        
        # 输入区与 System Prompt 动态构建
        user_input = st.chat_input("输入剧情简述 (或留空让 AI 自由发挥)...")
        
        if user_input:
            # 1. 构建 System Prompt
            # 全局基石
            sys_p = (
                f"你是由DeepSeek驱动的网文作家。\n"
                f"【全局设定】类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"世界背景：{st.session_state['global_world_bg']}。起名风格：{st.session_state['global_naming']}。\n"
                f"【基础参数】视角：{view_point}。\n"
            )
            
            # 导演指令 (仅当用户未选择自动时生效)
            if plot_phase != "✨ AI 自动把控节奏":
                sys_p += f"【强制要求】剧情节奏：{plot_phase}。\n"
            if desc_focus != "🎲 均衡/随机":
                sys_p += f"【强制要求】描写侧重：{desc_focus}。\n"
            
            if burst_mode:
                sys_p += "【扩写要求】强力注水模式：必须大量描写环境、光影、气味、微表情，将一句话扩写为一段话。\n"

            # 注入备战区素材
            if st.session_state["mimic_style"]:
                sys_p += f"【文风模仿】请严格模仿以下文风写作：\n{st.session_state['mimic_style']}\n"
            if st.session_state["context_buffer"]:
                sys_p += f"【前文接龙】请紧接以下内容继续写：\n{st.session_state['context_buffer']}\n"
            
            # 注入 Codex (设定集)
            if st.session_state["codex"]:
                codex_str = "; ".join([f"{k}:{v}" for k,v in st.session_state["codex"].items()])
                sys_p += f"【已知设定 (严禁冲突)】{codex_str}\n"

            # 格式铁律
            sys_p += (
                "\n【执行铁律】\n"
                "1. 输出的第一行必须是Markdown二级标题 (## 章节名)。\n"
                "2. 严禁输出'好的'、'明白'等废话，直接输出正文。\n"
            )

            # 2. 发送请求
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":user_input})
            with msg_container:
                st.chat_message("user", avatar="🧑‍💻").write(user_input)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role":"system", "content":sys_p}] + current_msgs,
                        stream=True
                    )
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # --- 右侧：灵感外挂 (集成版) ---
    if use_split_view and col_assist:
        with col_assist:
            st.markdown("### 🧩 灵感外挂")
            st.info("基于上下文的实时辅助工具")

            # 工具 1: 剧情罗盘 (Context Aware)
            with st.expander("🔮 剧情罗盘 (卡文急救)", expanded=True):
                st.caption("AI 读取上文，预测 3 个走向")
                if st.button("🎲 接下来发生什么？"):
                    # 获取最近 1000 字
                    recent_ctx = "".join([m["content"] for m in current_msgs[-3:]])
                    prompt = f"基于以下剧情：\n{recent_ctx[-1000:]}\n\n给出3个有趣的后续发展分支（1.冲突向 2.悬疑向 3.情感向），简短概括。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":prompt}])
                    st.info(r.choices[0].message.content)

            # 工具 2: 起名助手 (Global Config Aware)
            with st.expander("📛 起名助手"):
                st.caption(f"当前风格：{st.session_state['global_naming']}")
                name_type = st.selectbox("类型", ["配角名", "反派名", "宗门/势力", "宝物/功法"])
                if st.button("🎲 生成名字"):
                    p = f"根据风格【{st.session_state['global_naming']}】和小说类型【{st.session_state['global_genre']}】，生成5个好听的{name_type}，并附带简短设定。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)

            # 工具 3: 扩写神器
            with st.expander("💄 润色/扩写笔"):
                raw_s = st.text_input("输入干巴巴的句子", "他拔剑冲了上去")
                if st.button("🪄 扩写"):
                    p = f"扩写句子“{raw_s}”。要求：增加环境渲染、动作细节和心理活动，扩写到 150 字左右。风格：{st.session_state['global_tone']}。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user", "content":p}])
                    st.write(r.choices[0].message.content)
            
            # 工具 4: 查看大纲
            with st.expander("📜 创世大纲 (只读)"):
                st.text_area("大纲内容", st.session_state["pipe_outline"], height=300, disabled=True)

# --- TAB 2: 创世蓝图 (原流水线 - 全面升级为可编辑模式) ---
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图 (Genesis Blueprint)")
    st.info("在此构建世界观。所有生成内容均支持 **手动修改**，改完即存档。")
    
    bp_sys = f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。"

    # Step 1: 核心脑洞
    st.markdown("#### 1️⃣ 核心脑洞 (The Hook)")
    c_bp1, c_bp2 = st.columns([3, 1])
    with c_bp1:
        raw_idea = st.text_input("输入原始点子", value=st.session_state["pipe_idea"], placeholder="如：重生回到了高考前一天...")
    with c_bp2:
        if st.button("✨ AI 完善脑洞"):
            p = f"基于点子“{raw_idea}”，完善成一个有吸引力的核心梗，增加冲突和期待感。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":bp_sys},{"role":"user","content":p}])
            st.session_state["pipe_idea"] = r.choices[0].message.content
            st.rerun()
    # 结果可编辑
    st.session_state["pipe_idea"] = st.text_area("脑洞结果 (可直接修改)", st.session_state["pipe_idea"], height=150)

    st.markdown("---")

    # Step 2: 角色档案
    st.markdown("#### 2️⃣ 角色档案 (Characters)")
    t_char_gen, t_char_edit = st.tabs(["🎲 AI 生成", "✍️ 手动录入"])
    with t_char_gen:
        if st.button("👥 基于脑洞生成主角"):
            p = f"基于脑洞：{st.session_state['pipe_idea']}。生成男女主档案（姓名、性格、金手指、外貌）。"
            stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":bp_sys},{"role":"user","content":p}], stream=True)
            st.session_state["pipe_char"] = st.write_stream(stream)
    with t_char_edit:
        st.caption("手动输入或修改生成结果：")
        st.session_state["pipe_char"] = st.text_area("角色档案 (可直接修改)", st.session_state["pipe_char"], height=250)

    st.markdown("---")

    # Step 3: 剧情细纲
    st.markdown("#### 3️⃣ 剧情细纲 (Outline)")
    if st.button("📜 生成前三章细纲"):
        p = (
            f"脑洞：{st.session_state['pipe_idea']}。\n"
            f"人设：{st.session_state['pipe_char']}。\n"
            f"请生成前三章细纲。要求：每一章都有标题，列出关键事件和爽点。"
        )
        stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":bp_sys},{"role":"user","content":p}], stream=True)
        st.session_state["pipe_outline"] = st.write_stream(stream)
    
    st.session_state["pipe_outline"] = st.text_area("细纲内容 (可直接修改)", st.session_state["pipe_outline"], height=300)


# --- TAB 3: 灵感工具箱 (保留原版 - 以防万一用户想用旧的) ---
with tab_tools:
    st.info("🛠️ 经典工具箱 (旧版功能保留)")
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        st.markdown("### 🎬 万能场面")
        s_type = st.selectbox("类型", ["⚔️ 战斗", "💖 感情", "👻 恐怖", "😎 装逼"])
        s_desc = st.text_input("描述", placeholder="如：壁咚")
        if st.button("生成场面"):
            p = f"写一段{s_type}。内容：{s_desc}。300字。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
            st.text_area("结果", r.choices[0].message.content, height=200)
    with c_t2:
        st.markdown("### 📟 系统生成")
        sys_i = st.text_input("提示语", placeholder="获得神器")
        if st.button("生成"):
            st.markdown(f"""<div class="system-box">【系统】{sys_i}</div>""", unsafe_allow_html=True)


# --- TAB 4: 发书控制台 (功能增强版) ---
with tab_publish:
    st.markdown("### 🚀 发书控制台")
    st.info("一键清洗 Markdown 符号，自动排版，支持分章打包。")
    
    # 1. 聚合全书
    full_text_raw = ""
    for ch, msgs in st.session_state["chapters"].items():
        # 只提取 assistant 的回答
        ch_txt = "".join([m["content"] for m in msgs if m["role"] == "assistant"])
        full_text_raw += f"\n\n### 第 {ch} 章 ###\n\n{ch_txt}"
        
    # 2. 清洗算法
    def clean_novel_format(text):
        # 去除 markdown 粗体
        text = text.replace("**", "")
        # 去除 标题符号 #
        text = re.sub(r'#+\s*', '', text)
        # 去除多余空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        # 增加段首缩进 (全角空格 x2)
        formatted = [f"　　{line}" for line in lines]
        return "\n\n".join(formatted)

    clean_content = clean_novel_format(full_text_raw)
    
    # 3. 界面展示
    c_pub1, c_pub2 = st.columns([2, 1])
    with c_pub1:
        st.markdown("#### 👁️ 纯净预览 (前1000字)")
        st.text_area("预览", clean_content[:1000] + "...", height=400, disabled=True)
        
    with c_pub2:
        st.markdown("#### 💾 导出操作")
        
        # A. 下载 TXT
        st.download_button(
            label="📥 下载全书 (纯净版 TXT)",
            data=clean_content,
            file_name=f"novel_{st.session_state['global_genre']}.txt",
            mime="text/plain",
            type="primary"
        )
        
        st.markdown("---")
        
        # B. 打包 ZIP
        if st.button("🎁 分章打包 (ZIP)"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ch, msgs in st.session_state["chapters"].items():
                    raw_c = "".join([m["content"] for m in msgs if m["role"]=="assistant"])
                    clean_c = clean_novel_format(raw_c)
                    zip_file.writestr(f"Chapter_{ch}.txt", clean_c)
            st.download_button("点击保存 ZIP", zip_buffer.getvalue(), "chapters.zip", mime="application/zip")
            
        st.markdown("---")
        
        # C. 敏感词预检
        if st.button("🛡️ 敏感词预检"):
            risky_words = ["色情", "政治", "杀人", "自杀", "血腥", "恐怖"]
            found = [w for w in risky_words if w in clean_content]
            if found:
                st.error(f"⚠️ 检测到疑似敏感词：{', '.join(found)}")
            else:
                st.success("✅ 看起来很安全")
                
        # D. 全数据备份
        backup_data = {
            "config": {
                "genre": st.session_state["global_genre"],
                "tone": st.session_state["global_tone"],
                "naming": st.session_state["global_naming"],
                "world": st.session_state["global_world_bg"]
            },
            "chapters": st.session_state["chapters"],
            "codex": st.session_state["codex"],
            "blueprint": {
                "idea": st.session_state["pipe_idea"],
                "char": st.session_state["pipe_char"],
                "outline": st.session_state["pipe_outline"]
            },
            "scrap": st.session_state["scrap_yard"]
        }
        st.download_button("💊 完整数据备份 (JSON)", json.dumps(backup_data, ensure_ascii=False), "backup_full.json")