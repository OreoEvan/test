import os
import json
from datetime import datetime
from openai import OpenAI
from ddgs import DDGS

# 读取API Key（从环境变量获取，安全）
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com/v1")

# 你要研究的主题（可以改成你关心的任何话题）
TOPIC = "2026年5月AI领域最新进展"

def web_search(query):
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
        return [{"title": r["title"], "body": r["body"]} for r in results]

def generate_report(topic, search_results):
    context = "\n\n".join([f"标题：{r['title']}\n内容：{r['body']}" for r in search_results])
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个研究助手。请根据搜索结果生成一份结构清晰的日报，包含核心事件、观点和延伸阅读建议。"},
            {"role": "user", "content": f"研究主题：{topic}\n\n搜索结果：\n{context}"}
        ],
        temperature=0.5
    )
    return response.choices[0].message.content

def save_report(content):
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/research_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {TOPIC}\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(content)
    print(f"报告已保存: {filename}")
    return filename

def main():
    print(f"开始研究：{TOPIC}")
    results = web_search(TOPIC)
    if not results:
        print("没有搜索到结果")
        return
    report = generate_report(TOPIC, results)
    save_report(report)
    print("完成")

if __name__ == "__main__":
    main()