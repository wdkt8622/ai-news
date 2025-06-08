# AI News Summary

生成AI関連のニュースを自動収集し、要約してSlackに通知するシステムです。

## 機能

- 複数のRSSフィードから最新ニュースを取得
- AI技術を使用してLLM/生成AI関連のニュースをフィルタリング
- Structural Outputを使用した安定したニュース要約生成
- Slackへの自動通知

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

以下の環境変数を設定してください：

```bash
export OPENAI_API_KEY="your-openai-api-key"
export SLACK_WEBHOOK_URL="your-slack-webhook-url"
```

## 実行方法

### メインプログラムの実行

```bash
python service/news_summary.py
```

### テストの実行

#### 全テストの実行

```bash
python -m pytest tests/ -v
```

#### 特定のテストファイルの実行

```bash
python tests/test_news_summary.py
```

#### Unittestモジュールを使用した実行

```bash
python -m unittest tests.test_news_summary -v
```

## テスト内容

テストは以下の機能をカバーしています：

1. **フォーマット機能テスト** (`test_format_notification`)
   - 通知文章の雛形が正しく動作するかテスト
   - プレースホルダーの置換が正常に行われるかチェック

2. **要約機能テスト** (`test_summarize_news_success`)
   - OpenAI APIとの連携が正常に動作するかテスト
   - Structural Outputが正しく設定されているかチェック

3. **エラーハンドリングテスト**
   - APIキー未設定時の処理 (`test_summarize_news_no_api_key`)
   - API呼び出しエラー時の処理 (`test_summarize_news_api_error`)

4. **Pydanticモデルテスト** (`test_pydantic_models`)
   - データモデルの構造が正しく定義されているかテスト
   - JSON Schemaの生成が正常に行われるかチェック

## アーキテクチャ

### Structural Output

このシステムはOpenAI APIのStructural Output機能を使用して、安定した要約生成を実現しています：

- **NewsSummary**: 記事全体の要約と要点リストを含む
- **SummaryPoint**: 各要点のタイトルと説明を含む
- **NotificationTemplate**: Slack通知用のテンプレート

### 通知フォーマット

生成される通知は以下の雛形に従います：

```
```
{全体要約}
```
1. *{要点1タイトル}* ：{要点1説明}
2. *{要点2タイトル}* ：{要点2説明}
...
```

これにより、常に一貫性のある読みやすい形式でニュースが配信されます。

## ファイル構成

```
ai-news/
├── service/
│   ├── news_summary.py          # メイン処理
│   └── processed_news.json      # 処理済みニュース管理
├── tests/
│   └── test_news_summary.py     # テストコード
├── requirements.txt             # 依存関係
└── README.md                   # このファイル
```