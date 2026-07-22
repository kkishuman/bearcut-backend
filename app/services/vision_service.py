import base64
import json
from typing import List, Dict, Tuple

import anthropic

from app.config import CLAUDE_MODEL, VISION_BATCH_SIZE


def analyze_keyframes(frames: List[Tuple[str, float]]) -> List[Dict]:
    """Send keyframes to Claude Vision API in batches. Returns list of {timestamp, description, tags}."""
    if not frames:
        return []

    client = anthropic.Anthropic()
    all_descriptions = []

    for batch_start in range(0, len(frames), VISION_BATCH_SIZE):
        batch = frames[batch_start:batch_start + VISION_BATCH_SIZE]
        content = []

        for frame_path, timestamp in batch:
            with open(frame_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            content.append({
                "type": "text",
                "text": f"Frame at {timestamp:.1f}s:",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data,
                },
            })

        content.append({
            "type": "text",
            "text": (
                "你正在为 Vlog 视频剪辑师分析视频关键帧。"
                "请用中文针对每一帧(标注了对应的时间戳)描述以下内容:\n"
                "- 画面内容(场景、人物、物体、文字)\n"
                "- 拍摄场景/地点\n"
                "- 正在发生的活动\n"
                "- 情绪基调 / 画面氛围\n"
                "- 任何值得注意的视觉亮点\n\n"
                "请以 JSON 数组的形式返回,每个对象包含:"
                "timestamp(数字,时间戳)、description(字符串,中文描述)、tags(字符串数组,中文标签)。\n"
                "只返回 JSON 数组,不要包含任何其他文字。"
            ),
        })

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            batch_results = json.loads(text)
            all_descriptions.extend(batch_results)
        except json.JSONDecodeError:
            for frame_path, timestamp in batch:
                all_descriptions.append({
                    "timestamp": timestamp,
                    "description": text,
                    "tags": [],
                })

    return all_descriptions
