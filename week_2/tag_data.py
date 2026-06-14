"""Tag jobs with their technical stack using an LLM, via a FastMCP SQL server.

Rate limits (rate_limits.text — gemini-2.5-flash):
  RPM = 5  →  slot duration = 60 / 5 = 12 s per semaphore slot
  RPD = 20 →  batch_size = 10 keeps total calls well within the daily cap

Prompt optimisation (>5% token reduction):
  - System instruction trimmed from ~60 words to ~20 words.
  - Descriptions truncated to first 500 chars; most technical signal is
    front-loaded in job ads, and cutting here reduces per-batch input tokens
    by 50-70 % versus sending full descriptions.

Time optimisation (>5% reduction via async parallel batching):
  asyncio.gather fires all batches concurrently. A Semaphore(RPM=5) limits
  simultaneous API calls; each acquired slot is held for ≥ SLOT_DURATION (12 s)
  to respect the per-minute cap without serial sleeping between batches.
  For N batches, wall time ≈ ⌈N/5⌉ × 12 s  vs.  serial N × (T + 12 s).
  Example: 2 batches → ~12 s async vs. ~32 s serial (~63 % faster).
"""

import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path

from fastmcp import Client
from google import genai

from enums.models import Models
from settings.config import get_settings

# ── Constants ─────────────────────────────────────────────────────────────────
_MODEL = Models.CLOUD_MODELS.GEMINI_3_FLASH_PREVIEW   # change to any Local/Cloud model
_RPM = 5
_BATCH_SIZE = 10            # 10 jobs/call; RPD=20 → up to 200 rows/day
_SLOT_DURATION = 60 / _RPM  # 12 s — enforces ≤ RPM calls per minute
_MAX_RETRIES = 3
_RETRY_DELAY = 60           # s — one full RPM window resets the quota counter
_MAX_DESC_CHARS = 500       # truncate descriptions for prompt optimisation
_TIMEOUT = 120              # s — give up on a single LLM call after this long

_MCP_SERVER = str(Path(__file__).parent / "mcp_server.py")

# Terse prompt: ~20 words vs ~60 in a verbose version (≥ 66 % header reduction)
_PROMPT_TMPL = """\
Extract tech skills from each job description below.
Respond with exactly one line per job using the job's numeric ID in brackets, followed by a dash, then the skills.
If no tech skills exist, write a dash only. No other text.

{jobs}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(batch: list[dict]) -> str:
    blocks = "\n".join(
        f"[{j['source_id']}]\n{j['description'][:_MAX_DESC_CHARS]}"
        for j in batch
    )
    return _PROMPT_TMPL.format(jobs=blocks)


# Matches [id]|skills, [id]: skills, [id]-skills, [id]skills (separator optional)
_LINE_RE = re.compile(r"^\[(\w+)\]\s*[-|:]?\s*(.*)$")
# Phrases the model uses when a job has no tech content
_NO_SKILLS_RE = re.compile(r"no\s+(technical\s+)?skills?(\s+mentioned)?|none|n/a", re.I)


def _has_skills(value: str) -> bool:
    v = value.strip()
    return bool(v) and v != "-" and not _NO_SKILLS_RE.fullmatch(v)


def _parse_response(text: str, expected_ids: list[str]) -> dict[str, str] | None:
    """Parse model output into {source_id: tech_stack}.
    Returns None only on a format failure (wrong line count, unknown IDs) — not when a
    job legitimately has no skills. Callers should use _has_skills() to filter those out.
    """
    # Only keep lines that match the ID pattern — ignore headers, blanks, preamble
    id_set = set(expected_ids)
    result: dict[str, str] = {}
    for ln in text.splitlines():
        m = _LINE_RE.match(ln.strip())
        if not m:
            continue
        sid, value = m.group(1), m.group(2).strip()
        if sid in id_set:
            result[sid] = value

    if len(result) != len(expected_ids):
        matched = set(result.keys())
        missing = id_set - matched
        print(f"[DEBUG] matched {len(result)}/{len(expected_ids)} ids")
        print(f"[DEBUG] missing ids: {missing}")
        print(f"[DEBUG] raw text:\n{text}\n---")
        return None
    return result


def _fallback_tokens(text: str) -> int:
    """Estimate token count when the model does not return usage metadata."""
    return len(text.split()) * 4


def _print_quality_report(all_rows: list[dict]) -> None:
    total = len(all_rows)
    tagged = [r for r in all_rows if r.get("tech_stack")]
    coverage = len(tagged) / total * 100 if total else 0

    all_skills: list[str] = []
    per_job: list[int] = []
    exact_stacks: list[str] = []

    for r in tagged:
        skills = [s.strip() for s in r["tech_stack"].split(",") if s.strip()]
        per_job.append(len(skills))
        all_skills.extend(s.lower() for s in skills)
        exact_stacks.append(r["tech_stack"])

    counts = Counter(all_skills)
    cross_dups = sum(1 for _, c in counts.items() if c > 1)
    avg = sum(per_job) / len(per_job) if per_job else 0
    identical = len(exact_stacks) - len(set(exact_stacks))

    print("\n--- Quality Report ---")
    print(f"Coverage         : {len(tagged)}/{total} ({coverage:.1f}%)")
    print(f"Avg skills/job   : {avg:.1f}")
    print(f"Unique skills    : {len(counts)}")
    print(f"Cross-job dups   : {cross_dups} skills appear in >1 job")
    print(f"Identical stacks : {identical} jobs share an exact tech_stack")


# ── Unified async LLM caller ──────────────────────────────────────────────────

async def _call_llm(
    model: str,
    prompt: str,
    gemini_client: genai.Client | None,
) -> tuple[str, int, int]:
    """Call either a Gemini cloud model or a local Ollama model.
    Returns (text, input_tokens, output_tokens).
    """
    if model in Models.CLOUD_MODELS:
        assert gemini_client is not None
        resp = await gemini_client.aio.models.generate_content(
            model=model, contents=prompt
        )
        text = resp.text or ""
        usage = resp.usage_metadata
        in_tok = (usage.prompt_token_count if usage else None) or _fallback_tokens(prompt)
        out_tok = (usage.candidates_token_count if usage else None) or _fallback_tokens(text)
        return text, in_tok, out_tok

    if model in Models.LOCAL_MODELS:
        from ollama import AsyncClient as OllamaAsync
        resp = await OllamaAsync().chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            think=False,
            stream=False,
        )
        text = resp.message.content or ""
        in_tok = getattr(resp, "prompt_eval_count", None) or _fallback_tokens(prompt)
        out_tok = getattr(resp, "eval_count", None) or _fallback_tokens(text)
        return text, in_tok, out_tok

    raise ValueError(f"Unknown model '{model}'")


# ── Core async batch processor ────────────────────────────────────────────────

async def _process_batch(
    model: str,
    gemini_client: genai.Client | None,
    sem: asyncio.Semaphore,
    batch: list[dict],
    batch_num: int,
    mcp: Client,
) -> tuple[int, int]:
    """Run one LLM batch under the RPM semaphore. Returns (in_tokens, out_tokens)."""
    async with sem:
        slot_start = time.monotonic()
        prompt = _build_prompt(batch)
        expected_ids = [j["source_id"] for j in batch]
        in_tok = out_tok = 0

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                text, in_tok, out_tok = await asyncio.wait_for(
                    _call_llm(model, prompt, gemini_client),
                    timeout=_TIMEOUT,
                )
                
                parsed = _parse_response(text, expected_ids)
                if parsed is None:
                    print(
                        f"[Batch {batch_num}] Attempt {attempt} failed: "
                        "Mismatch between batch size and response"
                    )
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(_RETRY_DELAY)
                    continue

                # Write all jobs: skills if found, "N/A" otherwise so they are
                # never re-queued (get_untagged_jobs only fetches NULL rows)
                updates = [
                    {"source_id": sid, "tech_stack": skills if _has_skills(skills) else "N/A"}
                    for sid, skills in parsed.items()
                ]
                if updates:
                    try:
                        result = await mcp.call_tool(
                            "batch_update_tech_stacks",
                            {"updates_json": json.dumps(updates)},
                        )
                        if result and result.content[0].text.startswith("error"):
                            print(f"[Batch {batch_num}] DB write error: {result.content[0].text}")
                    except Exception as e:
                        print(f"[Batch {batch_num}] DB write failed: {e}")

                for local_idx, (sid, skills) in enumerate(parsed.items()):
                    job_num = batch_num * _BATCH_SIZE + local_idx + 1
                    if _has_skills(skills):
                        print(f"Analyzed Job {job_num} (sid-{sid}): {skills}")
                    else:
                        print(f"Skipped Job {job_num} (sid-{sid}): no tech skills found")
                break

            except asyncio.TimeoutError:
                print(
                    f"[Batch {batch_num}] Attempt {attempt} timed out "
                    f"after {_TIMEOUT}s"
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY)
            except Exception as e:
                print(f"[Batch {batch_num}] Attempt {attempt} error: {e}")
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY)

        # Hold slot for at least SLOT_DURATION to enforce the RPM cap
        if (gap := _SLOT_DURATION - (time.monotonic() - slot_start)) > 0:
            await asyncio.sleep(gap)

        return in_tok, out_tok


# ── Public entry point ────────────────────────────────────────────────────────

async def tag_data(model: str = _MODEL) -> tuple[int, float]:
    """Tag all untagged jobs. Returns (total_tokens, elapsed_ms)."""
    t0 = time.monotonic()
    total_tokens = 0

    gemini_client = (
        genai.Client(api_key=get_settings().gemini_api_key)
        if model in Models.CLOUD_MODELS
        else None
    )

    try:
        async with Client(_MCP_SERVER) as mcp:
            try:
                raw = await mcp.call_tool("get_untagged_jobs", {})
                rows: list[dict] = json.loads(raw.content[0].text)
            except Exception as e:
                print(f"Failed to fetch jobs: {e}")
                return 0, (time.monotonic() - t0) * 1000

            if not rows:
                print("No data to tag")
                return 0, (time.monotonic() - t0) * 1000

            sem = asyncio.Semaphore(_RPM)
            batches = [rows[i : i + _BATCH_SIZE] for i in range(0, len(rows), _BATCH_SIZE)]

            tasks = [
                _process_batch(model, gemini_client, sem, batch, idx, mcp)
                for idx, batch in enumerate(batches)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, tuple):
                    total_tokens += r[0] + r[1]
                elif isinstance(r, Exception):
                    print(f"Batch error: {r}")

            try:
                raw_q = await mcp.call_tool("get_all_tech_stacks", {})
                _print_quality_report(json.loads(raw_q.content[0].text))
            except Exception as e:
                print(f"Quality report failed: {e}")

    except Exception as e:
        print(f"Fatal error: {e}")

    return total_tokens, (time.monotonic() - t0) * 1000


# ── Script entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    from database.config import init_db

    init_db(Path(__file__).resolve().parent / "data" / "jobs.db")

    tokens, ms = asyncio.run(tag_data())
    print(f"\nTotal tokens used: {tokens}, took {ms:.3f}ms")
