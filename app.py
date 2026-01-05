import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 Ultimate", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        # --- 基础数据 ---
        "chapters": {1: []},
        "current_chapter": 1,
        "codex": {},
        "scrap_yard": [],
        "logged_in": False,
        "daily_target": 3000,
        "first_visit": True,
        
        # --- 创世蓝图数据 (独立存储输入和输出，防止冲突) ---
        "bp_raw_idea": "",      # 用户的原始输入
        "bp_res_idea": "",      # AI 生成的梗
        "bp_raw_char": "",      # 用户的原始人设输入
        "bp_res_char": "",      # AI 生成的人设
        "bp_res_outline": "",   # AI 生成的大纲
        
        # --- 备战区数据 ---
        "context_buffer": "",
        "mimic_style": "",
        
        # --- 全局设置 ---
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
# 1. 样式 (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    section[data-testid="stSidebar"] {background-color: #ffffff; border-right: 1px solid #e0e0e0;}
    
    .stButton>button {
        background-color: #228be6; color: white !important; 
        border-radius: 6px; border: none; font-weight: 600; 
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1c7ed6; transform: translateY(-1px);
    }
    
    .chapter-header {
        font-family: 'Georgia', serif; font-size: 28px; font-weight: bold; color: #343a40;
        border-bottom: 3px solid #e9ecef; padding-bottom: 15px; margin-bottom: 25px;
    }
    
    /* 强调输入框的可编辑性 */
    .stTextArea textarea {
        border: 1px solid #ced4da; background-color: #fff;
    }
    .stTextArea textarea:focus {
        border-color: #228be6; box-shadow: 0 0 0 2px rgba(34,139,230,0.2);
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 登录逻辑
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ GENESIS V3.1</h1>", unsafe_allow_html=True)
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
# 3. 侧边栏：全局指挥塔
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

    # --- 1. 全局书籍设置 (修复自定义问题) ---
    st.markdown("### 📚 世界观基石")
    with st.container():
        # 类型
        genre_list = ["东方玄幻", "都市异能", "末世求生", "无限流", "悬疑惊悚", "赛博朋克", "历史穿越", "西幻", "女频爽文", "自定义"]
        s_genre = st.selectbox("小说类型", genre_list, index=0)
        if s_genre == "自定义":
            st.session_state["global_genre"] = st.text_input("输入自定义类型", "克苏鲁修仙")
        else:
            st.session_state["global_genre"] = s_genre
        
        # 基调 (修复自定义问题)
        tone_opts = ["热血 / 王道", "暗黑 / 压抑", "轻松 / 搞笑", "悬疑 / 烧脑", "治愈 / 情感", "【✏️ 自定义...】"]
        s_tone = st.selectbox("核心基调", tone_opts, index=0)
        if s_tone == "【✏️ 自定义...】":
            st.session_state["global_tone"] = st.text_input("输入自定义基调", placeholder="如：慢热、群像、史诗感")
        else:
            st.session_state["global_tone"] = s_tone
        
        # 命名与背景
        st.session_state["global_world_bg"] = st.text_input("世界背景", placeholder="如：蒸汽朋克大明")
        st.session_state["global_naming"] = st.selectbox("起名风格", ["东方中文名", "西方译名", "日式轻小说", "古风雅韵"])

    st.divider()

    # --- 2. 导航与工具 (保留) ---
    curr_len = len("".join([m["content"] for m in st.session_state["chapters"][st.session_state["current_chapter"]] if m["role"]=="assistant"]))
    st.caption(f"本章字数: {curr_len} / {st.session_state['daily_target']}")
    st.progress(min(curr_len / st.session_state['daily_target'], 1.0))
    
    c1, c2 = st.columns([2, 1])
    with c1:
        target = st.number_input("跳转章节", 1, value=st.session_state.current_chapter)
        if target != st.session_state.current_chapter:
            if target not in st.session_state.chapters: st.session_state.chapters[target] = []
            st.session_state.current_chapter = target
            st.rerun()
    with c2: 
        if st.button("⏪"): # 撤销
            ch = st.session_state["chapters"][st.session_state.current_chapter]
            if len(ch) >= 2: ch.pop(); ch.pop(); st.rerun()

    with st.expander("📕 设定集"):
        k = st.text_input("词条", placeholder="青莲火")
        v = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕"): st.session_state["codex"][k] = v; st.success("已存")
        for key, val in st.session_state["codex"].items(): st.markdown(f"**{key}**: {val}")

    with st.expander("🗑️ 废稿篓"):
        s_txt = st.text_area("暂存", height=60)
        if st.button("📥"): st.session_state["scrap_yard"].append(s_txt); st.success("已存")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                st.text_area(f"#{i+1}", s, height=60, key=f"s_{i}")
                if st.button(f"删 #{i+1}", key=f"d_{i}"):
                    st.session_state["scrap_yard"].pop(i); st.rerun()

# ==========================================
# 4. 新手引导
# ==========================================
if st.session_state["logged_in"] and st.session_state["first_visit"]:
    st.markdown("<br><br><h1 style='text-align: center; color: #228be6;'>✨ GENESIS V3.1</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>交互修复版 · 自由度全开</p><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.info("🛠️ 全局设置现在支持自定义基调了"); c2.info("🗺️ 创世蓝图现在可以反复编辑重写了"); c3.info("🤐 修复了 AI 细纲废话太多的问题")
    if st.button("🚀 开始创作", type="primary", use_container_width=True):
        st.session_state["first_visit"] = False
        st.rerun()
    st.stop()

# ==========================================
# 5. 主工作区
# ==========================================
tab_write, tab_blueprint, tab_publish = st.tabs(["✍️ 沉浸写作", "🗺️ 创世蓝图", "💾 发书控制台"])

# --- TAB 1: 沉浸写作 ---
with tab_write:
    # 备战区
    with st.expander("🎬 备战区 (续写/仿写)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up_ctx = st.file_uploader("导入续写", type=["txt"])
            if up_ctx: st.session_state["context_buffer"] = up_ctx.getvalue().decode("utf-8")[-2000:]; st.success("✅ 已装载")
        with c2:
            up_sty = st.file_uploader("导入仿写", type=["txt"])
            if up_sty and st.button("提取文风"):
                with st.spinner("分析中..."):
                    p = f"分析文风：{up_sty.getvalue().decode('utf-8')[:2000]}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["mimic_style"] = r.choices[0].message.content
                    st.success("✅ 文风已提取")

    # 导演台 (默认自动)
    c_d1, c_d2, c_d3, c_d4 = st.columns(4)
    with c_d1: phase = st.selectbox("剧情状态", ["✨ AI 自动把控", "🌊 铺垫", "🔥 推进", "💥 高潮", "❤️ 收尾"])
    with c_d2: focus = st.selectbox("描写侧重", ["🎲 均衡", "👁️ 画面", "🗣️ 对话", "🧠 心理", "👊 动作"])
    with c_d3: view = st.selectbox("视角", ["第三人称", "第一人称"])
    with c_d4: burst = st.toggle("💥 注水模式", False)
    
    st.divider()

    # 写作区 + 灵感外挂
    use_split = st.toggle("📖 对照模式", True)
    if use_split: col_w, col_a = st.columns([7, 3])
    else: col_w = st.container(); col_a = st.empty()

    with col_w:
        st.markdown(f"<div class='chapter-header'>第 {st.session_state.current_chapter} 章</div>", unsafe_allow_html=True)
        msgs = st.session_state["chapters"][st.session_state.current_chapter]
        
        # 聊天框
        box = st.container(height=500)
        with box:
            for m in msgs:
                st.chat_message(m["role"], avatar="🧑‍💻" if m["role"]=="user" else "🖊️").write(m["content"])
        
        # 输入与 Prompt 构建
        if prompt := st.chat_input("输入剧情..."):
            # System Prompt 构建
            sys = (
                f"你是由DeepSeek驱动的作家。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
                f"背景：{st.session_state['global_world_bg']}。起名：{st.session_state['global_naming']}。\n"
                f"视角：{view}。\n"
            )
            if phase != "✨ AI 自动把控": sys += f"【强制要求】剧情状态：{phase}。\n"
            if focus != "🎲 均衡": sys += f"【强制要求】描写侧重：{focus}。\n"
            if burst: sys += "【强制要求】强力注水模式，大量描写细节，扩写篇幅。\n"
            if st.session_state["mimic_style"]: sys += f"【文风模仿】{st.session_state['mimic_style']}\n"
            if st.session_state["context_buffer"]: sys += f"【前文接龙】{st.session_state['context_buffer']}\n"
            codex_str = "; ".join([f"{k}:{v}" for k,v in st.session_state["codex"].items()])
            if codex_str: sys += f"【设定集】{codex_str}\n"
            
            # 死命令：禁止废话
            sys += "\n【铁律】1. 输出第一行必须是Markdown二级标题 (## 章节名)。2. 严禁输出'好的'等客套话，直接写正文。"

            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"user", "content":prompt})
            with box:
                st.chat_message("user", avatar="🧑‍💻").write(prompt)
                with st.chat_message("assistant", avatar="🖊️"):
                    stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":sys}]+msgs, stream=True)
                    response = st.write_stream(stream)
            st.session_state["chapters"][st.session_state.current_chapter].append({"role":"assistant", "content":response})

    # 右侧辅助
    if use_split and col_a:
        with col_a:
            st.info("🧩 灵感外挂")
            with st.expander("🔮 剧情预测", True):
                if st.button("🎲 接下来写啥？"):
                    recent = "".join([m["content"] for m in msgs[-3:]])
                    p = f"基于剧情：{recent[-800:]}，给出3个后续分支。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.info(r.choices[0].message.content)
            with st.expander("💄 扩写/润色"):
                txt = st.text_input("输入短句")
                if st.button("🪄 润色") and txt:
                    p = f"润色：{txt}。要求：{st.session_state['global_tone']}风格。"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.write(r.choices[0].message.content)

# --- TAB 2: 创世蓝图 (重构版：修复交互死循环) ---
with tab_blueprint:
    st.markdown("### 🗺️ 创世蓝图 (Ideation)")
    st.info("✨ 逻辑已修复：输入框和结果框分离，支持反复修改、反复生成。")
    
    # 统一 Prompt，强制禁止废话
    planner_sys = (
        f"你是一个网文策划。类型：{st.session_state['global_genre']}。基调：{st.session_state['global_tone']}。\n"
        "【严禁废话】不要输出'好的'、'以下是...'、'您觉得如何'等客套话。\n"
        "【严禁提问】不要在结尾询问用户是否满意。\n"
        "直接输出内容本身。"
    )

    # Step 1: 核心脑洞
    st.markdown("#### 1️⃣ 核心脑洞 (The Hook)")
    # 输入区 (绑定独立的 state bp_raw_idea)
    raw_idea_input = st.text_area("✍️ 输入你的原始点子", value=st.session_state.get("bp_raw_idea", ""), height=100, key="input_idea")
    
    c_b1, c_b2 = st.columns([1, 4])
    if c_b1.button("✨ 生成/重写脑洞"):
        st.session_state["bp_raw_idea"] = raw_idea_input # 保存输入
        with st.spinner("构思中..."):
            p = f"基于点子“{raw_idea_input}”，完善成一个有吸引力的核心梗。字数200字内。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
            st.session_state["bp_res_idea"] = r.choices[0].message.content
            st.success("生成完毕！↓")
            
    # 结果区 (绑定独立的 state bp_res_idea)
    if st.session_state["bp_res_idea"]:
        st.session_state["bp_res_idea"] = st.text_area("✅ AI 构思结果 (可修改)", st.session_state["bp_res_idea"], height=150)

    st.markdown("---")

    # Step 2: 角色档案
    st.markdown("#### 2️⃣ 角色档案")
    if st.button("👥 生成主角人设"):
        with st.spinner("捏人中..."):
            p = f"基于脑洞：{st.session_state['bp_res_idea']}。生成男女主档案。"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
            st.session_state["bp_res_char"] = r.choices[0].message.content
    
    if st.session_state["bp_res_char"]:
        st.session_state["bp_res_char"] = st.text_area("✅ 人设结果 (可修改)", st.session_state["bp_res_char"], height=200)

    st.markdown("---")

    # Step 3: 剧情细纲
    st.markdown("#### 3️⃣ 剧情细纲")
    if st.button("📜 生成前三章细纲"):
        with st.spinner("推演剧情..."):
            p = (
                f"脑洞：{st.session_state['bp_res_idea']}。\n"
                f"人设：{st.session_state['bp_res_char']}。\n"
                f"请生成前三章细纲。每章都要有标题。严禁输出任何结束语！"
            )
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":planner_sys},{"role":"user","content":p}])
            # 简单的后处理：去除可能的结尾问句
            clean_res = r.choices[0].message.content.replace("需要我为您继续构思吗？", "").replace("您觉得如何？", "")
            st.session_state["bp_res_outline"] = clean_res
    
    if st.session_state["bp_res_outline"]:
        st.session_state["bp_res_outline"] = st.text_area("✅ 细纲结果 (可修改)", st.session_state["bp_res_outline"], height=300)

# --- TAB 3: 发书控制台 ---
with tab_publish:
    st.markdown("### 🚀 发书控制台")
    # 聚合
    full_text = ""
    for ch, msgs in st.session_state["chapters"].items():
        txt = "".join([m["content"] for m in msgs if m["role"] == "assistant"])
        full_text += f"\n\n### 第 {ch} 章 ###\n\n{txt}"
    
    # 清洗
    def clean(t):
        t = t.replace("**", "").replace("##", "")
        t = re.sub(r'#+\s*', '', t)
        lines = [f"　　{l.strip()}" for l in t.split('\n') if l.strip()]
        return "\n\n".join(lines)
    
    cl_txt = clean(full_text)
    st.text_area("预览", cl_txt[:500]+"...", height=200, disabled=True)
    st.download_button("📥 下载全书 (TXT)", cl_txt, "novel.txt")
    
    # 打包
    if st.button("🎁 分章 ZIP"):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "a", zipfile.ZIP_DEFLATED, False) as z:
            for ch, msgs in st.session_state["chapters"].items():
                z.writestr(f"Chapter_{ch}.txt", clean("".join([m["content"] for m in msgs if m["role"]=="assistant"])))
        st.download_button("下载 ZIP", b.getvalue(), "chapters.zip", mime="application/zip")
    
    # 备份
    bk = {"conf": {"genre": st.session_state["global_genre"], "tone": st.session_state["global_tone"]}, "ch": st.session_state["chapters"], "bp": [st.session_state["bp_res_idea"], st.session_state["bp_res_char"], st.session_state["bp_res_outline"]]}
    st.download_button("💊 备份 JSON", json.dumps(bk, ensure_ascii=False), "backup.json")