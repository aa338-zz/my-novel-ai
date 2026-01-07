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
        # --- V1 基础数据 ---
        "chapters": {1: ""},      # 章节正文 (Key=章号, Value=内容)
        "current_chapter": 1,
        "codex": {},              # 设定集
        "scrap_yard": [],         # 废稿篓
        
        # --- V2 核心工作区 ---
        "work_draft": "",         # 左栏：当前草稿/大纲
        "work_result": "",        # 右栏：AI 精修后的结果
        "style_dna": "",          # 提取的大神文风
        "final_genre": "东方玄幻", # 最终确定的流派
        
        # --- 系统状态 ---
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
    
    /* 按钮样式优化 */
    .stButton>button {
        font-weight: 600; border-radius: 8px; transition: all 0.2s;
    }
    .big-btn {
        border: 2px solid #228be6; color: #228be6; 
        padding: 10px; text-align: center; border-radius: 8px; cursor: pointer;
        font-weight: bold; margin-bottom: 10px;
    }
    .big-btn:hover {background-color: #e7f5ff;}

    /* 文本域优化 - 仿作家软件 */
    textarea {
        font-family: 'SimSun', 'Courier New', serif !important; 
        font-size: 16px !important;
        line-height: 1.7 !important;
    }
    
    /* 提示框 */
    .info-box {
        background: #e7f5ff; border-left: 5px solid #228be6; padding: 15px; border-radius: 4px; font-size: 14px;
    }
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
# 3. 侧边栏：指挥塔 (全流派升级版)
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

    # --- 1. 核心参数区 (流派 & 禁词) ---
    st.markdown("#### 📚 设定控制台")
    
    # 全流派列表
    genre_list = [
        "东方玄幻 | 异世大陆", "东方玄幻 | 高武世界", "东方玄幻 | 王朝争霸",
        "西方奇幻 | 剑与魔法", "西方奇幻 | 领主种田", "西方奇幻 | 黑暗幻想",
        "仙侠修真 | 古典仙侠", "仙侠修真 | 现代修真", "仙侠修真 | 洪荒封神",
        "都市生活 | 都市异能", "都市生活 | 娱乐明星", "都市生活 | 商战职场", "都市生活 | 豪门世家",
        "历史军事 | 架空历史", "历史军事 | 穿越皇朝", "历史军事 | 谍战特工",
        "游戏竞技 | 虚拟网游", "游戏竞技 | 第四天灾", "游戏竞技 | 电子竞技",
        "科幻末世 | 星际文明", "科幻末世 | 赛博朋克", "科幻末世 | 进化变异",
        "悬疑灵异 | 恐怖惊悚", "悬疑灵异 | 侦探推理", "悬疑灵异 | 盗墓探险",
        "轻小说 | 衍生同人", "轻小说 | 原创轻小", "轻小说 | 搞笑吐槽",
        "女频 | 古代言情", "女频 | 现代言情", "女频 | 穿越重生", "女频 | 宫斗宅斗",
        "自定义 (手动输入)"
    ]
    
    sel_genre = st.selectbox("选择流派", genre_list, index=0)
    
    # 自定义处理逻辑
    if "自定义" in sel_genre:
        st.session_state["final_genre"] = st.text_input("✍️ 输入你的流派", placeholder="例如：蒸汽朋克克苏鲁")
    else:
        st.session_state["final_genre"] = sel_genre

    # 禁词黑名单
    st.markdown("#### 🚫 禁词黑名单 (反AI味)")
    banned_words_str = st.text_area(
        "禁止AI使用的词 (逗号分隔)", 
        value="像小刀子,像灌了铅,——,紧接着,旋即,嘴角勾起,淡淡的", 
        height=70,
        help="AI 生成时如果包含这些词，会被判定为违规。"
    )

    st.divider()

    # --- 2. 喂书系统 (V2新增) ---
    with st.expander("🧬 基因工程 (喂书/文风)", expanded=False):
        st.caption("上传大神作品(.txt)提取文风。")
        uploaded_style = st.file_uploader("上传参考书", type=["txt"], key="style_up")
        if uploaded_style:
            raw_style = uploaded_style.getvalue().decode("utf-8")[:3000]
            if st.button("🧠 提取文风基因"):
                with st.spinner("正在解构大神节奏..."):
                    p = f"分析这段小说的文风。重点分析：1. 开篇节奏（是否黄金三章）。2. 用词习惯（是否精炼）。3. 描写手法。只输出核心特征。\n样本：{raw_style}"
                    r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                    st.session_state["style_dna"] = r.choices[0].message.content
                    st.success("文风已激活！")
        
        if st.session_state["style_dna"]:
            st.info("🧬 当前已挂载大神文风")

    # --- 3. 章节管理 (V1保留) ---
    with st.expander("📑 章节管理", expanded=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            target_chap = st.number_input("章号", min_value=1, value=st.session_state.current_chapter, step=1)
            if target_chap != st.session_state.current_chapter:
                if target_chap not in st.session_state.chapters: 
                    st.session_state.chapters[target_chap] = ""
                st.session_state.current_chapter = target_chap
                st.rerun()
        with c2: 
            st.caption(f"当前：第 {st.session_state.current_chapter} 章")
        
        # 字数统计
        curr_txt = st.session_state["chapters"].get(st.session_state.current_chapter, "")
        st.progress(min(len(curr_txt) / st.session_state['daily_target'], 1.0))
        st.caption(f"{len(curr_txt)} / {st.session_state['daily_target']} 字")

    # --- 4. 设定与废稿 (V1保留) ---
    with st.expander("📕 设定集"):
        new_term = st.text_input("词条", placeholder="青莲火")
        new_desc = st.text_input("描述", placeholder="异火榜19")
        if st.button("➕ 添加"):
            st.session_state["codex"][new_term] = new_desc
            st.success("已录")
        for k, v in st.session_state["codex"].items():
            st.markdown(f"**{k}**: {v}")

    with st.expander("🗑️ 废稿篓"):
        if st.button("📥 存废稿"):
            if st.session_state["work_draft"]:
                st.session_state["scrap_yard"].append(st.session_state["work_draft"])
                st.success("存了")
        if st.session_state["scrap_yard"]:
            st.markdown("---")
            for i, s in enumerate(st.session_state["scrap_yard"]):
                with st.popover(f"查看废稿 {i+1}"):
                    st.text_area("内容", s, height=200)

# ==========================================
# 4. 核心逻辑：DeepSeek 导演引擎 (带禁词)
# ==========================================
def run_director(mode, content, user_req, word_limit, banned_words):
    """
    mode: "polish" (润色), "logic" (逻辑), "expand" (续写)
    """
    genre = st.session_state.get("final_genre", "东方玄幻")
    style_dna = st.session_state.get("style_dna", "标准白金文风")
    
    # 基础 Prompt：加入流派 + 禁词
    sys_p = (
        f"你是一个起点白金作家。当前创作类型：【{genre}】。\n"
        "【绝对禁令 - 违反直接封号】\n"
        f"1. **黑名单词汇（严禁出现）**：{banned_words}。\n"
        "2. **严禁 AI 标点**：禁止频繁使用破折号 '——'。禁止用冒号引出长段独白。\n"
        "3. **严禁无效描写**：不要写角色'怎么被扔出去的'（无效动作），要写他'为什么愤怒'（核心冲突）。\n"
        "4. **黄金三章**：开局必须有危机、有悬念，拒绝慢热。\n"
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
            f"不要写正文！请作为主编，分析以下片段的逻辑漏洞，并给出后续剧情的 3 个高潮走向建议。\n"
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
    st.info(f"👋 欢迎回来！当前模式：{st.session_state.get('final_genre', '未设定')}。左侧写草稿，右侧 AI 精修。")
    if st.button("明白，开始创作"):
        st.session_state["first_visit"] = False
        st.rerun()

tab_main, tab_publish = st.tabs(["✍️ 沉浸精修台", "💾 发书控制台"])

# --- TAB 1: 沉浸精修台 (V2 核心) ---
with tab_main:
    st.markdown(f"### 📖 第 {st.session_state.current_chapter} 章 · {st.session_state['final_genre']}")
    
    # 布局：左（草稿） - 中（控制） - 右（成品）
    c_left, c_mid, c_right = st.columns([4, 1, 4])
    
    # 1. 左侧：原稿区
    with c_left:
        st.markdown("#### 📝 草稿 / 大纲 / 废料")
        st.caption("随便写，流水账也没关系，逻辑通就行。")
        draft_in = st.text_area(
            "Draft", 
            value=st.session_state["work_draft"], 
            height=600, 
            label_visibility="collapsed",
            placeholder="在此输入剧情片段..."
        )
        st.session_state["work_draft"] = draft_in # 实时保存

    # 2. 中间：控制台
    with c_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # 参数控制
        target_w = st.number_input("字数", 100, 5000, 1500, step=100, label_visibility="collapsed")
        user_req = st.text_input("要求", placeholder="如：更有画面感", label_visibility="collapsed")
        
        st.markdown("---")
        
        # 核心按钮群
        if st.button("✨\n润\n色", use_container_width=True, help="将草稿转化为正文"):
            if not draft_in: st.toast("左边没字啊！", icon="😫")
            else:
                with c_right:
                    st.session_state["work_result"] = "" # 清空旧的
                    st.markdown("#### 💎 大神精修版")
                    placeholder = st.empty()
                    full_text = ""
                    stream = run_director("polish", draft_in, user_req, target_w, banned_words_str)
                    if stream:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                txt = chunk.choices[0].delta.content
                                full_text += txt
                                placeholder.markdown(full_text + " ▌")
                        placeholder.markdown(full_text)
                        st.session_state["work_result"] = full_text

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🧠\n逻\n辑", use_container_width=True, help="分析逻辑漏洞"):
             if not draft_in: st.toast("没内容分析啥？", icon="🤔")
             else:
                with c_right:
                    st.markdown("#### 🩺 剧情诊断")
                    stream = run_director("logic", draft_in, "", 500, banned_words_str)
                    st.write_stream(stream)

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀\n续\n写", use_container_width=True, help="基于左侧内容往下编"):
             if not draft_in: st.toast("给个开头啊", icon="😶")
             else:
                with c_right:
                    st.markdown("#### 🚀 续写结果")
                    stream = run_director("expand", draft_in, user_req, target_w, banned_words_str)
                    st.write_stream(stream)

    # 3. 右侧：成品区
    with c_right:
        # 如果还没生成，显示当前章节的已保存内容，或者提示
        if not st.session_state["work_result"]:
            st.markdown("#### 💎 大神精修版")
            st.info("点击中间按钮，AI 将在此生成。")
        else:
            # 如果有生成结果，显示结果
            st.markdown("#### 💎 大神精修版 (未保存)")
            st.text_area("Result", value=st.session_state["work_result"], height=550, label_visibility="collapsed")
            
            # 保存按钮
            if st.button("💾 采纳并追加到本章", use_container_width=True, type="primary"):
                # 将润色好的内容追加到 chapters 存储中
                if st.session_state["current_chapter"] not in st.session_state["chapters"]:
                    st.session_state["chapters"][st.session_state["current_chapter"]] = ""
                
                st.session_state["chapters"][st.session_state["current_chapter"]] += "\n\n" + st.session_state["work_result"]
                
                # 清空工作区，方便下一段
                st.session_state["work_result"] = "" 
                st.session_state["work_draft"] = ""
                st.success("已写入！请在下方查看全章预览。")
                time.sleep(1)
                st.rerun()

    # --- 全章预览 ---
    st.divider()
    with st.expander(f"📜 第 {st.session_state.current_chapter} 章 · 全文预览 (可手动编辑)", expanded=True):
        # 允许用户最后手动修改全章
        current_full_text = st.session_state["chapters"].get(st.session_state.current_chapter, "")
        new_full_text = st.text_area("Chapter Edit", value=current_full_text, height=300, label_visibility="collapsed")
        if new_full_text != current_full_text:
            st.session_state["chapters"][st.session_state.current_chapter] = new_full_text

# --- TAB 2: 发书控制台 (V1保留) ---
with tab_publish:
    st.info("准备发布？这里可以将所有章节打包。")
    
    full_book_text = ""
    for ch_num in sorted(st.session_state["chapters"].keys()):
        content = st.session_state["chapters"][ch_num]
        full_book_text += f"\n\n### 第 {ch_num} 章 ###\n\n{content}"
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("#### 🧹 纯净 TXT (单文件)")
        # 清洗 Markdown 符号
        clean_text = full_book_text.replace("**", "").replace("##", "")
        st.download_button("📥 下载全书", clean_text, "novel_full.txt")
        
    with c_p2:
        st.markdown("#### 📦 分章打包 (ZIP)")
        if st.button("🎁 生成压缩包"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ch_num, content in st.session_state["chapters"].items():
                    clean_c = content.replace("**", "").replace("##", "")
                    zip_file.writestr(f"Chapter_{ch_num}.txt", clean_c)
            st.download_button("📥 下载 ZIP", zip_buffer.getvalue(), "novel_chapters.zip", mime="application/zip")
    
    st.divider()
    st.markdown("#### 💊 备份数据")
    st.caption("导出包含设定集、废稿在内的所有数据。")
    backup = {
        "chapters": st.session_state["chapters"],
        "codex": st.session_state["codex"],
        "scrap": st.session_state["scrap_yard"]
    }
    st.download_button("📥 导出备份 (.json)", json.dumps(backup, ensure_ascii=False), "backup.json")