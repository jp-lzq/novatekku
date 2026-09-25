#!/usr/bin/env python3
"""Generate the language-specific /test Q&A snapshot through the live NOVA AI API."""

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


QUESTIONS = {
    "zh": [
        ("本地价格", "iPhone 17 Pro Max 256GB 当前哪三家回收价格最高？也告诉我有效均价。"),
        ("本地价格", "iPhone 17 Pro 256GB 现在最高回收价是哪家？前三家分别多少钱？"),
        ("本地价格", "iPhone 17 Pro Max 512GB 各店价格差距大吗？给我一个简单的卖出建议。"),
        ("本地价格", "iPhone 16 Pro 256GB 的本地回收价格和平均价怎么样？"),
        ("批量计算", "按当前最高回收价计算，iPhone 17 Pro Max 256GB 两台一共多少钱？"),
        ("数据迁移", "安卓手机换到 iPhone，微信、照片和通讯录应该按什么顺序迁移？"),
        ("电池", "安卓手机充满电半天就没电，应该先检查哪些地方？"),
        ("存储", "iPhone 提示存储空间已满，但我不想删照片，应该怎么办？"),
        ("充电", "手机突然不能快充了，怎样判断是充电器、线还是手机接口的问题？"),
        ("发热", "手机看视频时很烫，需要马上停用吗？哪些发热情况比较危险？"),
        ("二手机", "买二手 iPhone 时，现场最重要的十分钟应该检查什么？"),
        ("容量选择", "普通用户买手机选 256GB 还是 512GB？怎么根据使用习惯判断？"),
        ("出售准备", "把旧手机卖掉前，需要备份、退出和删除哪些内容？"),
        ("电池健康", "iPhone 电池健康度只剩 79%，应该换电池还是直接换手机？"),
        ("隐私安全", "手机丢了以后，前十分钟最应该做哪几件事？"),
        ("拍照", "手机拍照一直对不上焦，镜头擦过也没用，怎么继续排查？"),
        ("网络", "手机在家里 Wi-Fi 很慢，但电脑正常，可能是什么原因？"),
        ("防水", "手机换过屏幕后还能相信原来的防水等级吗？"),
        ("eSIM", "换新手机时 eSIM 一般怎么迁移？操作前要注意什么？"),
        ("选购", "给长辈选手机，除了屏幕大和声音大，还应该重点看什么？"),
    ],
    "ja": [
        ("ローカル価格", "iPhone 17 Pro Max 256GB の現在の買取上位3店舗と有効平均価格を教えてください。"),
        ("ローカル価格", "iPhone 17 Pro 512GB は今どの店舗が高いですか。店舗差も簡単に説明してください。"),
        ("ローカル価格", "iPhone 16 Pro Max 256GB を今日売るなら、NOVA の価格データではどこが候補ですか。"),
        ("一括計算", "iPhone 17 Pro 256GB を3台売る場合、現在の最高価格ベースの合計はいくらですか。"),
        ("LINE移行", "Android から iPhone へ変更するとき、LINE のトーク履歴を失わないための注意点は？"),
        ("交通系IC", "iPhoneを機種変更するとき、モバイルSuicaを安全に移す基本手順を教えてください。"),
        ("eSIM", "eSIMを使っているiPhoneを買い替える前に確認すべきことは何ですか。"),
        ("バッテリー", "iPhone のバッテリー最大容量が80%です。交換を考える目安を教えてください。"),
        ("発熱", "充電しながらゲームをすると本体が熱くなります。故障を避ける使い方はありますか。"),
        ("充電", "USB-Cケーブルを替えても充電が途切れます。自分でできる切り分け方法は？"),
        ("中古購入", "中古スマホを購入するとき、ネットワーク利用制限と赤ロムはどう確認しますか。"),
        ("売却準備", "iPhoneを買取店へ出す前に、探す機能・Apple ID・初期化はどの順番で行いますか。"),
        ("写真", "iCloud写真を使っています。機種変更時に写真が消えないか確認する方法は？"),
        ("容量", "写真と動画をよく撮る場合、256GBと512GBのどちらを選ぶべきですか。"),
        ("通信", "5G表示なのに通信が遅いとき、端末側で試せることを順番に教えてください。"),
        ("防水", "水没したスマホを乾かすために、米へ入れる方法は本当に有効ですか。"),
        ("紛失", "iPhoneを紛失した直後に、別の端末から行うべき操作を教えてください。"),
        ("通知", "Androidで通知が遅れてまとめて届く原因と設定の確認場所を教えてください。"),
        ("長期保管", "予備スマホを半年使わず保管するとき、電池を傷めない方法はありますか。"),
        ("家族向け", "高齢の家族向けスマホを選ぶとき、操作性と安全面で重視する点は何ですか。"),
    ],
    "en": [
        ("Local prices", "What are the top three local buyback offers and valid average for iPhone 17 Pro Max 256GB?"),
        ("Local prices", "Which store currently pays the most for iPhone 17 Pro 256GB, and how close are the next offers?"),
        ("Local prices", "Compare the local buyback market for iPhone 16 Pro 512GB and give a short selling recommendation."),
        ("Batch total", "Using the current best local offer, what is the total for two iPhone 17 Pro Max 512GB phones?"),
        ("Migration", "What is the safest order for moving contacts, photos, WhatsApp, and authenticator apps from Android to iPhone?"),
        ("Battery", "My Android phone loses half its battery overnight. What should I check first?"),
        ("Storage", "My iPhone storage is full, but most photos are already in iCloud. How can I free space safely?"),
        ("Charging", "My phone only charges at certain cable angles. How can I tell whether the port or cable is damaged?"),
        ("Heat", "When is smartphone heat normal, and what warning signs mean I should stop using it?"),
        ("Used phone", "What should I test during a ten-minute inspection before buying a used iPhone?"),
        ("Security", "What are the first actions to take after a phone is lost or stolen?"),
        ("Selling", "What accounts, payment cards, and security features must be removed before selling a phone?"),
        ("Camera", "Why does my phone camera keep hunting for focus even after I clean the lens?"),
        ("Wi-Fi", "My phone has slow Wi-Fi while my laptop is fast on the same network. How should I troubleshoot it?"),
        ("Water resistance", "Is a phone still water resistant after a screen or battery replacement?"),
        ("eSIM", "How should I prepare for transferring an eSIM to a new phone without losing service?"),
        ("Capacity", "How do I choose between 256GB and 512GB for a phone I plan to keep for four years?"),
        ("Backup", "How can I verify that a phone backup is complete before doing a factory reset?"),
        ("Performance", "Why can a phone feel slow even when it still has plenty of free storage?"),
        ("Family phone", "What features matter most when choosing a safe, simple smartphone for an older parent?"),
    ],
}


async def generate_case(client, semaphore, base_url, language, index, category, question):
    payload = {
        "session_id": f"test-page-{language}-{index}-{uuid.uuid4()}",
        "message": question,
        "language": language,
    }
    last_error = "unknown error"
    for attempt in range(3):
        try:
            async with semaphore:
                response = await client.post(f"{base_url.rstrip('/')}/api/v1/ai/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            print(f"[{language} {index:02d}/20] complete", flush=True)
            return {
                "id": index,
                "category": category,
                "question": question,
                "answer": str(data.get("reply") or "").strip(),
            }
        except Exception as exc:
            last_error = str(exc)
            await asyncio.sleep(2 ** attempt)
    print(f"[{language} {index:02d}/20] failed: {last_error}", flush=True)
    return {"id": index, "category": category, "question": question, "answer": f"Generation failed: {last_error}"}


async def main_async(base_url: str, output: Path, concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=260) as client:
        tasks = [
            generate_case(client, semaphore, base_url, language, index, category, question)
            for language, entries in QUESTIONS.items()
            for index, (category, question) in enumerate(entries, start=1)
        ]
        results = await asyncio.gather(*tasks)

    grouped = {language: [] for language in QUESTIONS}
    cursor = 0
    for language, entries in QUESTIONS.items():
        grouped[language] = results[cursor:cursor + len(entries)]
        cursor += len(entries)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-5.6-terra",
        "reasoningEffort": "medium",
        "cases": grouped,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [case for cases in grouped.values() for case in cases if case["answer"].startswith("Generation failed:")]
    print(f"Wrote {sum(len(items) for items in grouped.values())} cases to {output}", flush=True)
    if failures:
        raise SystemExit(f"{len(failures)} cases failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://ai.novatekku.com")
    parser.add_argument("--output", type=Path, default=Path("frontend/src/data/aiTestCases.json"))
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(main_async(args.base_url, args.output, max(1, min(args.concurrency, 6))))


if __name__ == "__main__":
    main()
