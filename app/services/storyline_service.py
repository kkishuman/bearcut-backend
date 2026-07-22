import json
from datetime import datetime, timezone
from typing import Optional, List, Dict

import anthropic
from sqlalchemy.orm import Session

from app.config import CLAUDE_MODEL
from app.models import Clip, ClipAnalysis, Preferences, Storyline, EditPlan


def generate_storyline(
    project_id: int,
    db_factory,
    storyline_id: int,
    previous_segments: Optional[List[Dict]] = None,
    previous_summaries: Optional[List[str]] = None,
):
    """Generate a storyline + edit plan using Claude. Called in a background thread."""
    db: Session = db_factory()
    try:
        storyline = db.get(Storyline, storyline_id)
        if not storyline:
            return

        clips = db.query(Clip).filter(Clip.project_id == project_id).order_by(Clip.upload_order).all()
        prefs = db.query(Preferences).filter(Preferences.project_id == project_id).first()

        clip_data = []
        for clip in clips:
            analysis = db.query(ClipAnalysis).filter(ClipAnalysis.clip_id == clip.id).first()
            if not analysis or analysis.status != "complete":
                continue

            transcript = json.loads(analysis.transcript) if analysis.transcript else []
            keyframes = json.loads(analysis.keyframe_descriptions) if analysis.keyframe_descriptions else []

            clip_data.append({
                "clip_id": clip.id,
                "filename": clip.filename,
                "duration_seconds": clip.duration_seconds,
                "transcript": transcript,
                "keyframe_descriptions": keyframes,
                "scene_summary": analysis.scene_summary,
            })

        if not clip_data:
            storyline.status = "failed"
            storyline.narrative_summary = "No analyzed clips found."
            db.commit()
            return

        prompt = _build_prompt(clip_data, prefs, previous_segments, previous_summaries)

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8192,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)

        storyline.narrative_summary = result.get("narrative_summary", "")
        segments = result.get("segments", [])
        for seg in segments:
            seg["status"] = "pending"
        storyline.segments = json.dumps(segments, ensure_ascii=False)

        if result.get("reshoot_list") is not None:
            storyline.reshoot_list = json.dumps(result["reshoot_list"], ensure_ascii=False)
        if result.get("publishing_suggestions") is not None:
            storyline.publishing_suggestions = json.dumps(result["publishing_suggestions"], ensure_ascii=False)

        storyline.status = "complete"
        db.commit()

        for seg in segments:
            for cut in seg.get("cuts", []):
                plan = EditPlan(
                    storyline_id=storyline.id,
                    segment_id=seg["segment_id"],
                    clip_id=cut["clip_id"],
                    in_timestamp=cut["in_timestamp"],
                    out_timestamp=cut["out_timestamp"],
                    order_in_segment=cut.get("order_in_segment", 0),
                    reasoning=cut.get("reasoning"),
                    transition_note=cut.get("transition_note"),
                    clip_summary=cut.get("clip_summary"),
                    purpose=cut.get("purpose"),
                )
                db.add(plan)
        db.commit()

    except Exception as e:
        try:
            storyline = db.get(Storyline, storyline_id)
            if storyline:
                storyline.status = "failed"
                storyline.narrative_summary = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _build_prompt(
    clip_data: List[Dict],
    prefs: Optional[Preferences],
    previous_segments: Optional[List[Dict]],
    previous_summaries: Optional[List[str]] = None,
) -> str:
    clips_text = ""
    for cd in clip_data:
        transcript_text = " | ".join(
            f"[{s['start']}-{s['end']}] {s['text']}" for s in cd["transcript"][:50]
        )
        keyframes_text = " | ".join(
            f"[{k['timestamp']}秒] {k['description'][:150]}" for k in cd["keyframe_descriptions"][:20]
        )
        clips_text += (
            f"\n### 视频:{cd['filename']} (ID: {cd['clip_id']}, 时长 {cd['duration_seconds']:.1f}秒)\n"
            f"场景概述:{cd['scene_summary']}\n"
            f"语音转写:{transcript_text}\n"
            f"画面描述:{keyframes_text}\n"
        )

    pacing_map = {"fast": "快节奏", "medium": "中等节奏", "slow": "慢节奏"}
    tone_map = {"cinematic": "电影感", "casual": "轻松随性", "energetic": "活力四射", "calm": "平静舒缓"}
    type_map = {"travel": "旅行", "day-in-life": "日常Vlog", "review": "测评", "tutorial": "教程", "other": "其他"}

    platform_constraints = {
        "xiaohongshu": (
            "目标平台:小红书\n"
            "- 时长:30 秒到 3 分钟为佳\n"
            "- 节奏:中慢节奏,画面精致有生活感\n"
            "- 段落数:4-6 段,叙事自然展开\n"
            "- 风格基调:真实、有温度、有审美\n"
            "- 标题风格:口语化,带情绪/利益点,可用 emoji,不超过 20 字\n"
            "- 话题标签:生活化,围绕地点/品类/心情/人群"
        ),
        "douyin": (
            "目标平台:抖音\n"
            "- 时长:15-60 秒为佳\n"
            "- 节奏:快节奏,前 3 秒必须有强钩子(冲突/反差/悬念/高光画面)\n"
            "- 段落数:3-5 段,每段都要有节拍点\n"
            "- 风格基调:强情绪、强反转、强信息密度\n"
            "- 标题风格:短、有冲击力、设悬念或抛结论,带数字或对比\n"
            "- 话题标签:流量话题为主,蹭热点+垂类标签组合"
        ),
        "video_account": (
            "目标平台:视频号\n"
            "- 时长:1-5 分钟为佳\n"
            "- 节奏:中等节奏,完整叙事弧\n"
            "- 段落数:5-8 段,起承转合分明\n"
            "- 风格基调:个人品牌感,真诚、有思考、有观点\n"
            "- 标题风格:陈述句或观点句,体现作者视角\n"
            "- 话题标签:垂直领域标签为主,关注熟人圈层共鸣"
        ),
    }

    prefs_text = ""
    if prefs:
        prefs_text = f"""
## 剪辑偏好
- 节奏:{pacing_map.get(prefs.pacing, prefs.pacing)}
- 风格:{tone_map.get(prefs.tone, prefs.tone)}
- 视频类型:{type_map.get(prefs.vlog_type, prefs.vlog_type)}
"""
        if prefs.target_duration_seconds:
            prefs_text += f"- 目标时长:{prefs.target_duration_seconds} 秒\n"
        if prefs.must_include:
            prefs_text += f"- 必须包含:{prefs.must_include}\n"
        if prefs.must_exclude:
            prefs_text += f"- 必须剔除:{prefs.must_exclude}\n"
        if prefs.additional_notes:
            prefs_text += f"- 备注:{prefs.additional_notes}\n"
        platform = getattr(prefs, "target_platform", "none")
        if platform and platform != "none" and platform in platform_constraints:
            prefs_text += f"\n## 平台约束(必须严格遵守)\n{platform_constraints[platform]}\n"

    anti_pattern_text = ""
    if previous_summaries:
        prior_list = "\n".join(f"- 上第 {i+1} 版:{s}" for i, s in enumerate(previous_summaries))
        anti_pattern_text = f"""
## 过去版本(必须避开,不能重复)
{prior_list}

本次重新生成必须从**全新的角度**切入,以下维度必须发生明显变化:
- 故事框架(线性 / 非线性 / 圆环 等)
- 情绪基调(冷静 / 热烈 / 治愈 / 锐利 等)
- 切入点(从哪个素材的哪个画面开始讲)
- 段落顺序与节奏(开头紧凑 vs 慢热;高潮在中段 vs 收尾前)

不要做和上面任何一版相同立意或类似措辞的故事。如果你直觉认为"上版那个解读最自然",请刻意避开,选一个不那么显然但同样成立的解读。
"""

    regen_text = ""
    if previous_segments:
        accepted = [s for s in previous_segments if s.get("status") == "accepted"]
        rejected = [s for s in previous_segments if s.get("status") == "rejected"]
        if accepted:
            regen_text += "\n## 已采纳的段落(请在新版本中保留这些段落及其位置):\n"
            for s in accepted:
                regen_text += f"- {s['title']}:{s['description']}\n"
        if rejected:
            regen_text += "\n## 已舍弃的段落(请不要包含类似的内容):\n"
            for s in rejected:
                regen_text += f"- {s['title']}:{s['description']}\n"
        regen_text += "\n请重新生成其余段落,填补空缺,优化叙事节奏。\n"

    return f"""你是一位专业的 Vlog 视频剪辑师和内容策划。

## 思考步骤(必须按顺序在心里完成,但不要输出过程)
第一步:逐条阅读每个视频的转写文本和画面描述,识别每段素材的核心内容、情绪、独特价值
第二步:思考这些素材的共性、差异、潜在的叙事线索(地点流转 / 情绪起伏 / 事件因果 / 对比反差 等)
第三步:基于素材的真实内容(不是套路),设计一个有机的故事结构(开头如何抓人、中段如何推进、结尾如何收束)
第四步:才开始填写 narrative_summary —— 必须具体引用素材里的画面或情绪,体现"我真的看过了"

## 你要生成的内容
1. 创作方向(narrative_summary):基于上面的思考,用第一人称表达你想把这些素材剪成什么样的故事 + 为什么要这么剪
2. 故事线(segments):由一系列叙事段落组成的引人入胜的 Vlog,每段标注结构角色
3. 剪辑方案(cuts):每个段落指定使用哪些视频片段,精确到入点和出点
4. 补录清单(reshoot_list):指出叙事缺口、原因、如何补录
5. 平台发布建议(publishing_suggestions):封面帧、标题、话题标签

## 视频素材
{clips_text}
{prefs_text}
{anti_pattern_text}
{regen_text}

## 输出格式
仅返回符合以下结构的 JSON 对象(不要包含任何其他文字、不要 markdown 代码块),所有文本字段必须使用中文:
{{
  "narrative_summary": "创作方向。严格按下面三段结构,用中文撰写,段落之间用空行(\\n\\n)分隔。\\n\\n第一句(独立成段):用一句话说这组素材能讲什么故事。不能说套话,要说出这组素材放在一起独有的、意想不到的气质和化学反应,让用户觉得'对,被说中了,我自己没想到'。\\n\\n第二段:必须以'我从你的素材里看到了:'开头,用 2-3 句话解释为什么这组素材适合这个方向,必须结合用户具体的素材内容(画面、台词、动作、情绪)来说,不能泛泛而谈。\\n\\n第三句(独立成段):剪出来的感觉——节奏快慢、情绪色调、配乐风格,用普通人能懂的语言描述(不要专业术语堆砌)。",
  "segments": [
    {{
      "segment_id": "seg_01",
      "order": 1,
      "role": "开头",
      "title": "段落标题",
      "description": "这一段讲什么,为何放在这里",
      "mood": "这一段的氛围/情绪",
      "estimated_duration_seconds": 15,
      "cuts": [
        {{
          "clip_id": <上方列出的视频 ID,整数>,
          "clip_filename": "filename.mp4",
          "in_timestamp": 12.5,
          "out_timestamp": 18.0,
          "order_in_segment": 1,
          "clip_summary": "一句话描述这段视频的画面内容(具体到能想象出画面;不要以'素材:'开头,直接写画面)",
          "purpose": "这段放在这个位置承担什么情绪功能,为什么是这段而不是别的段,它在故事里推进了什么(把三个问题都回答到,可以2-3句;不要以'作用:'开头,直接写)",
          "transition_note": "转场方式,例如:硬切 / 淡入淡出 / 叠化"
        }}
      ]
    }}
  ],
  "reshoot_list": [
    {{
      "shot_description": "缺哪一类镜头(例如:餐厅外景全景空镜)",
      "reason": "为什么需要补这个镜头(填补哪个叙事缺口)",
      "how_to_capture": "如何拍摄(机位/构图/时长/光线建议)",
      "priority": "essential 或 nice_to_have"
    }}
  ],
  "publishing_suggestions": {{
    "cover_frame": {{
      "clip_id": <选中的视频 ID,整数>,
      "timestamp": 12.5,
      "description": "为什么这一帧适合做封面(画面要素 + 信息传达)"
    }},
    "titles": ["标题备选 1", "标题备选 2", "标题备选 3"],
    "hashtags": ["#话题1", "#话题2", "#话题3", "#话题4", "#话题5"]
  }}
}}

重要要求:
- 仅使用上方列出的视频 ID
- in_timestamp 和 out_timestamp 必须在该视频实际时长范围内
- cover_frame 的 clip_id 必须是真实存在的视频 ID,timestamp 必须在该视频时长内
- 故事弧应有清晰的开头、发展和结尾,每段都有明确作用
- segment 的 role 字段:推荐使用"开头 / 铺垫 / 发展 / 转折 / 高潮 / 收尾 / 结尾",但允许在合适时使用其他更贴切的标签(如"反差 / 呼应 / 闪回")。每段必须有 role。
- cuts 里 clip_summary 与 purpose 必须分开两条:clip_summary 描述素材画面本身(看到什么),purpose 描述这段在故事里起什么作用(叙事功能)。不要把两者混写。
- 严禁:clip_summary 的值不要以"素材:""素材"开头;purpose 的值不要以"作用:""作用"开头。直接写内容本身,UI 会自动加 label。
- 补录清单要诚实指出缺口;如果素材已足够,可返回空数组 []
- 如果选择了目标平台,标题、话题、节奏、时长都要严格匹配平台约束
- 所有文本字段必须使用中文
- 输出必须是合法 JSON,不要包含任何注释或额外文字"""
