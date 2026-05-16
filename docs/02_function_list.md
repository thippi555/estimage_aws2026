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
| `cognito` | Amazon Cognito | cognito, ログイン, 認証 |
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
| `data_transfer_gb` | `storage_gb` と同じ | CloudFront等の月間データ転送量 |
| `lambda_memory_mb` | `512` | Lambdaメモリ |
| `lambda_duration_ms` | `500` | Lambda平均実行時間 |
| `ec2_instance` | `t3.micro` | EC2インスタンスタイプ |
| `ec2_count` | `1` | EC2台数 |
| `rds_instance` | `db.t4g.micro` | RDSインスタンスタイプ |
| `rds_storage_gb` | `20` | RDSストレージ容量 |
| `multi_az` | `false` | RDS Multi-AZ構成 |

JSONで明示された値は自然文から抽出した値より優先する。

### 1.4 概算見積もり

`src/agent/agent_example.py` 内の簡易単価表を使って月額を算出する。

現段階ではラフ見積もりであり、AWS Pricing APIとは連携していない。

EC2、RDS、Lambda、CloudFrontは詳細条件を一部反映する。

| サービス | 反映する条件 |
|---|---|
| Lambda | `monthly_requests`, `lambda_memory_mb`, `lambda_duration_ms` |
| EC2 | `ec2_instance`, `ec2_count` |
| RDS | `rds_instance`, `rds_storage_gb`, `multi_az` |
| CloudFront | `data_transfer_gb` |

### 1.5 不足情報の質問生成

検出されたサービスに応じて、追加確認したい項目を返す。

例:

- S3がある場合: 保存容量
- CloudFrontがある場合: 月間データ転送量
- Lambdaがある場合: メモリ、平均実行時間
- EC2がある場合: インスタンスタイプ、台数
- RDSがある場合: インスタンスタイプ、ストレージ容量、Multi-AZ有無
- Cognitoがある場合: 月間アクティブユーザー数

### 1.6 Foundation Modelによる構成抽出

`use_fm=true` を指定した場合、Amazon BedrockのFoundation Modelを呼び出して、自然文からサービス一覧と規模情報をJSONとして抽出する。

FMの役割は料金計算ではなく、以下の補助である。

- 曖昧な自然文からAWSサービス候補を補完する
- 「ログインあり」からCognitoなどを推定する
- 月間アクセス数や保存容量を構造化する
- 抽出できない値は `null` として扱う

FM呼び出しに失敗した場合は、従来のルールベース検出にフォールバックする。

デフォルトモデルはAPACのInference Profile ID `apac.amazon.nova-micro-v1:0` で、`model_id` または環境変数 `BEDROCK_MODEL_ID` で変更できる。

### 1.7 出力形式

| format | 内容 |
|---|---|
| `compact` | デフォルトの短いJSON |
| `terminal` | CLI向けの英語テキスト |
| `full` | 日本語詳細JSON |
| `markdown` | Markdown本文 |
| `ascii_json` | 日本語をUnicodeエスケープしたJSON文字列 |

## 2. 未実装・今後の候補

- AWS Pricing API連携
- Bedrockモデルによる自然文解析の精度改善
- EC2/RDSインスタンスサイズ別見積もり
- Multi-AZ / Single-AZ の切り替え
- ALB / NAT Gateway / EBS / データ転送の詳細見積もり
- Markdown / JSON のS3保存
- Terraform構成案生成
- 見積もり履歴のMemory保存
