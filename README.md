# estimate_aws2026

Amazon Bedrock AgentCore Runtime 上で動作する、AWS構成の概算見積もりエージェントです。

現在は初期PoCとして、自然文から代表的なAWSサービスと規模感を抽出し、組み込みの簡易単価表で月額概算を返します。

## 現在できること

- AgentCore Runtime へのコンテナデプロイ
- 自然文からAWSサービスを検出
- 月間リクエスト数、保存容量、ユーザー数の簡易抽出
- EC2/RDS/Lambda/CloudFront向けの詳細条件指定
- 構成に応じた不足情報の質問生成
- 月額USD概算とJPY参考換算の返却
- `use_fm=true` 指定時のBedrock Foundation Modelによる構成抽出
- CLI向けの `terminal` 出力
- 詳細確認向けの `full` / `markdown` / `ascii_json` 出力

## 実行例

```bash
agentcore invoke '{"prompt": "月1000000リクエスト、50GB。Lambda API Gateway S3 DynamoDB CloudWatchで見積もり", "format": "terminal"}'
```

```bash
agentcore invoke '{"prompt": "EC2 1台、RDS、S3 100GBで月額見積もり", "format": "terminal"}'
```

Foundation Modelで自然文から構成を補完する場合:

```bash
agentcore invoke '{"prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり。月50万アクセス", "format": "terminal", "use_fm": true}'
```

質問から始める場合:

```bash
agentcore invoke '{"mode": "clarify", "prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり", "format": "terminal", "use_fm": true}'
```

質問への回答を渡して見積もる場合:

```bash
agentcore invoke '{"mode": "estimate", "prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり", "format": "terminal", "use_fm": true, "answers": {"monthly_requests": 500000, "storage_gb": 100, "data_transfer_gb": 300, "lambda_memory_mb": 1024, "lambda_duration_ms": 800, "users": 1000}}'
```

詳細条件を指定する場合:

```bash
agentcore invoke '{"prompt": "EC2 2台、RDS、S3 100GBで月額見積もり", "format": "terminal", "ec2_instance": "t3.small", "ec2_count": 2, "rds_instance": "db.t4g.small", "rds_storage_gb": 50, "multi_az": true}'
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

`use_fm=true` の場合も、FMは料金計算ではなく構成抽出に利用します。料金計算は引き続きPython側の簡易単価表で行います。

東京リージョンではNova Microの直指定 `amazon.nova-micro-v1:0` ではなく、APACのInference Profile ID `apac.amazon.nova-micro-v1:0` をデフォルトで使います。
