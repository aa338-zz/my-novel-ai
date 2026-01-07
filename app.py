import streamlit as st
from openai import OpenAI
import json
import time

# ==========================================
# 0. 全局配置 & 核心记忆初始化
# ==========================================
st.set_page_config(
    page_title="GENESIS · 创世笔 V2", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session():
    defaults = {
        # --- 核心写作数据 ---
        "draft_content": "",       # 左侧：你的草稿/大纲
        "polished_content": "",    # 右侧：AI精修后的正文
        "style_guide": "",         # 朋友喂的“大神文风”
        
        # --- 状态标记 ---
        "logged_in": False,
        "first_visit": True,       # 新手引导
        "history_snapshots": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session()

# ==========================================
# 1. 样式美化 (去AI味的视觉暗示)
# ==========================================
st.markdown("""
<style>
    .stTextArea textarea {font-size: 16px; line-height: 1.6; font-family: 'SimSun', serif;} 
    .big-btn {padding: 20px !important; font-size: 20px !important; font-weight: bold !important;}
    .report-box {background: #f1f3f5; padding: 15px; border-left: 5px solid #fa5252; border-radius: 4px;}
    .success-box {background: #e6fcf5; padding: 15px; border-left: 5px solid #0ca678; border-radius: 4px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 简易登录 (保留)
# ==========================================
USERS = {"vip": "666", "admin": "admin"} 
def check_login():
    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.title("⚡ 创世笔")
            st.caption("专为网文大神打造的‘去AI化’辅助终端")
            pwd = st.text_input("🔑 启动密钥", type="password")
            if st.button("🚀 进入工作台", use_container_width=True):
                if pwd in USERS.values():
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("密钥错误")
        st.stop()
check_login()

# ==========================================
# 3. 侧边栏：喂书 & 参数 (关键！)
# ==========================================
with st.sidebar:
    st.markdown("### 🧬 基因工程 (喂书区)")
    
    # API配置
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        st.success("🧠 神经网络：在线")
    else:
        st.error("🔴 缺 API Key")
        st.stop()

    st.info("👇 这里是你朋友发挥的地方")
    uploaded_style = st.file_uploader("📥 投喂大神切片 (.txt)", type=["txt"])
    
    if uploaded_style:
        raw_text = uploaded_style.getvalue().decode("utf-8")
        if st.button("🧪 提取文风基因"):
            with st.spinner("正在解析大神节奏..."):
                # 让AI分析这段文字的“黄金节奏”
                p = f"分析这段网文的节奏、用词习惯、开篇冲突设置。\n样本：{raw_text[:1500]}\n只输出核心分析结果，不要废话。"
                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}])
                st.session_state["style_guide"] = resp.choices[0].message.content
                st.success("✅ 基因提取完成！已注入润色引擎。")

    if st.session_state["style_guide"]:
        with st.expander("查看当前文风"):
            st.caption(st.session_state["style_guide"])

    st.divider()
    
    st.markdown("### ⚙️ 润色参数")
    novel_type = st.selectbox("📚 类型", ["玄幻 | 练气", "都市 | 异能", "悬疑 | 诡秘", "历史 | 争霸"])
    # 针对你朋友说的“字数控制”
    target_words = st.number_input("🎯 目标字数", 500, 5000, 2000, step=100)
    
    if st.button("❓ 找回新手引导"):
        st.session_state["first_visit"] = True
        st.rerun()

# ==========================================
# 4. 逻辑核心：去 AI 味的 Prompt
# ==========================================
def generate_novel(action_type, input_text):
    """
    核心生成函数
    action_type: "polish" (润色), "expand" (扩写), "logic" (逻辑梳理)
    """
    
    # 基础人设：严格禁止 AI 习惯
    base_system = (
        f"你是一个起点白金作家。擅长类型：{novel_type}。\n"
        "【绝对禁令 - 违反直接封号】\n"
        "1. **严禁滥用比喻**：禁止出现'像小刀子一样的风'、'像灌了铅的腿'这种陈词滥调。\n"
        "2. **严禁 AI 标点**：禁止频繁使用破折号 '——'。禁止用冒号引出长段独白。\n"
        "3. **严禁无效描写**：不要写角色'怎么被扔出去的'，要写他'为什么愤怒'。动作服务于剧情。\n"
        "4. **开篇法则**：黄金三章原则。开局要有冲突，要有悬念，拒绝慢热。\n"
    )

    # 注入朋友喂的文风
    if st.session_state["style_guide"]:
        base_system += f"\n【模仿文风】\n{st.session_state['style_guide']}\n"

    user_prompt = ""
    
    if action_type == "polish":
        user_prompt = (
            f"请润色以下片段。去除水词，去除 AI 味，加强冲突和画面感。\n"
            f"目标字数：{target_words}字左右。\n"
            f"【原稿】：\n{input_text}"
        )
    elif action_type == "logic":
        user_prompt = (
            f"不要写正文！分析以下片段的逻辑漏洞，并给出后续剧情的 3 个高潮走向建议。\n"
            f"【原稿】：\n{input_text}"
        )
    
    # 流式输出
    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": base_system},
                {"role": "user", "content": user_prompt}
            ],
            stream=True,
            temperature=1.3  # 稍微高一点，为了更有创意
        )
        return stream
    except Exception as e:
        st.error(f"引擎过热：{e}")
        return None

# ==========================================
# 5. 主界面：左写右改
# ==========================================
st.markdown("## ⚡ GENESIS · 创作台")

# 新手引导
if st.session_state["first_visit"]:
    st.info("👋 欢迎！左边放你的大纲或废稿，右边 AI 帮你改成大神之作。点击侧边栏可以‘喂书’。")
    if st.button("我懂了，开始吧"):
        st.session_state["first_visit"] = False
        st.rerun()

# 双栏布局
col_left, col_btn, col_right = st.columns([4, 1, 4])

with col_left:
    st.markdown("#### 📝 原稿 / 大纲 / 废稿")
    draft = st.text_area(
        "draft_input", 
        value=st.session_state["draft_content"], 
        height=600, 
        placeholder="在这里输入你的想法，比如：\n萧火火被退婚了，他很生气，喊了一句莫欺少年穷。\n(哪怕是流水账也没关系，交给AI去修)",
        label_visibility="collapsed"
    )
    # 实时保存左侧输入，防止丢失
    st.session_state["draft_content"] = draft

with col_btn:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    # 按钮 1：核心润色
    if st.button("✨\n注\n入\n灵\n魂", use_container_width=True):
        if not draft:
            st.warning("左边没字啊大哥")
        else:
            with col_right:
                st.markdown("#### 💎 大神精修版")
                st.session_state["polished_content"] = "" # 清空旧的
                placeholder = st.empty()
                full_response = ""
                
                stream = generate_novel("polish", draft)
                if stream:
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            txt = chunk.choices[0].delta.content
                            full_response += txt
                            placeholder.markdown(full_response + " ▌")
                    placeholder.markdown(full_response)
                    st.session_state["polished_content"] = full_response
                    st.success("润色完成！")

    st.markdown("<br>", unsafe_allow_html=True)

    # 按钮 2：逻辑诊断
    if st.button("🧠\n逻\n辑\n诊\n断", use_container_width=True):
        if not draft: st.warning("没内容")
        else:
            with col_right:
                st.markdown("#### 🩺 剧情诊断书")
                stream = generate_novel("logic", draft)
                st.write_stream(stream)

with col_right:
    # 如果没生成，显示标题；如果生成了，内容在上面按钮回调里已经显示了
    if not st.session_state["polished_content"]:
        st.markdown("#### 💎 大神精修版 (等待生成...)")
        st.info("点击中间的按钮，AI 将在这里重写你的故事。")
    else:
        # 这里是为了刷新后内容不丢失
        # 注意：实际流式输出在按钮里，这里是用来持久化显示的
        st.text_area(
            "result_display",
            value=st.session_state["polished_content"],
            height=600,
            label_visibility="collapsed"
        )
        if st.button("📋 复制结果"):
            st.toast("请手动全选复制 (浏览器限制)", icon="⚠️")

# ==========================================
# 6. 底部工具栏
# ==========================================
st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    st.caption(f"当前模式：{novel_type}")
with c2:
    if st.session_state["style_guide"]:
        st.caption("🧬 文风挂载：已激活")
    else:
        st.caption("🧬 文风挂载：无 (使用默认白金模式)")
with c3:
    st.caption(f"DeepSeek 引擎就绪")