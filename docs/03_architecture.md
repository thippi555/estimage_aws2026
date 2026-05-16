# AgentCore 見積エージェント アーキテクチャ設計

## 1. システム概要

本システムは Amazon Bedrock AgentCore を利用し、AWS構成やタスク内容に応じた見積支援を行うAIエージェントシステムである。

ユーザーが自然言語で依頼内容を入力し、AIエージェントが必要に応じてコード実行、ツール呼び出し、ファイル保存を行いながら結果を生成する。

初期構成では、コストを抑えた最小構成を採用する。

---

## 2. システム構成

```text
+----------------------+
| User                 |
| Web / CLI            |
+----------+-----------+
           |
           v
+----------------------+
| AgentCore Runtime    |
| AI Agent             |
+----------+-----------+
           |
           v
+----------------------+
| Foundation Model     |
| Claude / Nova        |
+----------+-----------+
           |
           +-------------------+
           |                   |
           v                   v
+----------------+   +----------------------+
| Code Interpreter|   | Lambda Tool         |
| Python Sandbox  |   | External Processing |
+----------------+   +----------------------+
           |
           v
+----------------------+
| S3 Storage           |
| JSON / Output Files  |
+----------------------+

## 3. 初期アーキテクチャ方針

初期段階では以下を重視する。

- 最小コスト
- 最小構成
- 動作確認優先
- 段階的拡張
- サーバーレス構成

そのため、以下は初期段階では利用しない。

- OpenSearch Serverless
- 大規模RAG
- 常時起動型Vector DB
- 複雑な認証基盤

---

## 4. Runtime構成

AgentCore Runtime 上で AI エージェントを実行する。

Runtime は以下を担当する。

- エージェント実行
- Foundation Model 呼び出し
- Tool実行
- セッション管理
- コンテナ分離実行

---

## 5. Foundation Model構成

初期構成では以下を候補とする。

| モデル | 用途 |
|---|---|
| Claude | 長文生成・設計支援 |
| Nova | コスト重視処理 |

モデル選定はコストと品質を見ながら切り替える。

---

## 6. Code Interpreter構成

Code Interpreter を利用し、以下を実施する。

- Pythonコード実行
- JSON整形
- 見積計算
- CSV生成
- draw.io補助生成
- Markdown生成

Code Interpreter はサンドボックス環境上で実行する。

---

## 7. S3構成

S3は以下用途で利用する。

| 用途 | 内容 |
|---|---|
| 出力保存 | Markdown / JSON |
| 一時ファイル | CSV / drawio |
| 軽量Memory | JSON履歴保存 |

初期段階ではS3のみ利用し、Vector DBは利用しない。

---

## 8. Lambda Tool構成

外部処理は Lambda Tool として実装する。

想定用途：

- AWS料金取得
- Terraform生成
- draw.io変換
- GitHub連携
- CSV処理

---

## 9. Memory構成

初期段階では軽量Memoryを採用する。

利用候補：

| 方式 | 用途 |
|---|---|
| S3 JSON | 会話履歴 |
| SQLite | ローカル保持 |
| DynamoDB | 将来拡張 |

初期段階では以下は利用しない。

- OpenSearch Serverless
- 大規模Vector DB
- 高頻度Embedding

---

## 10. Gateway構成

将来、外部APIやMCP連携が必要になった場合、Gatewayを追加する。

想定用途：

- 外部API連携
- MCP連携
- SaaS連携
- GitHub連携強化

---

## 11. Identity構成

将来的にユーザー管理が必要となった場合、Identityを追加する。

想定用途：

- 認証
- 認可
- JWT管理
- Cognito連携

---

## 12. ログ・監視構成

ログは CloudWatch Logs を利用する。

初期段階では最低限のログ出力とする。

出力対象：

- Runtimeログ
- Tool実行ログ
- Lambdaログ
- エラーログ

---

## 13. ディレクトリ構成

```text
estimate/
├── docs/
├── src/
├── terraform/
└── test/