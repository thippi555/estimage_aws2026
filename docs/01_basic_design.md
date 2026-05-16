# AgentCore 見積エージェント 基本設計書

## 1. 目的

Amazon Bedrock AgentCore を利用し、AWS構成やタスク内容に応じた見積支援を行うAIエージェントを構築する。

## 2. 開発方針

個人開発であるため、コストを抑えた最小構成から開始する。

構築順序は以下とする。

1. AgentCore Runtime
2. Code Interpreter
3. S3保存
4. Lambda Tool
5. 軽量Memory
6. Gateway
7. Identity

## 3. 初期スコープ

初期スコープでは、Runtime と Code Interpreter を中心に、AIエージェントが入力内容を処理し、必要に応じてコード実行を行える構成を作成する。

## 4. コスト方針

OpenSearch Serverless など常時課金が発生しやすい構成は初期段階では利用しない。

Memory は当初、S3 JSON またはローカルファイルによる軽量管理とする。

## 5. ディレクトリ構成

```text
estimate/
├── docs/
├── src/
├── terraform/
└── test/