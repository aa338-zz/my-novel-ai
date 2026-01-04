import streamlit as st
from openai import OpenAI

# --- 1. 网页配置 ---
st.set_page_config(page_title="AI 小说大神 (会员版)", page_icon="🔒", layout="wide")

# --- 2. 简单的会员名单 (用户名: 密码) ---
# 注意：正式做大生意需要用数据库，前期我们手动管理这个名单就行
USERS = {
    "vip001": "123456",  # 会员1
    "vip002": "888888",  # 会员2
    "admin": "admin"     # 你自己
}

# --- 3. 登录检查函数 ---
def check_login():
    # 如果已经登录成功，就不显示登录框
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.header("🔒 会员登录")
        st.write("本站为会员制，请输入账号密码进入。")
        
        username = st.text_input("账号")
        password = st.text_input("密码", type="password")
        
        if st.button("登录"):
            if username in USERS and USERS[username] == password:
                st.session_state["logged_in"] = True
                st.success("登录成功！")
                st.rerun() # 刷新页面进入系统
            else:
                st.error("账号或密码错误，请联系管理员开通。")
        st.stop() # 没登录就卡在这里，不运行下面的代码

# --- 运行登录检查 ---
check_login()

# ==========================================
# 下面是你之前的“小说大神”核心代码
# 只有登录成功后，程序才会运行到这里
# ==========================================

st.title("📚 沉浸式小说创作助手 (VIP专享)")

with st.sidebar:
    st.header("⚙️ 创作控制台")
    # 这里依然需要 Key，但未来我们可以把 Key 藏在服务器里，不用会员填
    api_key = st.text_input("请输入 DeepSeek API Key:", type="password")
    st.divider()
    novel_genre = st.selectbox("选择小说类型", ("玄幻修仙", "都市言情", "悬疑推理"))
    novel_style = st.selectbox("选择文笔风格", ("爽文风格", "细腻唯美", "暗黑深沉"))

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "尊敬的会员，你想写个什么故事？"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input("开始创作..."):
    if not api_key:
        st.warning("请输入 API Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # 简化的 Prompt，保留核心逻辑
    system_prompt = f"你是一位畅销书作家，正在写一本{novel_style}风格的{novel_genre}小说。"
    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="deepseek-chat", messages=messages_to_send, stream=True
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})