#!/usr/bin/env python3
"""E2E check for NotebookLM file upload source_id/title/content mapping.

This script intentionally uses real NotebookLM APIs. It creates a temporary
notebook, uploads multiple markdown files in one add_files batch, waits for
indexing, and verifies each returned source_id points to the expected content
by both fulltext RPC and source-scoped chat.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from random import Random
from typing import Any

import httpx

from notebooklm import NotebookLMClient
from notebooklm.auth import (
    AuthTokens,
    extract_csrf_from_html,
    extract_session_id_from_html,
    load_auth_from_storage,
)

TOKENS = [
    ("alpha-orion.md", "NBLM-MAP-ALPHA-ORION", "朱色の灯台", "北東航路"),
    ("bravo-vega.md", "NBLM-MAP-BRAVO-VEGA", "青磁の橋", "南西市場"),
    ("charlie-sirius.md", "NBLM-MAP-CHARLIE-SIRIUS", "黒曜石の時計", "中央研究室"),
    ("delta-rigel.md", "NBLM-MAP-DELTA-RIGEL", "琥珀の庭", "沿岸倉庫"),
    ("echo-altair.md", "NBLM-MAP-ECHO-ALTAIR", "銀色の帆", "山麓工場"),
    ("foxtrot-deneb.md", "NBLM-MAP-FOXTROT-DENEB", "緑の磁針", "湾岸店舗"),
    ("golf-capella.md", "NBLM-MAP-GOLF-CAPELLA", "紫の帳簿", "都市物流"),
    ("hotel-polaris.md", "NBLM-MAP-HOTEL-POLARIS", "白い鍵", "湖畔拠点"),
]


async def load_auth(storage: str) -> AuthTokens:
    cookies = load_auth_from_storage(Path(storage))
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.get(
            "https://notebooklm.google.com/",
            headers={"Cookie": cookie_header},
            follow_redirects=True,
        )
        resp.raise_for_status()
        csrf = extract_csrf_from_html(resp.text)
        session_id = extract_session_id_from_html(resp.text)
    return AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)


def make_files(base_dir: Path, count: int) -> list[Path]:
    files = []
    for index, (filename, token, phrase, location) in enumerate(TOKENS[:count], 1):
        path = base_dir / filename
        path.write_text(
            "\n".join(
                [
                    f"# Source mapping E2E file {index}",
                    "",
                    f"検証コード: {token}",
                    f"固有フレーズ: {phrase}",
                    f"固有拠点: {location}",
                    "",
                    "このファイルはNotebookLM source_id対応付けのE2E検証専用です。",
                    "他のファイルとは検証コード、固有フレーズ、固有拠点が重複しません。",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files.append(path)
    return files


def order_files(files: list[Path], order: str) -> list[Path]:
    if order == "input":
        return files
    if order == "reverse":
        return list(reversed(files))
    if order == "shuffled":
        shuffled = list(files)
        Random(20260722).shuffle(shuffled)
        return shuffled
    raise ValueError(f"unsupported order: {order}")


def expected_by_title(count: int) -> dict[str, dict[str, str]]:
    return {
        filename: {"token": token, "phrase": phrase, "location": location}
        for filename, token, phrase, location in TOKENS[:count]
    }


def contains_all(text: str, expected: dict[str, str]) -> bool:
    return all(value in text for value in expected.values())


async def run(args: argparse.Namespace) -> dict[str, Any]:
    started_at = time.time()
    auth = await load_auth(args.storage)
    notebook_id: str | None = None
    notebook_title = f"codex-source-mapping-e2e-{int(started_at)}"

    report: dict[str, Any] = {
        "started_at": started_at,
        "notebook_title": notebook_title,
        "file_count": args.count,
        "file_order": args.order,
        "upload_concurrency": args.concurrency,
        "storage": args.storage,
        "checks": [],
        "deleted": False,
    }

    with tempfile.TemporaryDirectory(prefix="nblm-source-map-") as tmp:
        tmp_dir = Path(tmp)
        files = make_files(tmp_dir, args.count)
        files = order_files(files, args.order)
        expected = expected_by_title(args.count)

        async with NotebookLMClient(auth) as client:
            nb = await client.notebooks.create(notebook_title)
            notebook_id = nb.id
            report["notebook_id"] = notebook_id
            report["notebook_url"] = f"https://notebooklm.google.com/notebook/{notebook_id}"

            uploaded = await client.sources.add_files(
                notebook_id,
                files,
                concurrency=args.concurrency,
            )
            report["uploaded_sources"] = [
                {"id": source.id, "title": source.title} for source in uploaded
            ]

            source_ids = [source.id for source in uploaded]
            ready = await client.sources.wait_for_sources(
                notebook_id,
                source_ids,
                timeout=args.wait_timeout,
                initial_interval=2,
                max_interval=15,
            )
            report["ready_sources"] = [
                {"id": source.id, "title": source.title, "status": source.status}
                for source in ready
            ]

            try:
                listed = await client.sources.list(notebook_id)
                report["listed_sources"] = [
                    {"id": source.id, "title": source.title, "status": source.status}
                    for source in listed
                ]
            except Exception as exc:
                report["listed_sources_error"] = f"{type(exc).__name__}: {exc}"

            for source in uploaded:
                title = source.title or ""
                expectation = expected.get(title)
                check: dict[str, Any] = {
                    "source_id": source.id,
                    "title": title,
                    "expected": expectation,
                    "fulltext_ok": False,
                    "ask_ok": False,
                }
                if expectation is None:
                    check["error"] = "returned title is not one of uploaded filenames"
                    report["checks"].append(check)
                    continue

                fulltext = await client.sources.get_fulltext(notebook_id, source.id)
                check["fulltext"] = {
                    "title": fulltext.title,
                    "char_count": fulltext.char_count,
                    "contains_token": expectation["token"] in fulltext.content,
                    "contains_phrase": expectation["phrase"] in fulltext.content,
                    "contains_location": expectation["location"] in fulltext.content,
                }
                check["fulltext_ok"] = contains_all(fulltext.content, expectation)

                question = (
                    "このソースだけを使って、検証コード、固有フレーズ、固有拠点を"
                    "そのまま抜き出してください。説明は短くしてください。"
                )
                answer = await client.chat.ask(
                    notebook_id,
                    question,
                    source_ids=[source.id],
                )
                check["ask"] = {
                    "answer": answer.answer,
                    "conversation_id": answer.conversation_id,
                    "references": [asdict(ref) for ref in answer.references],
                }
                check["ask_ok"] = contains_all(answer.answer, expectation)
                report["checks"].append(check)

    report["all_fulltext_ok"] = all(check.get("fulltext_ok") for check in report["checks"])
    report["all_ask_ok"] = all(check.get("ask_ok") for check in report["checks"])
    report["success"] = report["all_fulltext_ok"] and report["all_ask_ok"]
    report["finished_at"] = time.time()
    report["elapsed_sec"] = round(report["finished_at"] - started_at, 3)

    if notebook_id and not args.keep_notebook:
        cleanup_auth = await load_auth(args.storage)
        async with NotebookLMClient(cleanup_auth) as cleanup_client:
            report["deleted"] = await cleanup_client.notebooks.delete(notebook_id)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage", default="/root/.notebooklm/storage_state.json")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--order", choices=["input", "reverse", "shuffled"], default="input")
    parser.add_argument("--wait-timeout", type=float, default=300)
    parser.add_argument("--keep-notebook", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.count < 1 or args.count > len(TOKENS):
        raise SystemExit(f"--count must be between 1 and {len(TOKENS)}")

    report = asyncio.run(run(args))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
