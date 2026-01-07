import streamlit as st
from openai import OpenAI
import json
import random
import re
import io
import zipfile
import time

# ==========================================
# 0. 全局配置 & 强力初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        "chapters": {1: ""},      
        "current_chapter": 1,
        "codex": {},              
        "scrap_yard": [],         
        "work_draft": "",         # 左栏：草稿
        "work_result": "",        # 右栏：成品
        "style_dna": "",          
        "final_genre": "东方玄幻", 
        "logged_in": False,
        "first_visit": True,
        "daily_target": 3000
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa; color: #1a1a1a;}
    .stButton>button {font-weight: 600; border-radius: 8px;}
    textarea {font-family: 'SimSun', 'Courier New', serif !important; font-size: 16px !important; line-height: 1.7 !important;}
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
            st.markdown("<br><br><h1 style='text-align: center;'>⚡ 创世笔 Ultimate</h1>", unsafe_allow_html=True)
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
# 3. 侧边栏：指挥塔
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
    
    # --- 🔥 1. 导入旧稿 (你要找回的功能！) ---
    st.markdown("#### 📥 导入旧稿 (续写/润色)")
    uploaded_draft = st.file_uploader("上传 .txt 到左侧草稿箱", type=["txt"], key="draft_up")
    if uploaded_draft:
        # 读取内容
        content = uploaded_draft.getvalue().decode("utf-8")
        # 按钮确认，防止误触
        if st.button("确认覆盖左侧草稿"):
            st.session_state["work_draft"] = content
            st.success("已导入！请在右侧点击‘润色’。")
            time.sleep(1)
            st.rerun()
            
    st.divider()

    # --- 2. 核心参数区 ---
    st.markdown("#### 📚 设定控制台")
    genre_list = [
        "东方玄幻 | 异世大陆", "东方玄幻 | 高武世界", 
        "都市生活 | 都市异能", "都市生活 | 豪门世家",
        "历史军事 | 架空历史", "科幻末世 | 赛博朋克",
        "悬疑灵异 | 恐怖惊悚", "女频 | 宫斗宅斗",
        "自定义 (手动输入)"
    ]
    sel_genre = st.selectbox("选择流派", genre_list, index=0)
    if "自定义" in sel_genre:
        st.session_state["final_genre"] = st.text_input("✍️ 输入流派", placeholder="例如：克苏鲁修仙")
    else:
        st.session_state["final_genre"] = sel_genre

    # 禁词黑名单
    with st.expander("🚫 禁词黑名单 (反AI味)", expanded=False):
        banned_words_str = st.text_area(
            "禁止出现的词", 
            value="像小刀子,像灌了铅,——,紧接着,旋即,嘴角勾起", 
            height=70,
            help="AI 生成时如果包含这些词，会被判定为违规。"
        )

    # --- 3. 喂书系统 ---
    with st.expander("🧬 基因工程 (提取文风)", expanded=False):
        uploaded_style = st.file_uploader("上传大神作品", type=["txt"], key="style_up")
        if uploaded_style:
            raw_style = uploaded_style.getvalue().decode("utf-8")[:3000]
            if st.button("🧠 提取文风"):
                with st.spinner("正在解构..."):
                    p = f"分析文风。重点：1.开篇节奏。2.用词习惯。3.描写手法。\n样本：{raw_style}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["style_dna"] = r.choices[0].message.content
                    st.success("文风已激活！")

    # --- 4. 章节管理 ---
    with st.expander("📑 章节管理", expanded=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            target_chap = st.number_input("章号", min_value=1, value=st.session_state.current_chapter, step=1)
            if target_chap != st.session_state.current_chapter:
                if target_chap not in st.session_state.chapters: st.session_state.chapters[target_chap] = ""
                st.session_state.current_chapter = target_chap
                st.rerun()
        with c2: st.caption(f"第 {st.session_state.current_chapter} 章")
        curr_txt = st.session_state["chapters"].get(st.session_state.current_chapter, "")
        st.progress(min(len(curr_txt) / st.session_state['daily_target'], 1.0))
        st.caption(f"{len(curr_txt)}字")

    st.divider()
    
    # 物理清洗按钮 (Feature A)
    if st.button("🧹 暴力清洗禁词 (左侧)", help="不通过AI，直接删掉破折号和违禁词"):
        clean_draft = st.session_state["work_draft"]
        clean_draft = clean_draft.replace("——", "。").replace("像小刀子", "").replace("嘴角勾起", "")
        st.session_state["work_draft"] = clean_draft
        st.toast("已暴力清洗！", icon="🧹")
        st.rerun()

# ==========================================
# 4. 核心逻辑
# ==========================================
def run_director(mode, content, user_req, word_limit, banned_words):
    genre = st.session_state.get("final_genre", "东方玄幻")
    style_dna = st.session_state.get("style_dna", "标准白金文风")
    
    sys_p = (
        f"你是一个起点白金作家。当前创作类型：【{genre}】。\n"
        "【绝对禁令】\n"
        f"1. **黑名单词汇**：{banned_words}。\n"
        "2. **严禁 AI 标点**：禁止频繁使用破折号 '——'。\n"
        "3. **核心原则**：读者只想知道'为什么'（冲突），不想知道'怎么做'（无效动作）。\n"
        "4. **黄金三章**：开局必须有危机。\n"
        f"【文风参考】\n{style_dna}"
    )

    if mode == "polish":
        prompt = (
            f"请润色以下片段。去除水词，严格避开黑名单词汇，加强【{genre}】特有的氛围。\n"
            f"目标字数：{word_limit}字左右。\n"
            f"额外要求：{user_req}\n"
            f"【原稿】：\n{content}"
        )
    elif mode == "logic":
        prompt = (
            f"不要写正文！作为主编，分析逻辑漏洞。并对'节奏'进行评分（0-100）。\n"
            f"给出3个后续高潮走向建议。\n"
            f"【原稿】：\n{content}"
        )
    elif mode == "expand":
        prompt = (
            f"接着以下内容续写。保持节奏紧凑，符合【{genre}】风格。\n"
            f"目标字数：{word_limit}字左右。\n"
            f"剧情指向：{user_req}\n"
            f"【前文】：\n{content}"
        )

    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role":"system","content":sys_p}, {"role":"user","content":prompt}],
            stream=True, temperature=1.3
        )
        return stream
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# ==========================================
# 5. 主工作区
# ==========================================
if st.session_state["first_visit"]:
    st.info(f"👋 欢迎！已载入 V2.2 核心版。请在侧边栏上传旧稿，或在左侧直接写作。")
    if st.button("开始创作"):
        st.session_state["first_visit"] = False
        st.rerun()

tab_main, tab_publish = st.tabs(["✍️ 沉浸精修台", "💾 发书控制台"])

with tab_main:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章 · {st.session_state['final_genre']}")
    c_left, c_mid, c_right = st.columns([4, 1, 4])
    
    # 左侧：原稿区
    with c_left:
        st.markdown("#### 📝 原稿 / 导入区")
        draft_in = st.text_area("Draft", value=st.session_state["work_draft"], height=600, label_visibility="collapsed", placeholder="在此输入或从侧边栏导入...")
        st.session_state["work_draft"] = draft_in

    # 中间：控制台
    with c_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        target_w = st.number_input("字数", 100, 5000, 1500, step=100, label_visibility="collapsed")
        user_req = st.text_input("要求", placeholder="例: 加强打斗画面", label_visibility="collapsed")
        st.markdown("---")
        
        if st.button("✨\n润\n色", use_container_width=True):
            if not draft_in: st.toast("左边没字！", icon="😫")
            else:
                with c_right:
                    st.session_state["work_result"] = ""
                    st.markdown("#### 💎 大神精修版")
                    placeholder = st.empty()
                    full_text = ""
                    stream = run_director("polish", draft_in, user_req, target_w, banned_words_str)
                    if stream:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + " ▌")
                        placeholder.markdown(full_text)
                        st.session_state["work_result"] = full_text

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🩺\n诊\n断", use_container_width=True, help="分析节奏和逻辑"):
             if not draft_in: st.toast("没内容", icon="🤔")
             else:
                with c_right:
                    st.markdown("#### 🩺 剧情诊断书")
                    stream = run_director("logic", draft_in, "", 500, banned_words_str)
                    st.write_stream(stream)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀\n续\n写", use_container_width=True):
             if not draft_in: st.toast("没开头", icon="😶")
             else:
                with c_right:
                    st.markdown("#### 🚀 续写结果")
                    stream = run_director("expand", draft_in, user_req, target_w, banned_words_str)
                    st.write_stream(stream)

    # 右侧：成品区
    with c_right:
        if not st.session_state["work_result"]:
            st.markdown("#### 💎 大神精修版")
            st.info("AI 将在此生成。")
        else:
            st.markdown("#### 💎 大神精修版")
            st.text_area("Result", value=st.session_state["work_result"], height=550, label_visibility="collapsed")
            if st.button("💾 采纳并追加到本章", use_container_width=True, type="primary"):
                if st.session_state["current_chapter"] not in st.session_state["chapters"]:
                    st.session_state["chapters"][st.session_state["current_chapter"]] = ""
                st.session_state["chapters"][st.session_state["current_chapter"]] += "\n\n" + st.session_state["work_result"]
                st.session_state["work_result"] = "" 
                st.session_state["work_draft"] = ""
                st.success("已写入！")
                time.sleep(1)
                st.rerun()

    st.divider()
    with st.expander(f"📜 全文预览 (第 {st.session_state.current_chapter} 章)", expanded=True):
        current_full_text = st.session_state["chapters"].get(st.session_state.current_chapter, "")
        new_full_text = st.text_area("Chapter Edit", value=current_full_text, height=300, label_visibility="collapsed")
        if new_full_text != current_full_text:
            st.session_state["chapters"][st.session_state.current_chapter] = new_full_text

with tab_publish:
    st.info("发布中心")
    full_book_text = ""
    for ch_num in sorted(st.session_state["chapters"].keys()):
        full_book_text += f"\n\n### 第 {ch_num} 章 ###\n\n{st.session_state['chapters'][ch_num]}"
    
    clean_text = full_book_text.replace("**", "").replace("##", "")
    st.download_button("📥 下载全书", clean_text, "novel_full.txt")
    
    if st.button("📦 打包 ZIP"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for ch_num, content in st.session_state["chapters"].items():
                zip_file.writestr(f"Chapter_{ch_num}.txt", content.replace("**", ""))
        st.download_button("📥 下载 ZIP", zip_buffer.getvalue(), "novel.zip", mime="application/zip")