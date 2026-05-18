import feedparser
import smtplib
import os
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime
from openai import OpenAI

# 从环境变量读取敏感信息
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

if not all([DEEPSEEK_API_KEY, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
    raise ValueError("请设置环境变量: DEEPSEEK_API_KEY, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")

RSS_FEEDS = [
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("BBC News", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("36氪", "https://36kr.com/feed"),
    ("Reuters", "http://feeds.reuters.com/reuters/topNews"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
]

MAX_ARTICLES_PER_FEED = 3
MAX_TOTAL_ARTICLES = 15

def fetch_articles(feed_url, limit):
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
            })
        return articles
    except Exception as e:
        print(f"抓取失败 {feed_url}: {e}")
        return []

def humanize_news(title, link):
    prompt = f"""请用非常自然、口语化的中文，将下面这条新闻改写成一句“人话”。就像朋友聊天一样，可以带一点情绪或点评，不要官腔、不要“据报道”之类的套话。

新闻标题：{title}
链接：{link}

要求：只输出改写后的一句话，不超过40个字。"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,    # 从0.7修改为0.5
            max_tokens=80
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"【AI偷懒】{title[:30]}……"

def build_email_body(all_news):
    today = datetime.now().strftime("%Y-%m-%d")
    body = f"📧 你的每日新闻简报 – {today}\n\n"
    for source_name, articles in all_news:
        body += f"✨ {source_name}\n"
        for art in articles:
            body += f"• {art['human']}\n  🔗 {art['link']}\n\n"
    body += "---\n🤖 本简报由 DeepSeek AI 自动生成 | 祝你有美好的一天！"
    return body

def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = Header(SENDER_EMAIL)
    msg["To"] = Header(RECEIVER_EMAIL)
    msg["Subject"] = Header(subject, "utf-8")
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
    print("邮件发送成功")

def main():
    all_news = []
    total = 0
    for name, url in RSS_FEEDS:
        if total >= MAX_TOTAL_ARTICLES:
            break
        print(f"抓取 {name} ...")
        articles = fetch_articles(url, MAX_ARTICLES_PER_FEED)
        if not articles:
            continue
        enriched = []
        for art in articles:
            if total >= MAX_TOTAL_ARTICLES:
                break
            human = humanize_news(art["title"], art["link"])
            enriched.append({
                "title": art["title"],
                "link": art["link"],
                "human": human
            })
            total += 1
        if enriched:
            all_news.append((name, enriched))
    if not all_news:
        print("没有抓到任何新闻，不发送邮件。")
        return
    subject = f"AI新闻简报 - {datetime.now().strftime('%Y-%m-%d')}"
    body = build_email_body(all_news)
    send_email(subject, body)

if __name__ == "__main__":
    main()