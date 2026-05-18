"""Standalone auto-post runner for GitHub Actions.

Keep this file thin: load schedule, run content pipeline, publish, log outcome.
"""

from __future__ import annotations

import argparse
import os
import sys

import content_orchestrator
import facebook_publisher
import scheduler_runner


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"{name} not set in GitHub Secrets")
        sys.exit(1)
    return value


def publish_result(bundle: dict, fb_page: str, fb_token: str) -> dict:
    text = bundle["text"]
    slides = bundle.get("slides") or []
    image = bundle.get("image")

    if slides:
        result = facebook_publisher.post_carousel(fb_page, fb_token, slides, text)
        if result.get("success"):
            return result

    if image:
        result = facebook_publisher.post_image(fb_page, fb_token, image, text)
        if result.get("success"):
            return result

    return facebook_publisher.post_text(fb_page, fb_token, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one scheduled post.")
    parser.add_argument(
        "--slot",
        required=True,
        choices=["morning", "afternoon", "evening", "trending"],
    )
    args = parser.parse_args(argv)

    groq_key = _require_env("GROQ_API_KEY")
    fb_token = _require_env("FB_PAGE_TOKEN")
    fb_page = _require_env("FB_PAGE_ID")

    slot_name, slot = scheduler_runner.get_next_slot(args.slot)
    bundle = content_orchestrator.generate_content_bundle(slot_name, slot, groq_key)
    if not bundle:
        print("Failed to generate publishable content")
        return 1

    result = publish_result(bundle, fb_page, fb_token)
    content_orchestrator.record_run(bundle, result)

    if result.get("success"):
        print(f"POSTED SUCCESSFULLY: {result['id']}")
        return 0

    print(f"FAILED: {result.get('error')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
