from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp


app = BedrockAgentCoreApp()


HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class ServiceEstimate:
    service: str
    description: str
    monthly_usd: float
    assumptions: list[str]


SERVICE_HINTS = {
    "lambda": ["lambda", "ラムダ", "serverless", "サーバーレス"],
    "api_gateway": ["api gateway", "apigateway", "api gw", "rest api", "http api"],
    "s3": ["s3", "bucket", "バケット", "storage", "ストレージ"],
    "dynamodb": ["dynamodb", "dynamo", "nosql"],
    "rds": ["rds", "postgres", "postgresql", "mysql", "mariadb"],
    "ecs_fargate": ["ecs", "fargate", "コンテナ", "container"],
    "ec2": ["ec2", "instance", "インスタンス", "vm"],
    "cloudfront": ["cloudfront", "cdn"],
    "bedrock": ["bedrock", "claude", "nova", "llm", "生成ai", "生成 ai"],
    "cloudwatch": ["cloudwatch", "logs", "ログ", "監視"],
}


def normalize_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt") or payload.get("message") or payload.get("text") or ""
    if isinstance(prompt, str):
        return prompt.strip()
    return json.dumps(prompt, ensure_ascii=False)


def parse_scale(prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    text = prompt.lower()
    users = _first_int(text, [r"(\d[\d,]*)\s*(?:users|user|ユーザー|人)"], 100)
    requests = _first_int(
        text,
        [
            r"(\d[\d,]*)\s*(?:requests|request|req|リクエスト)",
            r"月\s*(\d[\d,]*)\s*(?:回|件)",
        ],
        100_000,
    )
    storage_gb = _first_int(text, [r"(\d[\d,]*)\s*(?:gb|ギガ)"], 20)

    return {
        "region": payload.get("region", "ap-northeast-1"),
        "users": int(payload.get("users", users)),
        "monthly_requests": int(payload.get("monthly_requests", requests)),
        "storage_gb": int(payload.get("storage_gb", storage_gb)),
        "currency": payload.get("currency", "USD"),
    }


def _first_int(text: str, patterns: list[str], default: int) -> int:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return default


def detect_services(prompt: str, payload: dict[str, Any]) -> list[str]:
    explicit = payload.get("services")
    if isinstance(explicit, list) and explicit:
        return [str(service).strip().lower() for service in explicit if str(service).strip()]

    text = prompt.lower()
    detected = [
        service
        for service, hints in SERVICE_HINTS.items()
        if any(hint in text for hint in hints)
    ]

    if detected:
        return detected

    return ["lambda", "api_gateway", "s3", "cloudwatch"]


def estimate_services(services: list[str], scale: dict[str, Any]) -> list[ServiceEstimate]:
    requests_million = scale["monthly_requests"] / 1_000_000
    storage_gb = scale["storage_gb"]
    users = scale["users"]
    estimates: list[ServiceEstimate] = []

    for service in services:
        if service in {"lambda", "aws lambda"}:
            estimates.append(
                ServiceEstimate(
                    "AWS Lambda",
                    "API/バッチ処理用のサーバーレス実行基盤",
                    max(0.20, requests_million * 0.20 + requests_million * 0.35),
                    [
                        "平均実行時間 500ms、メモリ 512MB の軽量処理を想定",
                        "無料枠やSavings Plansは考慮外",
                    ],
                )
            )
        elif service in {"api_gateway", "api gateway", "apigateway"}:
            estimates.append(
                ServiceEstimate(
                    "Amazon API Gateway",
                    "外部/フロントエンドからのHTTP API受付",
                    max(1.00, requests_million * 1.20),
                    ["HTTP API相当の単価感で概算", "データ転送量は小さい前提"],
                )
            )
        elif service in {"s3", "amazon s3"}:
            estimates.append(
                ServiceEstimate(
                    "Amazon S3",
                    "成果物・JSON・一時ファイル保存",
                    max(0.50, storage_gb * 0.025 + requests_million * 0.40),
                    [f"保存容量 {storage_gb}GB を想定", "ライフサイクル/Glacier移行は未考慮"],
                )
            )
        elif service in {"dynamodb", "dynamo"}:
            estimates.append(
                ServiceEstimate(
                    "Amazon DynamoDB",
                    "軽量な状態管理・履歴管理",
                    max(1.00, requests_million * 1.50 + users * 0.002),
                    ["オンデマンド課金を想定", "小さなアイテムサイズを前提"],
                )
            )
        elif service in {"rds", "postgres", "postgresql", "mysql"}:
            estimates.append(
                ServiceEstimate(
                    "Amazon RDS",
                    "リレーショナルDB",
                    35.00,
                    ["小型シングルAZ構成を想定", "ストレージ20GB程度、バックアップ最小"],
                )
            )
        elif service in {"ecs_fargate", "ecs", "fargate"}:
            estimates.append(
                ServiceEstimate(
                    "Amazon ECS on Fargate",
                    "常時稼働コンテナ",
                    28.00,
                    ["0.25 vCPU / 0.5GB タスク1個の常時稼働を想定", "ALB費用は別途"],
                )
            )
        elif service == "ec2":
            estimates.append(
                ServiceEstimate(
                    "Amazon EC2",
                    "仮想サーバー",
                    18.00,
                    ["小型インスタンス1台の常時稼働を想定", "EBS 20GB程度を含む概算"],
                )
            )
        elif service == "cloudfront":
            estimates.append(
                ServiceEstimate(
                    "Amazon CloudFront",
                    "CDN配信",
                    max(1.00, storage_gb * 0.12 + requests_million * 0.75),
                    ["日本/アジア向け少量配信を想定", "大容量動画配信は別見積もり"],
                )
            )
        elif service == "bedrock":
            estimates.append(
                ServiceEstimate(
                    "Amazon Bedrock",
                    "LLM推論",
                    max(3.00, requests_million * 12.00),
                    ["軽量モデル/短文入出力の概算", "Claude等の大きなモデルでは増額"],
                )
            )
        elif service == "cloudwatch":
            estimates.append(
                ServiceEstimate(
                    "Amazon CloudWatch",
                    "ログ保存・メトリクス監視",
                    max(1.00, requests_million * 0.80 + storage_gb * 0.03),
                    ["ログ保持30日程度を想定", "詳細メトリクス/アラーム多数は別途"],
                )
            )

    return estimates


def build_response(prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    scale = parse_scale(prompt, payload)
    services = detect_services(prompt, payload)
    estimates = estimate_services(services, scale)
    total = round(sum(item.monthly_usd for item in estimates), 2)

    line_items = [
        {
            "service": item.service,
            "description": item.description,
            "monthly_usd": round(item.monthly_usd, 2),
            "assumptions": item.assumptions,
        }
        for item in estimates
    ]

    response = {
        "summary": {
            "title": "AWS構成の概算見積もり",
            "monthly_total_usd": total,
            "monthly_total_jpy_reference": round(total * 155),
            "currency_note": "JPYは 1 USD = 155 JPY の参考換算です。実請求額はAWS料金・為替・税で変動します。",
        },
        "input": {
            "prompt": prompt,
            "scale": scale,
            "detected_services": services,
        },
        "line_items": line_items,
        "assumptions": [
            "初期PoC/個人開発向けの低コスト構成として概算しています。",
            "AWS公式料金APIではなく、エージェント内の簡易単価表によるラフ見積もりです。",
            "データ転送、税、サポート料金、無料枠、割引プランは詳細計算していません。",
        ],
        "questions": [
            "月間リクエスト数を教えてください。",
            "保存データ量とログ保持期間はどのくらいですか？",
            "常時稼働が必要ですか、それともリクエスト時のみ動けばよいですか？",
        ],
        "next_actions": [
            "サービスごとの利用量を入力して再見積もりする",
            "本番/検証/開発環境を分けた見積もりにする",
            "Terraform構成案とあわせて費用表を作る",
        ],
    }
    response["markdown"] = render_markdown(response)
    return response


def render_markdown(response: dict[str, Any]) -> str:
    summary = response["summary"]
    scale = response["input"]["scale"]
    lines = [
        f"# {summary['title']}",
        "",
        f"- 月額概算: ${summary['monthly_total_usd']}",
        f"- 参考円換算: {summary['monthly_total_jpy_reference']:,}円/月",
        f"- リージョン: {scale['region']}",
        f"- 月間リクエスト: {scale['monthly_requests']:,}",
        f"- 保存容量: {scale['storage_gb']:,}GB",
        "",
        "## 明細",
    ]

    for item in response["line_items"]:
        lines.extend(
            [
                f"- {item['service']}: ${item['monthly_usd']}",
                f"  - {item['description']}",
            ]
        )

    lines.extend(["", "## 前提"])
    lines.extend([f"- {item}" for item in response["assumptions"]])

    lines.extend(["", "## 確認したいこと"])
    lines.extend([f"- {item}" for item in response["questions"]])

    lines.extend(["", "## 次のアクション"])
    lines.extend([f"- {item}" for item in response["next_actions"]])

    return "\n".join(lines)


@app.entrypoint
def estimate_agent(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = normalize_prompt(payload)
    if not prompt:
        prompt = "Lambda, API Gateway, S3 を使った小規模なWeb API"

    response = build_response(prompt, payload)
    output_format = str(payload.get("format", "compact")).lower()

    if output_format == "full":
        return response
    if output_format == "markdown":
        return {"message": response["markdown"]}
    if output_format == "terminal":
        return {"message": render_terminal_text(response)}
    if output_format == "ascii_json":
        return {"json": json.dumps(response, ensure_ascii=True)}

    return compact_response(response)


def compact_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "message": (
            "Estimate ready. "
            f"Monthly total: ${response['summary']['monthly_total_usd']} "
            f"(about {response['summary']['monthly_total_jpy_reference']:,} JPY). "
            "Use format=full for Japanese details, or format=ascii_json if your terminal garbles Japanese."
        ),
        "summary": {
            "monthly_total_usd": response["summary"]["monthly_total_usd"],
            "monthly_total_jpy_reference": response["summary"]["monthly_total_jpy_reference"],
            "note": "JPY uses a rough 155 JPY/USD conversion.",
        },
        "line_items": [
            {
                "service": item["service"],
                "monthly_usd": item["monthly_usd"],
            }
            for item in response["line_items"]
        ],
        "input": {
            "scale": response["input"]["scale"],
            "detected_services": response["input"]["detected_services"],
        },
        "formats": ["compact", "terminal", "full", "markdown", "ascii_json"],
    }


def render_terminal_text(response: dict[str, Any]) -> str:
    summary = response["summary"]
    scale = response["input"]["scale"]
    lines = [
        "AWS estimate",
        "",
        f"Monthly total: ${summary['monthly_total_usd']}",
        f"JPY reference: {summary['monthly_total_jpy_reference']:,} JPY/month",
        f"Region: {scale['region']}",
        f"Monthly requests: {scale['monthly_requests']:,}",
        f"Storage: {scale['storage_gb']:,} GB",
        "",
        "Line items:",
    ]

    for item in response["line_items"]:
        lines.append(f"- {item['service']}: ${item['monthly_usd']}")

    lines.extend(
        [
            "",
            "Notes:",
            "- Rough estimate for an initial PoC or small personal project.",
            "- Uses a simple built-in price table, not the AWS Pricing API.",
            "- Data transfer, tax, support, free tier, and discounts are not fully calculated.",
            "",
            "Next:",
            "- Provide exact usage numbers for each service.",
            "- Split the estimate into prod, staging, and dev environments.",
            "- Generate a Terraform plan and a cost table together.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    app.run()
