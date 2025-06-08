import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.news_summary import (
    summarize_news, 
    format_notification, 
    NewsSummary, 
    SummaryPoint
)


class TestNewsSummary(unittest.TestCase):
    
    def setUp(self):
        """テスト用のサンプルデータを準備"""
        self.sample_entry = Mock()
        self.sample_entry.title = "最新のLLM技術について"
        self.sample_entry.link = "https://example.com/llm-news"
        self.sample_entry.get.return_value = "生成AIの最新技術について詳しく解説しています。"
        
        self.sample_news_summary = NewsSummary(
            overall_summary="LLM技術の進歩により、より高精度な自然言語処理が可能になっています。",
            key_points=[
                SummaryPoint(
                    title="性能向上",
                    description="従来比で30%の精度向上を実現"
                ),
                SummaryPoint(
                    title="計算効率化",
                    description="推論時間を50%短縮"
                ),
                SummaryPoint(
                    title="多言語対応",
                    description="100以上の言語をサポート"
                )
            ]
        )
    
    def test_format_notification(self):
        """通知フォーマット機能のテスト"""
        result = format_notification(self.sample_news_summary)
        
        # 期待される構造が含まれているかチェック
        self.assertIn("LLM技術の進歩により", result)
        self.assertIn("1. *性能向上*", result)
        self.assertIn("2. *計算効率化*", result)
        self.assertIn("3. *多言語対応*", result)
        
        # コードブロックが含まれているかチェック
        self.assertIn("```", result)
        
        print("✓ format_notification テスト成功")
        print(f"生成された通知フォーマット:\n{result}\n")
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('service.news_summary.OpenAI')
    def test_summarize_news_success(self, mock_openai_class):
        """summarize_news関数の正常系テスト"""
        # OpenAI APIのモックレスポンスを設定
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "overall_summary": "テスト用の全体要約です。",
            "key_points": [
                {
                    "title": "テスト要点1",
                    "description": "テスト説明1"
                },
                {
                    "title": "テスト要点2", 
                    "description": "テスト説明2"
                }
            ]
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # テスト実行
        processed_news = {}
        news_entries = [self.sample_entry]
        
        result = summarize_news(news_entries, processed_news)
        
        # 結果検証
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], "最新のLLM技術について")
        self.assertEqual(result[0]['link'], "https://example.com/llm-news")
        self.assertIn("テスト用の全体要約です", result[0]['summary'])
        
        # OpenAI APIが正しく呼ばれたかチェック
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        # response_formatがstructural outputに設定されているかチェック
        self.assertEqual(call_args[1]['response_format']['type'], 'json_schema')
        self.assertEqual(call_args[1]['response_format']['json_schema']['name'], 'news_summary')
        
        print("✓ summarize_news 正常系テスト成功")
        print(f"生成されたサマリー:\n{result[0]['summary']}\n")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_summarize_news_no_api_key(self):
        """APIキーが設定されていない場合のテスト"""
        processed_news = {}
        news_entries = [self.sample_entry]
        
        result = summarize_news(news_entries, processed_news)
        
        # 空のリストが返されることを確認
        self.assertEqual(result, [])
        
        print("✓ APIキー未設定時のテスト成功")
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('service.news_summary.OpenAI')
    def test_summarize_news_api_error(self, mock_openai_class):
        """OpenAI API呼び出しでエラーが発生した場合のテスト"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # API呼び出しで例外を発生させる
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        processed_news = {}
        news_entries = [self.sample_entry]
        
        result = summarize_news(news_entries, processed_news)
        
        # エラーが発生しても空のリストが返されることを確認
        self.assertEqual(result, [])
        
        print("✓ API エラー時のテスト成功")
    
    def test_pydantic_models(self):
        """Pydanticモデルの構造テスト"""
        # SummaryPointモデルのテスト
        point = SummaryPoint(title="テストタイトル", description="テスト説明")
        self.assertEqual(point.title, "テストタイトル")
        self.assertEqual(point.description, "テスト説明")
        
        # NewsSummaryモデルのテスト
        summary = NewsSummary(
            overall_summary="全体要約",
            key_points=[point]
        )
        self.assertEqual(summary.overall_summary, "全体要約")
        self.assertEqual(len(summary.key_points), 1)
        self.assertEqual(summary.key_points[0].title, "テストタイトル")
        
        # JSON Schemaが正しく生成されるかテスト
        schema = NewsSummary.model_json_schema()
        self.assertIn("properties", schema)
        self.assertIn("overall_summary", schema["properties"])
        self.assertIn("key_points", schema["properties"])
        
        print("✓ Pydantic モデルのテスト成功")


if __name__ == '__main__':
    print("=== AI News Summary テスト開始 ===\n")
    unittest.main(verbosity=2)