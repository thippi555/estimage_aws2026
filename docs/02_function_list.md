# AgentCore 見積エージェント 機能一覧

## 1. 現在実装済みの機能

### 1.1 自然文入力

ユーザーは `prompt` にAWS構成や条件を自然文で入力する。

例:

```json
{
  "prompt": "月1000000リクエスト、50GB。Lambda API Gateway S3 DynamoDB CloudWatchで見積もり"
}
```

### 1.2 サービス検出

以下の代表的なAWSサービスをキーワードベースで検出する。

| 内部名 | 表示名 | 主なキーワード |
|---|---|---|
| `lambda` | AWS Lambda | lambda, ラムダ, serverless |
| `api_gateway` | Amazon API Gateway | api gateway, rest api, http api |
| `s3` | Amazon S3 | s3, bucket, storage |
| `dynamodb` | Amazon DynamoDB | dynamodb, dynamo, nosql |
| `rds` | Amazon RDS | rds, postgres, mysql |
| `ecs_fargate` | Amazon ECS on Fargate | ecs, fargate, container |
| `ec2` | Amazon EC2 | ec2, instance, vm |
| `cloudfront` | Amazon CloudFront | cloudfront, cdn |
| `bedrock` | Amazon Bedrock | bedrock, claude, nova, llm |
| `cloudwatch` | Amazon CloudWatch | cloudwatch, logs, 監視 |

サービス指定がない場合は、初期構成として `lambda`, `api_gateway`, `s3`, `cloudwatch` を使う。

### 1.3 規模抽出

自然文またはJSONフィールドから以下を抽出する。

| 項目 | デフォルト | 説明 |
|---|---:|---|
| `region` | `ap-northeast-1` | 見積もり対象リージョン |
| `users` | `100` | 想定ユーザー数 |
| `monthly_requests` | `100000` | 月間リクエスト数 |
| `storage_gb` | `20` | 保存容量GB |
| `currency` | `USD` | 基準通貨 |

JSONで明示された値は自然文から抽出した値より優先する。

### 1.4 概算見積もり

`src/agent/agent_example.py` 内の簡易単価表を使って月額を算出する。

現段階ではラフ見積もりであり、AWS Pricing APIとは連携していない。

### 1.5 出力形式

| format | 内容 |
|---|---|
| `compact` | デフォルトの短いJSON |
| `terminal` | CLI向けの英語テキスト |
| `full` | 日本語詳細JSON |
| `markdown` | Markdown本文 |
| `ascii_json` | 日本語をUnicodeエスケープしたJSON文字列 |

## 2. 未実装・今後の候補

- AWS Pricing API連携
- Bedrockモデルによる自然文解析
- EC2/RDSインスタンスサイズ別見積もり
- Multi-AZ / Single-AZ の切り替え
- ALB / NAT Gateway / EBS / データ転送の詳細見積もり
- Markdown / JSON のS3保存
- Terraform構成案生成
- 見積もり履歴のMemory保存
