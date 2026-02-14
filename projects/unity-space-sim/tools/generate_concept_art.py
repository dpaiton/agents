#!/usr/bin/env python3
"""Generate concept art renders via the OpenAI Images API.

Modes:
  generate  Create a new image from a text prompt (DALL-E 3).
  edit      Edit an existing image with a new prompt (gpt-image-1).
            Use this to render alternative angles of the same ship.

Usage:
    # Generate hero image from scratch
    python generate_concept_art.py generate --prompt "A space fighter..." --output hero.png

    # Edit hero image to produce a different angle (same ship)
    python generate_concept_art.py edit --image hero.png \
      --prompt "Same ship, side profile view..." --output side.png

Requires OPENAI_API_KEY in the environment (or .env file in the repo root).
"""

import argparse
import base64
import io
import json
import os
import sys
import urllib.request
import urllib.error
import uuid
from pathlib import Path


def load_env():
    """Load .env file from repo root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        candidates = [Path.cwd()]
        d = Path(__file__).resolve().parent
        for _ in range(6):
            candidates.append(d)
            d = d.parent
        for d in candidates:
            env_path = d / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                return
    except ImportError:
        pass


def _get_api_key():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        print("Set it in your .env file or export it in your shell.", file=sys.stderr)
        sys.exit(1)
    return api_key


def _save_image(b64_data: str, output_path: str):
    img_bytes = base64.b64decode(b64_data)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)
    print(f"Saved: {output_path}")


def _build_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    """Build a multipart/form-data body from fields and files.

    fields: {name: value} for text fields
    files:  {name: (filename, bytes_data, content_type)} for file fields

    Returns (body_bytes, content_type_header).
    """
    boundary = f"----PythonBoundary{uuid.uuid4().hex}"
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )
    for name, (filename, data, ctype) in files.items():
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        )
        parts.append(header.encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n")

    body = b""
    for p in parts:
        body += p.encode() if isinstance(p, str) else p
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


# ---------------------------------------------------------------------------
# Generate (DALL-E 3)
# ---------------------------------------------------------------------------

def generate_image(prompt: str, output_path: str, size: str = "1024x1024",
                   model: str = "dall-e-3", quality: str = "standard") -> str:
    """Create a new image from a text prompt."""
    api_key = _get_api_key()

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

    _save_image(data["data"][0]["b64_json"], output_path)

    revised_prompt = data["data"][0].get("revised_prompt", "")
    if revised_prompt:
        meta_path = output_path.rsplit(".", 1)[0] + "_prompt.txt"
        with open(meta_path, "w") as f:
            f.write(f"Original prompt:\n{prompt}\n\nRevised prompt:\n{revised_prompt}\n")

    return output_path


# ---------------------------------------------------------------------------
# Edit (gpt-image-1 — keeps the same subject across angles)
# ---------------------------------------------------------------------------

def edit_image(image_path: str, prompt: str, output_path: str,
               size: str = "1024x1024", model: str = "gpt-image-1",
               quality: str = "low") -> str:
    """Edit an existing image with a new prompt.

    Use this to render alternative angles of the same ship by providing
    the hero render as the source image and prompting for a different
    camera angle.
    """
    api_key = _get_api_key()

    with open(image_path, "rb") as f:
        image_data = f.read()

    fields = {
        "model": model,
        "prompt": prompt,
        "n": "1",
        "size": size,
        "quality": quality,
    }
    files = {
        "image": (Path(image_path).name, image_data, "image/png"),
    }

    body, content_type = _build_multipart(fields, files)

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/edits",
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"Error: OpenAI API returned {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not reach OpenAI API: {e.reason}", file=sys.stderr)
        sys.exit(1)

    _save_image(data["data"][0]["b64_json"], output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate concept art via OpenAI image APIs")
    sub = parser.add_subparsers(dest="command")

    # -- generate --
    gen = sub.add_parser("generate", help="Create new image from text prompt (DALL-E 3)")
    gen.add_argument("--prompt", required=True)
    gen.add_argument("--output", required=True)
    gen.add_argument("--size", default="1024x1024",
                     choices=["1024x1024", "1792x1024", "1024x1792"])
    gen.add_argument("--model", default="dall-e-3")
    gen.add_argument("--quality", default="standard", choices=["standard", "hd"])

    # -- edit --
    ed = sub.add_parser("edit", help="Edit existing image for a new angle (gpt-image-1)")
    ed.add_argument("--image", required=True, help="Source image (hero render)")
    ed.add_argument("--prompt", required=True)
    ed.add_argument("--output", required=True)
    ed.add_argument("--size", default="1024x1024",
                    choices=["1024x1024", "1536x1024", "1024x1536"])
    ed.add_argument("--model", default="gpt-image-1")
    ed.add_argument("--quality", default="low", choices=["low", "medium", "high"])

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    load_env()

    if args.command == "generate":
        generate_image(args.prompt, args.output, args.size, args.model, args.quality)
    elif args.command == "edit":
        edit_image(args.image, args.prompt, args.output, args.size, args.model, args.quality)


if __name__ == "__main__":
    main()
