import json
import datetime
import requests
import streamlit as st
from openai import OpenAI
from ddgs import DDGS

# 尝试从 Streamlit Secrets 读取 API Key
try:
    DEEPSEEK_KEY = st.secrets["DEEPSEEK_KEY"]
except Exception:
    st.error("❌ 未找到 DeepSeek API Key，请在 Streamlit Cloud 的 Secrets 中配置 DEEPSEEK_KEY")
    st.stop()

client = OpenAI(
    api_key=DEEPSEEK_KEY,
    base_url="https://api.deepseek.com/v1"
)

# ---------- 工具定义 ----------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如 '3*5+2'"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "在互联网上搜索信息，用于回答实时问题或未知信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如 '今天北京天气'"}
                },
                "required": ["query"]
            }
        }
    }
]

# ---------- 工具实现 ----------
def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str):
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

def web_search(query: str):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "未找到相关信息。"
            snippets = [f"{r['title']}: {r['body']}" for r in results]
            return "\n".join(snippets)
    except Exception as e:
        return f"搜索失败: {e}"

# ---------- 核心对话函数 ----------
def get_ai_response(messages):
    """输入消息列表（每个元素是字典，包含 role, content 等），返回助手的回答字符串，并更新 messages 列表"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = response.choices[0].message

    # 将 assistant 的响应（可能含 tool_calls）转为字典存入历史
    assistant_dict = {"role": msg.role, "content": msg.content}
    if msg.tool_calls:
        assistant_dict["tool_calls"] = msg.tool_calls
    messages.append(assistant_dict)

    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if func_name == "get_current_time":
                result = get_current_time()
            elif func_name == "calculate":
                expr = args.get("expression")
                result = calculate(expr)
            elif func_name == "web_search":
                query = args.get("query")
                result = web_search(query)
            else:
                result = "未知工具"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # 第二次请求生成最终回答
        response2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        final_msg = response2.choices[0].message
        final_dict = {"role": final_msg.role, "content": final_msg.content}
        messages.append(final_dict)
        return final_msg.content
    else:
        return msg.content

# ---------- Streamlit 界面 ----------
st.set_page_config(page_title="个人智能助手", page_icon="🤖")
st.title("🤖 你的个人助手")
st.markdown("支持查时间、计算、联网搜索。")

# 初始化聊天历史（仅存字典）
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "system", "content": "你是一个能调用工具的个人助手，可以获取时间、计算、搜索网络。请友好回应。"}
    ]

# 显示历史消息（排除 system）
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.write(msg["content"])

# 输入框
user_input = st.chat_input("问点什么吧...")
if user_input:
    # 添加用户消息
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 获取助手回复
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            reply = get_ai_response(st.session_state.chat_history)
            st.write(reply)
    # 助手回复已经由 get_ai_response 添加到 chat_history 中，无需重复添加