import streamlit as st
from openai import OpenAI

# --- 1. 网页配置 ---
st.set_page_config(page_title="创世笔 (Genesis Pen)", page_icon="🖊️", layout="wide")

# --- 2. 会员系统 (保持不变) ---
USERS = {
    "vip001": "123456",
    "vip002": "888888",
    "admin": "admin"
}

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.header("🔒 创世笔 - 会员登录")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=100)
        with c2:
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            if st.button("🚀 登录"):
                if username in USERS and USERS[username] == password:
                    st.session_state["logged_in"] = True
                    st.toast("欢迎回来，大作家！", icon="🎉")
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        st.stop()

check_login()

# ==========================================
# 主界面
# ==========================================

st.title("🖊️ 创世笔 (Genesis Pen)")
st.caption("VIP 专属通道 | 沉浸式小说创作引擎")

with st.sidebar:
    st.header("⚙️ 创作控制台")
    
    # 读取 Key
    if "DEEPSEEK_API_KEY" in st.secrets:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        st.success("✅ 引擎连接正常")
    else:
        st.error("⚠️ 未配置 Secrets，请检查后台")
        st.stop()

    st.divider()
    
    # --- ✨ 新增功能：投喂设定集 ---
    st.subheader("📚 投喂设定 (让 AI 记住你的书)")
    
    novel_genre = st.selectbox("小说类型", ("玄幻修仙", "都市言情", "悬疑推理", "科幻未来", "武侠江湖"))
    
    # 这里就是你“投喂数据”的地方
    world_setting = st.text_area(
        "在此粘贴世界观/大纲/人物小传：",
        height=200,
        placeholder="例如：\n1. 世界观：这是一个灵气复苏的世界，货币是灵石。\n2. 主角：林风，性格腹黑，拥有一把会说话的剑。\n3. 反派：血魔教，目的是毁灭世界。\n4. 写作要求：多描写打斗细节，不要太啰嗦。"
    )
    
    if st.button("🚪 退出登录"):
        st.session_state["logged_in"] = False
        st.rerun()

# --- 聊天记录 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "创世神您好，您的世界设定已加载。请告诉我从哪里开始写？"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- 核心创作逻辑 ---
if user_input := st.chat_input("输入剧情大纲、开头或人设..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # --- 关键：把用户投喂的数据植入给 AI ---
    # 我们通过 Prompt 告诉 AI，它手里拿着一本设定集
    system_prompt = f"""
    你现在是世界顶尖的畅销书作家，代号【创世笔】。
    你正在创作一本【{novel_genre}】小说。
    
    【重要：请严格遵守以下世界观和设定】
    {world_setting}
    
    【写作黄金法则】
    1. "Show, Don't Tell"：不要直接说他很生气，要写“他捏碎了手里的茶杯”。
    2. 节奏感：短句为主，剧情紧凑，拒绝流水账。
    3. 沉浸感：调动读者的五感（视觉、听觉、嗅觉）。
    4. 永远直接输出正文，不要说“好的我明白”这种废话。
    """
    
    # 组合 Prompt
    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="deepseek-chat", messages=messages_to_send, stream=True
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})