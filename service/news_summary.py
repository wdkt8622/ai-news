import json
import feedparser
import openai
from openai import OpenAI
import requests
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

processed_news_file = "processed_news.json"


def load_processed_news():
    if os.path.exists(processed_news_file):
        with open(processed_news_file, "r") as file:
            return json.load(file)
    return {}


def save_processed_news(processed_news):
    with open(processed_news_file, "w") as file:
        json.dump(processed_news, file)


def clean_old_news(processed_news, days=7):
    threshold_date = datetime.now() - timedelta(days=days)
    threshold_timestamp = int(threshold_date.timestamp())
    return {k: v for k, v in processed_news.items() if v > threshold_timestamp}


def get_rss_feeds(urls, processed_news):
    all_entries = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.error(f"Failed to parse feed: {url}")
            else:
                for entry in feed.entries:
                    link = entry.get("link")
                    if link and link not in processed_news:
                        all_entries.append(entry)
                        processed_news[link] = int(datetime.now().timestamp())
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
    return all_entries


def filter_ai_news(feed_entries):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OpenAI API key is not set.")
        return []

    openai.api_key = openai_api_key
    client = OpenAI()

    filtered_entries = []

    for entry in feed_entries:
        title = entry.title
        description = entry.get("description", "")
        content = entry.get("content", "")[:300]

        prompt = f"""
与えられた文章が、以下の条件に合致する場合は1、そうでない場合は0を出力せよ。結果は0か1のみを出力すること。
# 条件
[LLM, 生成AI, 生成系AI, 基盤モデル, 大規模言語モデル, ChatGPT, OpenAI, Gemini, Claude, RAG]のいずれかに深く関連すること。
# 文章
{title}
{description}
{content}
# 結果
result=
"""
        logger.debug(f"filter_prompt: {prompt}")

        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}]
            )
            ai_decision = completion.choices[0].message.content.strip()
            if ai_decision == "1":
                filtered_entries.append(entry)
        except Exception as e:
            logger.error(f"Error in AI filtering: {e}")

    return filtered_entries


def summarize_news(news_entries, processed_news):
    summaries = []
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OpenAI API key is not set.")
        return summaries

    openai.api_key = openai_api_key
    client = OpenAI()

    for entry in news_entries:
        link = entry.get("link")
        try:
            prompt = f"""
以下の記事のContentをFormatに従って要約して下さい。
<制約条件>
- 要点は3~5つに絞って下さい。
- 日本語で要約して下さい。
- Formatの内容以外のことは出力しないでください。
<Format>
```
{{記事全体の要約を100字程度で出力する}}
```
1. *{{要点1見出し}}* ：{{要点1のまとめ}}
2. *{{要点2見出し}}* ：{{要点2のまとめ}}
...
n. *{{要点n見出し}}* ：{{要点nのまとめ}}
ーーーーーーーー
<Content>
{entry.title}
{entry.get('content', '')}
"""
            logger.debug(f"summary_prompt: {prompt}")

            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                temperature=0,
            )
            summaries.append(
                {
                    "title": entry.title,
                    "summary": completion.choices[0].message.content,
                    "link": entry.link,
                }
            )
            processed_news[link] = int(datetime.now().timestamp())
        except Exception as e:
            logger.error(f"Error summarizing news: {e}")
    return summaries


def send_to_slack(summaries, webhook_url):
    if not webhook_url:
        logger.error("Slack Webhook URL is not set.")
        return

    for summary in summaries:
        try:
            message = {
                "text": f"*<{summary['link']}|{summary['title']}>*\n{summary['summary']}",
                "unfurl_links": True,
            }
            response = requests.post(webhook_url, json=message)
            if response.status_code != 200:
                logger.error(f"Failed to send message to Slack: {response.status_code}")

            logger.debug(f"message: {message}")
        except Exception as e:
            logger.error(f"Error sending to Slack: {e}")


def main():
    # 環境変数のチェック
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        logger.error("Slack Webhook URL is not set.")
        return

    # 処理済みニュースの読み込み
    processed_news = load_processed_news()

    # 古いニュースを削除
    processed_news = clean_old_news(processed_news)

    # 複数のRSSフィードからニュースを取得
    rss_urls = [
        "https://qiita.com/popular-items/feed",
        # "https://gigazine.net/news/rss_2.0/",
        # "https://b.hatena.ne.jp/entrylist/it.rss",
        # "https://dev.classmethod.jp/feed/",
        # "https://news.microsoft.com/ja-jp/feed/",
        # "https://aws.amazon.com/jp/about-aws/whats-new/recent/feed/",
        # "https://zenn.dev/feed",
    ]
    print(f"Fetching RSS feeds from {len(rss_urls)} sources.")
    feed_entries = get_rss_feeds(rss_urls, processed_news)
    print(f"Fetched {len(feed_entries)} new entries from RSS feeds.")

    # ニュースから生成AIに関連するものを抽出
    print("Filtering AI-related news...")
    ai_related_entries = filter_ai_news(feed_entries)
    print(f"Filtered down to {len(ai_related_entries)} AI-related entries.")

    # ニュースのサマリを生成
    print("Generating summaries for filtered news...")
    summaries = summarize_news(ai_related_entries, processed_news)
    print(f"Generated summaries for {len(summaries)} entries.")

    # 処理済みニュースの保存
    save_processed_news(processed_news)
    print("Saved processed news data.")

    # サマリをSlackに送信
    print("Sending summaries to Slack...")
    send_to_slack(summaries, slack_webhook_url)
    print("Summaries sent to Slack.")


if __name__ == "__main__":
    main()
