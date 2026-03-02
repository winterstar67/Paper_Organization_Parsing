#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5_abs_summary.py
GPT-5-nano based abstract summary generation

Description:
    Phase 5: Generates a concise 2-3 sentence summary per paper using GPT-5-nano.
    Reads Title and Abstract from Phase 4 organ_integrate.csv,
    inserts abs_llm_summary column immediately to the right of Authors,
    and saves the result to Phase_5/5_abs_summary.csv.

    This step runs between Phase 4 (organ_integrate) and Phase 6 (gmail_sending).
    gmail_sending.py will prefer this file over organ_integrate.csv when present.
"""

import asyncio
import os
import pandas as pd
import dotenv
import time
from typing import Dict

from openai import OpenAI
from pipeline_config import results_dir

dotenv.load_dotenv()

MODEL = "gpt-5-nano"
MAX_CONCURRENCY = max(1, int(os.getenv("ABS_SUMMARY_CONCURRENCY", "5")))

SYSTEM_PROMPT = (
    "You are a research assistant. "
    "Summarize the given paper in 2-3 concise sentences. "
    "Focus on the key problem, the proposed method, and the main result or contribution. "
    "Be factual and avoid filler phrases."
)


def get_gpt5_minimal_settings(model: str) -> Dict:
    """Return extra kwargs for GPT-5-nano to minimize cost and latency."""
    if model and model.startswith("gpt-5-nano"):
        return {
            "reasoning": {"effort": "minimal"},
            "text": {"verbosity": "low"},
        }
    return {}


async def call_with_timeout_retry(factory, timeout: int, retries: int, label: str):
    """
    Call an async factory with timeout and retry logic.

    Input:
        - factory: callable returning a coroutine (e.g. lambda: asyncio.to_thread(...))
        - timeout: seconds before TimeoutError per attempt
        - retries: number of additional attempts after first failure
        - label: string identifier for log messages

    Output:
        - result of the successful coroutine call

    Raises:
        - last exception if all attempts fail
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(factory(), timeout=timeout)
        except asyncio.TimeoutError as e:
            last_exc = e
            if attempt < retries:
                print(f"  [{label}] Timeout (attempt {attempt + 1}/{retries + 1}), retrying...")
        except Exception as e:
            last_exc = e
            if attempt < retries:
                print(f"  [{label}] Error: {e} (attempt {attempt + 1}/{retries + 1}), retrying...")
    raise last_exc


class AbstractSummarizer:
    """Wraps GPT-5-nano Responses API calls for paper abstract summarization."""

    def __init__(self):
        self.model = MODEL
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")
        self.client = OpenAI(api_key=api_key)

    async def summarize(self, title: str, abstract: str, label: str = "abs_summary") -> str:
        """
        Generate a concise summary for a single paper.

        Input:
            - title: str - Paper title
            - abstract: str - Paper abstract

        Output:
            - summary: str - 2-3 sentence summary, empty string on failure
        """
        user_prompt = f"Title: {title}\n\nAbstract: {abstract}"

        completion = await call_with_timeout_retry(
            lambda: asyncio.to_thread(
                self.client.responses.create,
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=user_prompt,
                **get_gpt5_minimal_settings(self.model)
            ),
            timeout=10, retries=2, label=label
        )

        return completion.output_text.strip()


async def generate_summaries(
    df: pd.DataFrame,
    summarizer: AbstractSummarizer,
    max_concurrency: int = MAX_CONCURRENCY
) -> list:
    """
    Generate summaries for all rows in df.

    Input:
        - df: pd.DataFrame - Must contain 'Title' and 'Abstract' columns
        - summarizer: AbstractSummarizer

    Output:
        - summaries: list[str] - One summary per row, empty string on skip/failure
    """
    summaries = [''] * len(df)
    total = len(df)
    sem = asyncio.Semaphore(max(1, max_concurrency))
    state_lock = asyncio.Lock()
    start_time = time.time()
    completed_count = 0

    async def summarize_one(i: int, row) -> tuple[int, str]:
        nonlocal completed_count
        title = str(row.get('Title', '') or '').strip()
        abstract = str(row.get('Abstract', '') or '').strip()
        paper_num = i + 1
        display_title = title[:60] + ("..." if len(title) > 60 else "")
        progress = (paper_num / total) * 100 if total else 100.0
        elapsed_time = time.time() - start_time

        print(f"\n[{paper_num:3d}/{total}] ({progress:.1f}%) 처리 중: {display_title or '(제목 없음)'}")
        print(f"경과시간: {elapsed_time/60:.1f}분")

        if not title and not abstract:
            async with state_lock:
                completed_count += 1
                done = completed_count
            estimated_total_time = (elapsed_time * total / done) if done > 0 else 0
            remaining_time = max(0.0, estimated_total_time - elapsed_time)
            print(f"[{paper_num:3d}/{total}] Title/Abstract 없음 - 건너뜀")
            print(f"예상 남은시간: {remaining_time/60:.1f}분")
            return i, ''

        try:
            async with sem:
                summary = await summarizer.summarize(title, abstract, label=f"abs_summary-{paper_num}")
            async with state_lock:
                completed_count += 1
                done = completed_count
            elapsed_after = time.time() - start_time
            estimated_total_time = (elapsed_after * total / done) if done > 0 else 0
            remaining_time = max(0.0, estimated_total_time - elapsed_after)
            print(f"[{paper_num:3d}/{total}] 완료: {display_title or '(제목 없음)'}")
            print(f"경과시간: {elapsed_after/60:.1f}분 | 예상 남은시간: {remaining_time/60:.1f}분")
        except Exception as e:
            async with state_lock:
                completed_count += 1
                done = completed_count
            elapsed_after = time.time() - start_time
            estimated_total_time = (elapsed_after * total / done) if done > 0 else 0
            remaining_time = max(0.0, estimated_total_time - elapsed_after)
            print(f"[{paper_num:3d}/{total}] 실패 ({e}): {display_title or '(제목 없음)'}")
            print(f"경과시간: {elapsed_after/60:.1f}분 | 예상 남은시간: {remaining_time/60:.1f}분")
            summary = ''

        return i, summary

    tasks = [asyncio.create_task(summarize_one(i, row)) for i, (_, row) in enumerate(df.iterrows())]

    for task in asyncio.as_completed(tasks):
        idx, summary = await task
        summaries[idx] = summary

    return summaries


def insert_column_after(df: pd.DataFrame, anchor_col: str, new_col: str, values: list) -> pd.DataFrame:
    """
    Insert new_col immediately to the right of anchor_col.
    Falls back to appending at the end if anchor_col is not found.
    """
    if anchor_col in df.columns:
        pos = df.columns.get_loc(anchor_col) + 1
    else:
        pos = len(df.columns)
    df.insert(pos, new_col, values)
    return df


async def async_main():
    input_file = os.path.join(results_dir('Phase_4'), 'organ_integrate.csv')
    output_file = os.path.join(results_dir('Phase_5'), '5_abs_summary.csv')

    if not os.path.exists(input_file):
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 Phase 4 (organ_integrate.py)를 실행해주세요.")
        return

    df = pd.read_csv(input_file)
    print(f"총 {len(df)}개 논문 로드 완료: {input_file}")

    try:
        summarizer = AbstractSummarizer()
    except ValueError as e:
        print(f"오류: {e}")
        return

    print(f"\nGPT-5-nano 요약 생성 시작 (총 {len(df)}개)")
    summaries = await generate_summaries(df, summarizer)

    df = insert_column_after(df, 'Authors', 'abs_llm_summary', summaries)

    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    success_count = sum(1 for s in summaries if s.strip())
    print(f"\n요약 생성 완료: {success_count}/{len(df)}개 성공")
    print(f"결과 저장: {output_file}")


def main():
    print("=" * 60)
    print("Phase 5: GPT-5-nano 논문 요약 생성")
    print("=" * 60)
    asyncio.run(async_main())
    print("Phase 5 완료!")


if __name__ == "__main__":
    main()
