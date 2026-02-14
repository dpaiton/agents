#!/usr/bin/env python3
"""Generate concept art renders via the OpenAI Images API (DALL-E 3).

Usage:
    python generate_concept_art.py --prompt "A small space fighter..." --output render.png
    python generate_concept_art.py --prompt "..." --output render.png --size 1792x1024
    python generate_concept_art.py --prompt "..." --output render.png --model dall-e-3 --quality hd

Requires OPENAI_API_KEY in the environment (or .env file in the repo root).
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_env():
    """Load .env file from repo root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        # Walk up to find .env
        d = Path(__file__).resolve().parent
        for _ in range(5):
            env_path = d / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                return
            d = d.parent
    except ImportError:
        pass


def generate_image(prompt: str, output_path: str, size: str = "1792x1024",
                   model: str = "dall-e-3", quality: str = "hd") -> str:
    """Call OpenAI Images API and save the result to output_path.

    Returns the path to the saved image.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        print("Set it in your .env file or export it in your shell.", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "b64_json",
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"Error: OpenAI API returned {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not reach OpenAI API: {e.reason}", file=sys.stderr)
        sys.exit(1)

    b64_data = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(b64_data)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    revised_prompt = data["data"][0].get("revised_prompt", "")
    if revised_prompt:
        # Save the revised prompt alongside the image for reference
        meta_path = output_path.rsplit(".", 1)[0] + "_prompt.txt"
        with open(meta_path, "w") as f:
            f.write(f"Original prompt:\n{prompt}\n\nRevised prompt:\n{revised_prompt}\n")

    print(f"Saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate concept art via OpenAI DALL-E")
    parser.add_argument("--prompt", required=True, help="Image generation prompt")
    parser.add_argument("--output", required=True, help="Output file path (PNG)")
    parser.add_argument("--size", default="1792x1024",
                        choices=["1024x1024", "1792x1024", "1024x1792"],
                        help="Image size (default: 1792x1024)")
    parser.add_argument("--model", default="dall-e-3",
                        help="Model to use (default: dall-e-3)")
    parser.add_argument("--quality", default="hd", choices=["standard", "hd"],
                        help="Quality level (default: hd)")
    args = parser.parse_args()

    load_env()
    generate_image(args.prompt, args.output, args.size, args.model, args.quality)


if __name__ == "__main__":
    main()
