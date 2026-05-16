# estimate_aws2026

Amazon Bedrock AgentCore Runtime 上で動作する、AWS構成の概算見積もりエージェントです。

現在は初期PoCとして、自然文から代表的なAWSサービスと規模感を抽出し、組み込みの簡易単価表で月額概算を返します。

## 現在できること

- AgentCore Runtime へのコンテナデプロイ
- 自然文からAWSサービスを検出
- 月間リクエスト数、保存容量、ユーザー数の簡易抽出
- 月額USD概算とJPY参考換算の返却
- CLI向けの `terminal` 出力
- 詳細確認向けの `full` / `markdown` / `ascii_json` 出力

## 実行例

```bash
agentcore invoke '{"prompt": "月1000000リクエスト、50GB。Lambda API Gateway S3 DynamoDB CloudWatchで見積もり", "format": "terminal"}'
```

```bash
agentcore invoke '{"prompt": "EC2 1台、RDS、S3 100GBで月額見積もり", "format": "terminal"}'
```

## 出力形式

| format | 用途 |
|---|---|
| `compact` | デフォルト。短いJSON結果 |
| `terminal` | CLIで読みやすい英語テキスト |
| `full` | 日本語の詳細JSON |
| `markdown` | Markdown本文 |
| `ascii_json` | 文字化け回避用のASCIIエスケープJSON |

## デプロイ

```bash
agentcore deploy
```

## 注意

現在の見積もりはAWS Pricing APIではなく、エージェント内の簡易単価表によるラフ見積もりです。税、データ転送、無料枠、割引、サポート料金は詳細計算していません。
