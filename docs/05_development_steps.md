# AgentCore 見積エージェント 開発手順

## 1. 現在の到達点

AgentCore Runtime へのデプロイと invoke は成功している。

現在のAgent ARN:

```text
arn:aws:bedrock-agentcore:ap-northeast-1:950473446046:runtime/estimate_agent-hYssgJD8iA
```

実行ロール:

```text
arn:aws:iam::950473446046:role/AmazonBedrockAgentCoreRuntime-estimate_agent
```

## 2. ローカル実装

エージェント本体:

```text
src/agent/agent_example.py
```

依存関係:

```text
requirements.txt
```

現在必要なPythonパッケージ:

```text
bedrock-agentcore
boto3
```

## 3. デプロイ

コードを変更したら以下を実行する。

```bash
agentcore deploy
```

## 4. 動作確認

CLIで読みやすい出力:

```bash
agentcore invoke '{"prompt": "月1000000リクエスト、50GB。Lambda API Gateway S3 DynamoDB CloudWatchで見積もり", "format": "terminal"}'
```

別構成の確認:

```bash
agentcore invoke '{"prompt": "EC2 1台、RDS、S3 100GBで月額見積もり", "format": "terminal"}'
```

詳細条件を指定した確認:

```bash
agentcore invoke '{"prompt": "EC2 2台、RDS、S3 100GBで月額見積もり", "format": "terminal", "ec2_instance": "t3.small", "ec2_count": 2, "rds_instance": "db.t4g.small", "rds_storage_gb": 50, "multi_az": true}'
```

詳細JSON:

```bash
agentcore invoke '{"prompt": "EC2 1台、RDS、S3 100GBで月額見積もり", "format": "full"}'
```

文字化け回避用:

```bash
agentcore invoke '{"prompt": "EC2 1台、RDS、S3 100GBで月額見積もり", "format": "ascii_json"}'
```

Foundation Modelを使う確認:

```bash
agentcore invoke '{"prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり。月50万アクセス", "format": "terminal", "use_fm": true}'
```

質問から始める確認:

```bash
agentcore invoke '{"mode": "clarify", "prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり", "format": "terminal", "use_fm": true}'
```

質問への回答を渡して見積もる確認:

```bash
agentcore invoke '{"mode": "estimate", "prompt": "小規模な社内向けWebアプリ。ログインあり、画像保存、管理画面あり", "format": "terminal", "use_fm": true, "answers": {"monthly_requests": 500000, "storage_gb": 100, "data_transfer_gb": 300, "lambda_memory_mb": 1024, "lambda_duration_ms": 800, "users": 1000}}'
```

モデルを明示する場合:

```bash
agentcore invoke '{"prompt": "ログインありの画像投稿Webアプリを見積もり", "format": "full", "use_fm": true, "model_id": "apac.amazon.nova-micro-v1:0"}'
```

## 5. ログ確認

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/estimate_agent-hYssgJD8iA-DEFAULT \
  --log-stream-name-prefix "2026/05/16/[runtime-logs]" \
  --follow
```

## 6. CLI表示の注意

AgentCore CLIはレスポンスをJSON文字列として表示するため、改行は `\n` として表示される。

日本語を含む長いJSONは、ターミナルやコピー時に一部文字化けすることがある。そのためCLI確認では `format=terminal` を推奨する。

## 7. IAMメモ

デプロイユーザー `thippi888` には以下の権限が必要。

- ECR push/pull
- CodeBuild実行
- `bedrock-agentcore:*`
- AgentCore実行ロールへの `iam:PassRole`

AgentCore Runtime用の実行ロールには以下が必要。

- ECRイメージ取得
- CloudWatch Logs書き込み
- Bedrockモデル呼び出し

FM利用時に `AccessDeniedException` が出る場合は、Runtime実行ロールに `bedrock:InvokeModel` が付いていること、対象モデルの利用が有効になっていることを確認する。

`Invocation of model ID amazon.nova-micro-v1:0 with on-demand throughput isn't supported` が出る場合は、直指定モデルIDではなくInference Profile ID `apac.amazon.nova-micro-v1:0` を使う。
