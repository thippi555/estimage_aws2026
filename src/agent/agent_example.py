from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp


app = BedrockAgentCoreApp()


HOURS_PER_MONTH = 730

EC2_MONTHLY_USD = {
    "t3.micro": 8.50,
    "t3.small": 17.00,
    "t3.medium": 34.00,
    "t4g.micro": 7.00,
    "t4g.small": 14.00,
    "t4g.medium": 28.00,
}

RDS_MONTHLY_USD = {
    "db.t4g.micro": 18.00,
    "db.t4g.small": 36.00,
    "db.t3.micro": 20.00,
    "db.t3.small": 40.00,
}


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
    "cognito": ["cognito", "ログイン", "認証", "authentication", "auth"],
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
            r"(\d[\d,]*)\s*万\s*(?:access|アクセス|requests|request|req|リクエスト)",
            r"月\s*(\d[\d,]*)\s*(?:回|件)",
            r"月\s*(\d[\d,]*)\s*万\s*(?:access|アクセス|requests|request|req|リクエスト|回|件)",
        ],
        100_000,
    )
    storage_gb = _first_int(text, [r"(\d[\d,]*)\s*(?:gb|ギガ)"], 20)

    return {
        "region": payload.get("region", "ap-northeast-1"),
        "users": int(payload.get("users", users)),
        "monthly_requests": int(payload.get("monthly_requests", requests)),
        "storage_gb": int(payload.get("storage_gb", storage_gb)),
        "data_transfer_gb": int(payload.get("data_transfer_gb", storage_gb)),
        "log_retention_days": int(payload.get("log_retention_days", 30)),
        "lambda_memory_mb": int(payload.get("lambda_memory_mb", 512)),
        "lambda_duration_ms": int(payload.get("lambda_duration_ms", 500)),
        "ec2_instance": str(payload.get("ec2_instance", "t3.micro")),
        "ec2_count": int(payload.get("ec2_count", 1)),
        "rds_instance": str(payload.get("rds_instance", "db.t4g.micro")),
        "rds_storage_gb": int(payload.get("rds_storage_gb", 20)),
        "multi_az": parse_bool(payload.get("multi_az", False)),
        "currency": payload.get("currency", "USD"),
    }


def _first_int(text: str, patterns: list[str], default: int) -> int:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1).replace(",", ""))
            if "万" in match.group(0):
                value *= 10_000
            return value
    return default


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on", "あり", "有り"}


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


def extract_with_fm(prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    import boto3

    model_id = str(payload.get("model_id") or os.getenv("BEDROCK_MODEL_ID") or "apac.amazon.nova-micro-v1:0")
    region = str(payload.get("region") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-1")
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": build_extraction_prompt(prompt)}],
            }
        ],
        inferenceConfig={
            "maxTokens": 600,
            "temperature": 0.0,
        },
    )
    text = response["output"]["message"]["content"][0]["text"]
    result = parse_json_object(text)
    result["model_id"] = model_id
    return result


def build_extraction_prompt(prompt: str) -> str:
    allowed_services = ", ".join(SERVICE_HINTS.keys())
    return f"""
You extract AWS estimate inputs from a user's request.
Return only one JSON object. Do not wrap it in Markdown.

Allowed services:
{allowed_services}

Schema:
{{
  "services": ["service_key"],
  "scale": {{
    "users": number | null,
    "monthly_requests": number | null,
    "storage_gb": number | null,
    "data_transfer_gb": number | null,
    "ec2_count": number | null,
    "ec2_instance": "instance-type" | null,
    "rds_instance": "db-instance-type" | null,
    "rds_storage_gb": number | null,
    "multi_az": boolean | null,
    "region": "aws-region" | null
  }},
  "notes": ["short reason"]
}}

Rules:
- Use only allowed service keys.
- Infer likely services from vague descriptions when helpful.
- Use null when the quantity is unknown.
- Do not calculate prices.

User request:
{prompt}
""".strip()


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def should_use_fm(payload: dict[str, Any]) -> bool:
    value = payload.get("use_fm", os.getenv("ESTIMATE_USE_FM", "false"))
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def merge_fm_extraction(
    payload: dict[str, Any],
    services: list[str],
    scale: dict[str, Any],
    extraction: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    fm_services = extraction.get("services")
    if isinstance(fm_services, list):
        normalized = [
            service
            for service in (normalize_service_key(item) for item in fm_services)
            if service
        ]
        if normalized:
            services = list(dict.fromkeys(normalized))

    fm_scale = extraction.get("scale")
    if isinstance(fm_scale, dict):
        for key in (
            "users",
            "monthly_requests",
            "storage_gb",
            "data_transfer_gb",
            "ec2_count",
            "ec2_instance",
            "rds_instance",
            "rds_storage_gb",
            "multi_az",
            "region",
        ):
            if key in payload:
                continue
            value = fm_scale.get(key)
            if value not in (None, ""):
                if key == "multi_az":
                    scale[key] = parse_bool(value)
                elif key in {"region", "ec2_instance", "rds_instance"}:
                    scale[key] = str(value)
                else:
                    scale[key] = int(value)

    return services, scale


def normalize_service_key(value: Any) -> str | None:
    service = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "api_gw": "api_gateway",
        "apigateway": "api_gateway",
        "aws_lambda": "lambda",
        "amazon_s3": "s3",
        "amazon_dynamodb": "dynamodb",
        "amazon_rds": "rds",
        "amazon_ec2": "ec2",
        "fargate": "ecs_fargate",
        "ecs": "ecs_fargate",
        "amazon_cloudfront": "cloudfront",
        "amazon_bedrock": "bedrock",
        "amazon_cognito": "cognito",
        "amazon_cloudwatch": "cloudwatch",
    }
    service = aliases.get(service, service)
    if service in SERVICE_HINTS:
        return service
    return None


def estimate_services(services: list[str], scale: dict[str, Any]) -> list[ServiceEstimate]:
    requests_million = scale["monthly_requests"] / 1_000_000
    storage_gb = scale["storage_gb"]
    users = scale["users"]
    estimates: list[ServiceEstimate] = []

    for service in services:
        if service in {"lambda", "aws lambda"}:
            compute_gb_seconds = (
                scale["monthly_requests"]
                * (scale["lambda_duration_ms"] / 1000)
                * (scale["lambda_memory_mb"] / 1024)
            )
            monthly = max(0.20, requests_million * 0.20 + compute_gb_seconds * 0.0000166667)
            estimates.append(
                ServiceEstimate(
                    "AWS Lambda",
                    "API/バッチ処理用のサーバーレス実行基盤",
                    monthly,
                    [
                        f"平均実行時間 {scale['lambda_duration_ms']}ms、メモリ {scale['lambda_memory_mb']}MB を想定",
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
            instance = str(scale["rds_instance"])
            instance_monthly = RDS_MONTHLY_USD.get(instance, RDS_MONTHLY_USD["db.t4g.micro"])
            storage_monthly = scale["rds_storage_gb"] * 0.12
            multi_az_multiplier = 2 if scale["multi_az"] else 1
            monthly = (instance_monthly + storage_monthly) * multi_az_multiplier
            estimates.append(
                ServiceEstimate(
                    "Amazon RDS",
                    "リレーショナルDB",
                    monthly,
                    [
                        f"{instance}、{scale['rds_storage_gb']}GBストレージを想定",
                        "Multi-AZ構成" if scale["multi_az"] else "Single-AZ構成",
                    ],
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
            instance = str(scale["ec2_instance"])
            instance_monthly = EC2_MONTHLY_USD.get(instance, EC2_MONTHLY_USD["t3.micro"])
            monthly = instance_monthly * scale["ec2_count"] + 2.00
            estimates.append(
                ServiceEstimate(
                    "Amazon EC2",
                    "仮想サーバー",
                    monthly,
                    [
                        f"{instance} x {scale['ec2_count']}台の常時稼働を想定",
                        "EBS 20GB程度を含む概算",
                    ],
                )
            )
        elif service == "cloudfront":
            estimates.append(
                ServiceEstimate(
                    "Amazon CloudFront",
                    "CDN配信",
                    max(1.00, scale["data_transfer_gb"] * 0.12 + requests_million * 0.75),
                    [f"月間データ転送 {scale['data_transfer_gb']}GB を想定", "大容量動画配信は別見積もり"],
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
        elif service == "cognito":
            estimates.append(
                ServiceEstimate(
                    "Amazon Cognito",
                    "ログイン・ユーザー認証",
                    max(0.00, (users - 50_000) * 0.0055),
                    ["月間アクティブユーザー 50,000 以内は低コスト想定", "高度なセキュリティ機能は未考慮"],
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


def build_questions(services: list[str], scale: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    questions: list[str] = []

    if "monthly_requests" not in payload and scale["monthly_requests"] == 100_000:
        questions.append("月間リクエスト数または月間アクセス数はどのくらいですか？")

    if "s3" in services and "storage_gb" not in payload and scale["storage_gb"] == 20:
        questions.append("S3に保存するデータ量は何GB程度ですか？")

    if "cloudfront" in services and "data_transfer_gb" not in payload:
        questions.append("CloudFrontの月間データ転送量は何GB程度ですか？")

    if "lambda" in services:
        if "lambda_memory_mb" not in payload:
            questions.append("Lambdaの想定メモリは何MBですか？")
        if "lambda_duration_ms" not in payload:
            questions.append("Lambdaの平均実行時間は何ms程度ですか？")

    if "ec2" in services:
        if "ec2_instance" not in payload and scale["ec2_instance"] == "t3.micro":
            questions.append("EC2のインスタンスタイプは何を想定しますか？")
        if "ec2_count" not in payload and scale["ec2_count"] == 1:
            questions.append("EC2は何台必要ですか？")

    if "rds" in services:
        if "rds_instance" not in payload and scale["rds_instance"] == "db.t4g.micro":
            questions.append("RDSのインスタンスタイプは何を想定しますか？")
        if "rds_storage_gb" not in payload and scale["rds_storage_gb"] == 20:
            questions.append("RDSのストレージ容量は何GB必要ですか？")
        if "multi_az" not in payload:
            questions.append("RDSはMulti-AZ構成にしますか？")

    if "cognito" in services and "users" not in payload:
        questions.append("月間アクティブユーザー数は何人程度ですか？")

    if not questions:
        questions.append("本番/検証/開発環境を分けて見積もりますか？")

    return questions[:6]


def build_response(prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    scale = parse_scale(prompt, payload)
    services = detect_services(prompt, payload)
    fm_info: dict[str, Any] = {"enabled": False}

    if should_use_fm(payload):
        fm_info["enabled"] = True
        try:
            extraction = extract_with_fm(prompt, payload)
            services, scale = merge_fm_extraction(payload, services, scale, extraction)
            fm_info.update(
                {
                    "status": "used",
                    "model_id": extraction.get("model_id"),
                    "notes": extraction.get("notes", []),
                }
            )
        except Exception as exc:
            fm_info.update(
                {
                    "status": "fallback",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

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
            "fm": fm_info,
        },
        "line_items": line_items,
        "assumptions": [
            "初期PoC/個人開発向けの低コスト構成として概算しています。",
            "AWS公式料金APIではなく、エージェント内の簡易単価表によるラフ見積もりです。",
            "データ転送、税、サポート料金、無料枠、割引プランは詳細計算していません。",
        ],
        "questions": build_questions(services, scale, payload),
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
            "fm": response["input"]["fm"],
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
