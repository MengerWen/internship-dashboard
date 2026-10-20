from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import frontmatter
import markdown
from pymdownx.slugs import uslugify
from pymdownx.superfences import fence_div_format


ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
SITE_DIR = ROOT / "site"
CONFIG_PATH = ROOT / "config.json"
DIST_DIR = ROOT / "dist"
OFFLINE_DIR = ROOT / "dist-offline"
CN_TZ = timezone(timedelta(hours=8))


@dataclass
class RenderedPage:
    key: str
    title: str
    html: str
    path: str
    meta: dict[str, Any]


class Builder:
    def __init__(self, offline: bool = False, tags_snapshot: Path | None = None) -> None:
        self.offline = offline
        self.tags_snapshot = tags_snapshot or CONTENT_DIR / "report-tags.json"
        self.out_dir = OFFLINE_DIR if offline else DIST_DIR
        self.build_stamp = datetime.now(CN_TZ).strftime("%Y%m%d%H%M%S")
        self.warnings: list[str] = []
        self.git_checked = False
        self.git_available = False
        self.git_shallow = False
        self.git_unshallow_attempted = False
        self.show_stats = {"md": 0, "html": 0, "none": 0, "html_unindexed": 0}
        self.time_stats = {"frontmatter": 0, "git": 0, "mtime": 0}
        self.config = self.read_json(CONFIG_PATH)
        self.stage_by_id = {stage["id"]: stage for stage in self.config["stages"]}
        self.showcase_pages: list[RenderedPage] = []
        self.daily_pages: list[RenderedPage] = []
        self.daily_show_pages: list[RenderedPage] = []
        self.journal_pages: list[RenderedPage] = []
        self.journal_entries: list[dict[str, Any]] = []
        self.journal_evidence: dict[str, Any] = {}
        self.chains: dict[str, Any] = {"tracks": [], "chains": [], "handoffs": []}
        self.journal_drafts = (0, 0)

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def markdown_renderer(self) -> markdown.Markdown:
        return markdown.Markdown(
            extensions=[
                "extra",
                "toc",
                "pymdownx.arithmatex",
                "pymdownx.details",
                "pymdownx.superfences",
                "admonition",
                "codehilite",
            ],
            extension_configs={
                "toc": {"slugify": uslugify, "permalink": False},
                "pymdownx.arithmatex": {
                    "generic": True,
                    "tex_inline_wrap": ["\\(", "\\)"],
                    "tex_block_wrap": ["\\[", "\\]"],
                },
                "pymdownx.superfences": {
                    "custom_fences": [
                        {
                            "name": "mermaid",
                            "class": "mermaid",
                            "format": fence_div_format,
                        }
                    ]
                },
                "codehilite": {
                    "guess_lang": False,
                    "noclasses": False,
                    "pygments_style": "native",
                },
            },
            output_format="html5",
        )

    def render_markdown_file(self, path: Path) -> tuple[dict[str, Any], str] | None:
        try:
            post = frontmatter.loads(path.read_text(encoding="utf-8"))
            md = self.markdown_renderer()
            html = md.convert(post.content)
            return dict(post.metadata), html
        except Exception as exc:  # noqa: BLE001 - build should continue with warnings.
            self.warnings.append(f"{path.relative_to(ROOT)} 渲染失败: {exc}")
            return None

    def normalize_to_cn(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=CN_TZ)
        return value.astimezone(CN_TZ)

    def parse_datetime_value(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return self.normalize_to_cn(value)
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return self.normalize_to_cn(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(text, fmt).replace(tzinfo=CN_TZ)
                except ValueError:
                    continue
        return None

    def ensure_git_available(self) -> bool:
        if self.git_checked:
            return self.git_available
        self.git_checked = True
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.git_available = result.returncode == 0 and result.stdout.strip() == "true"
        except Exception as exc:  # noqa: BLE001
            self.git_available = False
            self.warnings.append(f"git 不可用,日报时间整体降级为 mtime: {exc}")
        if not self.git_available:
            self.warnings.append("当前目录不是 git 仓库或无法调用 git,日报时间整体降级为 mtime")
            return False
        shallow = ROOT / ".git" / "shallow"
        self.git_shallow = shallow.exists()
        if self.git_shallow:
            self.git_unshallow_attempted = True
            result = subprocess.run(
                ["git", "fetch", "--unshallow"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                self.warnings.append("检测到浅克隆,git fetch --unshallow 失败;时间可能降级为 mtime")
            self.git_shallow = shallow.exists()
            if self.git_shallow:
                self.warnings.append("当前仍为浅克隆,首次提交时间可能不可得")
        return True

    def git_times_for(self, path: Path) -> tuple[datetime | None, datetime | None]:
        if not self.ensure_git_available():
            return None, None
        rel = path.relative_to(ROOT).as_posix()
        try:
            added = subprocess.run(
                ["git", "log", "--follow", "--diff-filter=A", "--format=%aI", "--", rel],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=15,
                check=False,
            )
            latest = subprocess.run(
                ["git", "log", "-1", "--format=%aI", "--", rel],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=15,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            self.warnings.append(f"{rel} git 时间读取失败,降级 mtime: {exc}")
            return None, None
        first_lines = [line.strip() for line in added.stdout.splitlines() if line.strip()]
        latest_lines = [line.strip() for line in latest.stdout.splitlines() if line.strip()]
        first = self.parse_datetime_value(first_lines[-1]) if first_lines else None
        last = self.parse_datetime_value(latest_lines[0]) if latest_lines else None
        return first, last

    def mtime_for(self, path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=CN_TZ)

    def file_updated_time(self, path: Path) -> tuple[str, str]:
        _, git_last = self.git_times_for(path)
        source = "git" if git_last else "mtime"
        updated = git_last or self.mtime_for(path)
        if source == "mtime":
            self.warnings.append(f"{path.relative_to(ROOT)} 更新时间来自 mtime，可能不准")
        return self.normalize_to_cn(updated).isoformat(timespec="seconds"), source

    def daily_times(self, path: Path, meta: dict[str, Any]) -> tuple[str, str, str]:
        published_override = self.parse_datetime_value(meta.get("published"))
        git_first, git_last = self.git_times_for(path)
        mtime = self.mtime_for(path)
        source = "mtime"
        if published_override:
            published = published_override
            source = "frontmatter"
        elif git_first:
            published = git_first
            source = "git"
        else:
            published = mtime
            self.warnings.append(f"{path.relative_to(ROOT)} 发布时间来自 mtime，可能不准")

        if git_last:
            updated = git_last
        else:
            updated = mtime
            self.warnings.append(f"{path.relative_to(ROOT)} 更新时间来自 mtime，可能不准")
        self.time_stats[source] += 1
        return (
            self.normalize_to_cn(published).isoformat(timespec="seconds"),
            self.normalize_to_cn(updated).isoformat(timespec="seconds"),
            source,
        )

    def prepare_output(self) -> None:
        if self.out_dir.exists():
            shutil.rmtree(self.out_dir)
        shutil.copytree(SITE_DIR, self.out_dir)
        content_assets = CONTENT_DIR / "assets"
        if content_assets.exists():
            shutil.copytree(
                content_assets,
                self.out_dir / "assets",
                dirs_exist_ok=True,
            )
        self.inject_asset_versions()

    def inject_asset_versions(self) -> None:
        index_path = self.out_dir / "index.html"
        html = index_path.read_text(encoding="utf-8")
        html = re.sub(r"\?v=\d+", f"?v={self.build_stamp}", html)
        index_path.write_text(html, encoding="utf-8", newline="\n")

    def build_showcase(self) -> list[dict[str, Any]]:
        content_by_stage: dict[str, RenderedPage] = {}
        showcase_dir = CONTENT_DIR / "showcase"
        for path in sorted(showcase_dir.glob("*.md")):
            rendered = self.render_markdown_file(path)
            if not rendered:
                continue
            meta, html = rendered
            stage_id = str(meta.get("stage", "")).strip()
            if stage_id not in self.stage_by_id:
                self.warnings.append(f"{path.relative_to(ROOT)} 的 stage 无效,已跳过")
                continue
            title = str(meta.get("title") or self.stage_by_id[stage_id]["label"])
            status = str(meta.get("status") or "planned")
            out_rel = Path("showcase") / f"{stage_id}.html"
            self.write_text(self.out_dir / out_rel, html)
            page = RenderedPage(
                key=stage_id,
                title=title,
                html=html,
                path=out_rel.as_posix(),
                meta={"stage": stage_id, "status": status, "source": path.name},
            )
            content_by_stage[stage_id] = page

        stage_entries: list[dict[str, Any]] = []
        for order, stage in enumerate(self.config["stages"], start=1):
            stage_id = stage["id"]
            page = content_by_stage.get(stage_id)
            if page is None:
                title = stage["label"]
                html = (
                    f"<h1>{title}</h1>\n"
                    "<p>示例内容,待替换。该阶段暂无正式 Markdown 文档。</p>"
                )
                rel = Path("showcase") / f"{stage_id}.html"
                self.write_text(self.out_dir / rel, html)
                page = RenderedPage(
                    key=stage_id,
                    title=title,
                    html=html,
                    path=rel.as_posix(),
                    meta={"stage": stage_id, "status": "planned", "source": None},
                )
            self.showcase_pages.append(page)
            stage_entries.append(
                {
                    "id": stage_id,
                    "label": stage["label"],
                    "title": page.title,
                    "status": page.meta["status"],
                    "order": order,
                    "path": page.path,
                }
            )
        self.write_text(
            self.out_dir / "showcase" / "index-data.json",
            json.dumps(stage_entries, ensure_ascii=False, indent=2),
        )
        return stage_entries

    def infer_title(self, path: Path, body: str, meta: dict[str, Any]) -> str:
        if meta.get("title"):
            return str(meta["title"])
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return path.stem

    def split_show_markdown(self, path: Path, date_key: str) -> tuple[str, str] | None:
        rendered = self.render_markdown_file(path)
        if not rendered:
            return None
        meta, html = rendered
        title = str(meta.get("title") or date_key)
        parts = html.split("<h2")
        scenes: list[str] = []
        if len(parts) == 1:
            scenes = [html]
        else:
            intro = parts[0].strip()
            for part in parts[1:]:
                scene = "<h2" + part
                if intro:
                    scene = intro + "\n" + scene
                    intro = ""
                scenes.append(scene)
        scene_html = "\n".join(
            f'<section class="daily-show-scene markdown-body" data-scene="{index}">\n{scene}\n</section>'
            for index, scene in enumerate(scenes)
        )
        return title, scene_html

    def build_daily(self) -> list[dict[str, Any]]:
        daily_entries: list[dict[str, Any]] = []
        daily_dir = CONTENT_DIR / "daily"
        primary_paths = [
            path for path in sorted(daily_dir.glob("*.md"))
            if not path.name.endswith(".show.md")
        ]
        primary_dates = {path.stem for path in primary_paths}
        for orphan in sorted(daily_dir.glob("*.show.md")):
            date_key = orphan.name.removesuffix(".show.md")
            if date_key not in primary_dates:
                self.warnings.append(f"{orphan.relative_to(ROOT)} 缺少对应主日报,已跳过")
        for orphan in sorted(daily_dir.glob("*.show.html")):
            date_key = orphan.name.removesuffix(".show.html")
            if date_key not in primary_dates:
                self.warnings.append(f"{orphan.relative_to(ROOT)} 缺少对应主日报,已跳过")

        seen_dates: set[str] = set()
        seen_report_ids: set[str] = set()
        for path in primary_paths:
            try:
                post = frontmatter.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                self.warnings.append(f"{path.relative_to(ROOT)} frontmatter 读取失败: {exc}")
                continue

            meta = dict(post.metadata)
            try:
                date_key = datetime.fromisoformat(path.stem).date().isoformat()
                if date_key != path.stem:
                    raise ValueError
            except ValueError:
                self.warnings.append(f"{path.relative_to(ROOT)} 日期解析失败,已跳过")
                continue
            date_value = meta.get("date")
            if date_value:
                try:
                    meta_date = datetime.fromisoformat(str(date_value)).date().isoformat()
                    if meta_date != date_key:
                        self.warnings.append(
                            f"{path.relative_to(ROOT)} frontmatter date 与文件名不一致,以文件名为准"
                        )
                except ValueError:
                    self.warnings.append(
                        f"{path.relative_to(ROOT)} frontmatter date 解析失败,以文件名为准"
                    )
            if date_key in seen_dates:
                self.warnings.append(f"{path.relative_to(ROOT)} 日期 {date_key} 重复,已跳过")
                continue
            seen_dates.add(date_key)
            report_id = str(meta.get("report_id") or date_key)
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", report_id) or report_id in {"__proto__", "constructor", "prototype"} or report_id in seen_report_ids:
                raise ValueError(f"{path.name}: report_id 无效或重复")
            seen_report_ids.add(report_id)

            stage_id = str(meta.get("stage") or "unclassified")
            if stage_id not in self.stage_by_id:
                self.warnings.append(
                    f"{path.relative_to(ROOT)} 缺少或使用未知 stage,已归入 unclassified"
                )
                stage_id = "unclassified"

            try:
                md = self.markdown_renderer()
                html = md.convert(post.content)
            except Exception as exc:  # noqa: BLE001
                self.warnings.append(f"{path.relative_to(ROOT)} 渲染失败: {exc}")
                continue

            title = self.infer_title(path, post.content, meta)
            out_rel = Path("daily") / f"{date_key}.html"
            self.write_text(self.out_dir / out_rel, html)
            download_md_rel = Path("downloads") / "daily" / f"{date_key}.md"
            download_html_rel = Path("downloads") / "daily" / f"{date_key}.html"
            (self.out_dir / download_md_rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, self.out_dir / download_md_rel)
            self.write_text(
                self.out_dir / download_html_rel,
                self.downloadable_daily_html(title, html),
            )
            published_at, updated_at, time_source = self.daily_times(path, meta)
            show_md = daily_dir / f"{date_key}.show.md"
            show_html = daily_dir / f"{date_key}.show.html"
            has_show = False
            show_type: str | None = None
            show_path: str | None = None
            show_title: str | None = None
            show_content: str | None = None
            show_updated_at: str | None = None
            show_time_source: str | None = None
            if show_html.exists() and show_md.exists():
                self.warnings.append(f"{date_key} 同时存在 .show.md 与 .show.html,已使用 .show.html")
            if show_html.exists():
                has_show = True
                show_type = "html"
                show_title = date_key
                show_content = show_html.read_text(encoding="utf-8")
                show_rel = Path("daily") / f"{date_key}.show.html"
                self.write_text(
                    self.out_dir / show_rel,
                    self.html_with_runtime_assets(show_content, prefix="../"),
                )
                show_path = show_rel.as_posix()
                self.show_stats["html"] += 1
                self.show_stats["html_unindexed"] += 1
            elif show_md.exists():
                split = self.split_show_markdown(show_md, date_key)
                if split:
                    has_show = True
                    show_type = "md"
                    show_title, show_content = split
                    show_rel = Path("daily") / f"{date_key}.show.html"
                    self.write_text(self.out_dir / show_rel, show_content)
                    show_path = show_rel.as_posix()
                    self.show_stats["md"] += 1
            else:
                self.show_stats["none"] += 1
            if has_show:
                show_updated_at, show_time_source = self.file_updated_time(
                    show_html if show_type == "html" else show_md
                )
            page = RenderedPage(
                key=date_key,
                title=title,
                html=html,
                path=out_rel.as_posix(),
                meta={
                    "date": date_key,
                    "stage": stage_id,
                    "summary": str(meta.get("summary") or ""),
                    "source": path.name,
                    "published_at": published_at,
                    "updated_at": updated_at,
                    "time_source": time_source,
                    "has_show": has_show,
                    "show_type": show_type,
                    "show_path": show_path,
                    "show_allow_downloads": meta.get("show_allow_downloads") is True,
                    "show_updated_at": show_updated_at,
                    "show_time_source": show_time_source,
                    "download_md_path": download_md_rel.as_posix(),
                    "download_html_path": download_html_rel.as_posix(),
                },
            )
            self.daily_pages.append(page)
            if has_show and show_content and show_path:
                self.daily_show_pages.append(
                    RenderedPage(
                        key=date_key,
                        title=show_title or title,
                        html=show_content,
                        path=show_path,
                        meta={"date": date_key, "stage": stage_id, "show_type": show_type},
                    )
                )
            daily_entries.append(
                {
                    "id": report_id,
                    "date": date_key,
                    "title": title,
                    "stage": stage_id,
                    "summary": page.meta["summary"],
                    "path": page.path,
                    "published_at": published_at,
                    "updated_at": updated_at,
                    "time_source": time_source,
                    "has_show": has_show,
                    "show_type": show_type,
                    "show_path": show_path,
                    "show_allow_downloads": page.meta["show_allow_downloads"],
                    "show_updated_at": show_updated_at,
                    "show_time_source": show_time_source,
                    "download_md_path": download_md_rel.as_posix(),
                    "download_html_path": download_html_rel.as_posix(),
                }
            )

        daily_entries.sort(key=lambda item: item["date"], reverse=True)
        self.daily_pages.sort(key=lambda page: page.key, reverse=True)
        return daily_entries

    def build_journal(self) -> None:
        """只读取本仓文件；采集历史与链条建议均不参与构建。"""
        journal_dir = CONTENT_DIR / "journal"
        registry_path = CONTENT_DIR / "chains.json"
        if not registry_path.exists():
            return
        try:
            registry = self.read_json(registry_path)
        except (ValueError, OSError) as exc:
            self.warnings.append(f"chains.json 读取失败: {exc}")
            return
        tracks = registry.get("tracks", [])
        chains = registry.get("chains", [])
        chain_ids = {c["id"] for c in chains}
        track_ids = {t["id"] for t in tracks}
        for track in tracks:
            if track.get("stage") is not None and track["stage"] not in self.stage_by_id:
                self.warnings.append(f"日志轨道 {track['id']} stage 无效，按无阶段处理")
                track["stage"] = None
            count = sum(c.get("track") == track["id"] for c in chains)
            if count > 10:
                self.warnings.append(f"日志轨道 {track['id']} 有 {count} 条链，超过 10 条")
        for chain in chains:
            if chain.get("track") not in track_ids:
                self.warnings.append(f"日志链条 {chain['id']} 轨道不存在")
        handoffs = []
        for edge in registry.get("handoffs", []):
            if (edge.get("from") not in chain_ids or edge.get("to") not in chain_ids
                    or edge.get("type") not in {"延续", "派生", "依赖解除", "收口"}
                    or edge.get("confidence") not in {"confirmed", "inferred"}):
                self.warnings.append(f"日志交接无效，已忽略: {edge}")
                continue
            if edge.get("date"):
                try:
                    if datetime.fromisoformat(edge["date"]).date().isoformat() != edge["date"]:
                        raise ValueError
                except (ValueError, TypeError):
                    self.warnings.append(f"日志交接日期无效，已忽略: {edge}")
                    continue
            handoffs.append(edge)
        notes = {p.stem: p for p in journal_dir.glob("????-??-??.md")}
        evidence = {}
        for path in sorted((journal_dir / "_evidence").glob("*.json")):
            try:
                key = datetime.fromisoformat(path.stem).date().isoformat()
                ev = self.read_json(path)
                if key != path.stem or ev.get("date") != key:
                    raise ValueError("文件名与 date 不符")
                evidence[key] = ev
            except (ValueError, OSError) as exc:
                self.warnings.append(f"日志证据 {path.name} 无效，已忽略: {exc}")
        missing = len(evidence.keys() - notes.keys())
        if missing:
            self.warnings.append(f"日志还有 {missing} 天缺少每日记录，已回落为待写条目")
        by_chain = {c["id"]: c for c in chains}
        daily = {p.key: p for p in self.daily_pages}
        drafts = long_drafts = 0
        for key in sorted(notes.keys() | evidence.keys()):
            try:
                if datetime.fromisoformat(key).date().isoformat() != key:
                    raise ValueError
            except ValueError:
                self.warnings.append(f"日志日期 {key} 无效，已忽略")
                continue
            meta, body = {}, ""
            if key in notes:
                rendered = self.render_markdown_file(notes[key])
                if rendered:
                    meta, body = rendered
                if str(meta.get("date", key)) != key:
                    self.warnings.append(f"日志 {key} date 与文件名不符，以文件名为准")
            ev = evidence.get(key, {"date": key, "repos": [], "plans": [], "reports_published": []})
            fallback = next((i["subject"] for repo in ev.get("repos", []) for i in repo.get("items", [])), "待写")
            headline = str(meta.get("headline") or fallback)
            source = str(meta.get("headline_source") or "commit")
            if source == "written" and len(headline) > 40:
                self.warnings.append(f"日志 {key} 的一句话超过 40 字")
            if source in {"report", "plan"}:
                drafts += 1
                long_drafts += len(headline) > 40
            highlights = [str(h) for h in meta.get("highlights", [])]
            if len(highlights) > 3:
                self.warnings.append(f"日志 {key} highlights 超过 3 条")
            picked, confidence = [], {}
            for cid in dict.fromkeys(meta.get("chains", [])):
                if cid not in by_chain:
                    self.warnings.append(f"日志 {key} 引用了不存在的链条 {cid}，已忽略")
                    continue
                picked.append(cid)
                review = by_chain[cid].get("review", {})
                pending = key in review.get("unreviewed_days", []) if review else not meta.get("chains_reviewed", False)
                confidence[cid] = "inferred" if pending else "confirmed"
            covering = []
            for rday in meta.get("reports_covering", ev.get("reports_covering", [])):
                rday = str(rday)
                if rday not in daily:
                    self.warnings.append(f"日志 {key} 引用的汇报 {rday} 不存在，已忽略")
                else:
                    covering.append(rday)
            published = [d for d in ev.get("reports_published", []) if d in daily]
            commits = {repo["repo"]: repo["commits"] for repo in ev.get("repos", [])}
            entry = {"date": key, "weekday": "周" + "一二三四五六日"[datetime.fromisoformat(key).weekday()],
                     "headline": headline, "headline_source": source, "chains": picked,
                     "chain_confidence": confidence, "highlights": highlights, "commits": commits,
                     "total_commits": sum(commits.values()), "report": covering[0] if covering else None,
                     "reports_covering": covering, "reports_published": published,
                     "has_body": bool(body.strip()), "evidence_path": f"journal/_evidence/{key}.json"}
            self.journal_entries.append(entry)
            # 标题和摘要来自已有构建结果，不额外复制日报正文。
            ev = {**ev, "reports": [
                {"date": d, "title": daily[d].title, "summary": daily[d].meta["summary"]}
                for d in dict.fromkeys(covering + published)
            ]}
            self.journal_evidence[key] = ev
            self.write_text(self.out_dir / entry["evidence_path"], json.dumps(ev, ensure_ascii=False, indent=2))
            self.write_text(self.out_dir / "journal" / f"{key}.html", body)
            words = [headline, *highlights, *[p["title"] for p in ev.get("plans", [])],
                     *[i["subject"] for r in ev.get("repos", []) for i in r.get("items", [])]]
            self.journal_pages.append(RenderedPage(key=key, title=headline,
                html="\n".join(f"<p>{html_lib.escape(w)}</p>" for w in words) + body,
                path=f"journal/{key}.html", meta={"date": key, "type": "journal"}))
        output_chains = []
        for chain in chains:
            active = [d["date"] for d in self.journal_entries if chain["id"] in d["chains"]]
            public = {k: v for k, v in chain.items() if k not in {"review", "start", "end"}}
            public.update(start=min(active) if active else None, end=max(active) if active else None)
            # 未发布的汇报不能生成死链接。保留源注册表供后续回填。
            if public.get("closes_into"):
                public["closes_into"] = {**public["closes_into"], "daily": [
                    d for d in public["closes_into"].get("daily", []) if d in daily]}
            output_chains.append(public)
        self.chains = {"tracks": tracks, "chains": output_chains, "handoffs": handoffs}
        self.journal_drafts = (drafts, long_drafts)

    def manifest(self, stage_entries: list[dict[str, Any]], daily_entries: list[dict[str, Any]]) -> dict[str, Any]:
        report_tags = self.read_json(self.tags_snapshot)
        if report_tags.get("schemaVersion") != 1 or not isinstance(report_tags.get("tags"), list) or not isinstance(report_tags.get("assignments"), dict):
            raise ValueError(f"标签快照格式不正确: {self.tags_snapshot}")
        data = {
            "built_at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
            "site_title": self.config["site_title"],
            "stages": self.config["stages"],
            "showcase": stage_entries,
            "daily": daily_entries,
            "report_tags": report_tags,
            "journal": self.journal_entries,
            "chains": self.chains,
        }
        self.write_text(
            self.out_dir / "manifest.json",
            json.dumps(data, ensure_ascii=False, indent=2),
        )
        return data

    def build_index_pages(self) -> None:
        index_dir = self.out_dir / "_index-pages"
        for page in self.journal_pages:
            self.write_text(index_dir / f"journal-{page.key}.html", self.index_page_html(
                title=page.title, body=page.html, redirect_hash=f"../#/journal/{page.key}", meta=page.meta))
        for page in self.showcase_pages:
            stage_id = page.meta["stage"]
            self.write_text(
                index_dir / f"showcase-{stage_id}.html",
                self.index_page_html(
                    title=page.title,
                    body=page.html,
                    redirect_hash=f"../#/showcase/{stage_id}",
                    meta={"stage": stage_id, "type": "showcase"},
                ),
            )
        for page in self.daily_pages:
            date_key = page.meta["date"]
            self.write_text(
                index_dir / f"daily-{date_key}.html",
                self.index_page_html(
                    title=page.title,
                    body=page.html,
                    redirect_hash=f"../#/daily/{date_key}",
                    meta={
                        "date": date_key,
                        "stage": page.meta["stage"],
                        "type": "daily",
                    },
                ),
            )
        for page in self.daily_show_pages:
            if page.meta["show_type"] != "md":
                continue
            date_key = page.meta["date"]
            self.write_text(
                index_dir / f"daily-{date_key}-show.html",
                self.index_page_html(
                    title=page.title,
                    body=page.html,
                    redirect_hash=f"../#/daily/{date_key}/show",
                    meta={
                        "date": date_key,
                        "stage": page.meta["stage"],
                        "type": "daily",
                        "view": "展示",
                    },
                ),
            )

    @staticmethod
    def index_page_html(title: str, body: str, redirect_hash: str, meta: dict[str, str]) -> str:
        title_attr = html_lib.escape(title, quote=True)
        meta_tags = "\n  ".join(
            f'<span hidden data-pagefind-meta="{html_lib.escape(f"{key}:{value}", quote=True)}"></span>'
            for key, value in meta.items()
            if value
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex,nofollow">
  <title>{title_attr}</title>
  <script>location.replace("{redirect_hash}");</script>
</head>
<body>
  {meta_tags}
  <main data-pagefind-body>
    <h1>{title_attr}</h1>
    {body}
  </main>
</body>
</html>
"""

    @staticmethod
    def downloadable_daily_html(title: str, body: str) -> str:
        title_attr = html_lib.escape(title, quote=True)
        body = (
            body
            .replace('src="assets/', 'src="../../assets/')
            .replace("src='assets/", "src='../../assets/")
            .replace('href="assets/', 'href="../../assets/')
            .replace("href='assets/", "href='../../assets/")
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_attr}</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true
      }},
      svg: {{fontCache: 'global'}},
      startup: {{typeset: false}}
    }};
  </script>
  <script defer src="../../vendor/mathjax/tex-svg.js"></script>
  <script defer src="../../vendor/mermaid/mermaid.min.js"></script>
  <script defer src="../../js/content-enhance.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      window.ContentEnhancer?.enhance(document);
    }});
  </script>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background: #111827;
      color: #e5e7eb;
      font-family: "Noto Serif SC", "Microsoft YaHei", serif;
      line-height: 1.85;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
    }}
    h1, h2, h3, h4 {{
      line-height: 1.35;
    }}
    h2 {{
      color: #fff6d6;
      margin-top: 32px;
    }}
    a {{
      color: #fff6d6;
    }}
    strong, b {{
      color: #ffffff;
      font-family: "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", sans-serif;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
    }}
    th, td {{
      border: 1px solid #344255;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #202b3b;
      color: #fff6d6;
    }}
    blockquote {{
      margin: 18px 0;
      padding: 14px 18px;
      border: 1px solid rgb(138 149 165 / 0.38);
      border-left: 4px solid #8a95a5;
      border-radius: 8px;
      background: rgb(138 149 165 / 0.16);
      color: #e5e7eb;
    }}
    pre {{
      overflow: auto;
      padding: 16px;
      background: #0a0f1c;
      border: 1px solid #344255;
    }}
  </style>
</head>
<body>
  <main class="markdown-body">
    {body}
  </main>
</body>
</html>
"""

    @staticmethod
    def html_with_runtime_assets(html_text: str, *, prefix: str = "") -> str:
        cleaned = re.sub(
            r"<script\b[^>]*>\s*window\.MathJax\s*=\s*[\s\S]*?;\s*</script>",
            "",
            html_text,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r'<script\b[^>]*\bsrc=["\'][^"\']*mathjax[^"\']*["\'][^>]*>\s*</script>',
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        inject = f"""
<script>
  window.MathJax = {{
    tex: {{
      inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
      displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
      processEscapes: true
    }},
    svg: {{fontCache: 'global'}},
    startup: {{typeset: false}}
  }};
</script>
<script defer src="{prefix}vendor/mathjax/tex-svg.js"></script>
<script defer src="{prefix}vendor/mermaid/mermaid.min.js"></script>
<script defer src="{prefix}js/content-enhance.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', () => {{
    window.ContentEnhancer?.enhance(document);
  }});
</script>
"""
        if re.search(r"</head>", cleaned, flags=re.IGNORECASE):
            return re.sub(
                r"</head>",
                lambda match: inject + match.group(0),
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            )
        return inject + cleaned

    def write_security_files(self) -> None:
        self.write_text(
            self.out_dir / "_headers",
            "/*\n  X-Robots-Tag: noindex, nofollow\n  X-Frame-Options: DENY\n",
        )
        self.write_text(self.out_dir / "robots.txt", "User-agent: *\nDisallow: /\n")

    def inline_offline_data(self, manifest: dict[str, Any]) -> None:
        index_path = self.out_dir / "index.html"
        html = index_path.read_text(encoding="utf-8")
        templates = []
        for entry in self.journal_entries:
            key = entry["date"]
            evidence = json.dumps(self.journal_evidence[key], ensure_ascii=False).replace("</", "<\\/")
            templates.append(f'<script type="application/json" id="journal-ev-{key}">{evidence}</script>')
            if entry["has_body"]:
                body = (self.out_dir / "journal" / f"{key}.html").read_text(encoding="utf-8")
                templates.append(f'<template id="journal-body-{key}">{body}</template>')
        for page in self.showcase_pages:
            templates.append(
                f'<template id="showcase-{page.key}">\n{page.html}\n</template>'
            )
        for page in self.daily_pages:
            templates.append(f'<template id="daily-{page.key}">\n{page.html}\n</template>')
        for page in self.daily_show_pages:
            if page.meta["show_type"] == "html":
                payload = json.dumps(page.html, ensure_ascii=False).replace("</", "<\\/")
                templates.append(
                    f'<script type="application/json" id="daily-show-html-{page.key}">{payload}</script>'
                )
            else:
                templates.append(
                    f'<template id="daily-show-{page.key}" data-show-type="{page.meta["show_type"]}">\n{page.html}\n</template>'
                )
        payload = (
            '<script type="application/json" id="inline-manifest">'
            + json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
            + "</script>\n"
            + "\n".join(templates)
        )
        html = html.replace("<body>", '<body data-offline="true">')
        html = html.replace("<!-- INLINE_DATA -->", payload)
        index_path.write_text(html, encoding="utf-8", newline="\n")

    def run_pagefind(self) -> None:
        if self.offline:
            return
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if npx is None:
            self.warnings.append("未检测到 npx,已跳过 Pagefind 索引")
            return
        try:
            result = subprocess.run(
                [npx, "-y", "pagefind", "--site", str(self.out_dir)],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=120,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            self.warnings.append(f"Pagefind 执行失败,已跳过: {exc}")
            return
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            self.warnings.append(f"Pagefind 返回非零状态,已跳过: {message}")

    def build(self) -> None:
        self.prepare_output()
        stage_entries = self.build_showcase()
        daily_entries = self.build_daily()
        self.build_journal()
        manifest = self.manifest(stage_entries, daily_entries)
        self.build_index_pages()
        self.write_security_files()
        if self.offline:
            self.inline_offline_data(manifest)
        else:
            self.run_pagefind()
        self.print_summary(stage_entries, daily_entries)

    def print_summary(self, stage_entries: list[dict[str, Any]], daily_entries: list[dict[str, Any]]) -> None:
        target = self.out_dir.relative_to(ROOT)
        print(f"构建完成: {target}")
        print(f"日报: {len(daily_entries)} 篇")
        print(f"阶段: {len(stage_entries)} 个")
        print(f"日志: {len(self.journal_entries)} 天；一句话草稿 {self.journal_drafts[0]} 天，其中 {self.journal_drafts[1]} 天超过 40 字")
        print(
            "展示版: "
            f"md {self.show_stats['md']} 篇 / "
            f"html {self.show_stats['html']} 篇 / "
            f"无展示 {self.show_stats['none']} 篇"
        )
        if self.show_stats["html_unindexed"]:
            print(f"展示版搜索: html 跳过索引 {self.show_stats['html_unindexed']} 篇")
        print(
            "时间来源: "
            f"frontmatter {self.time_stats['frontmatter']} 篇 / "
            f"git {self.time_stats['git']} 篇 / "
            f"mtime {self.time_stats['mtime']} 篇"
        )
        if self.warnings:
            print("警告:")
            for warning in self.warnings:
                print(f"- {warning}")
        else:
            print("警告: 0")


def serve() -> None:
    import http.server
    import socketserver
    import webbrowser

    port = 8000
    handler = http.server.SimpleHTTPRequestHandler
    while True:
        try:
            with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
                url = f"http://127.0.0.1:{port}/dist/"
                print(f"本地预览: {url}")
                webbrowser.open(url)
                httpd.serve_forever()
        except OSError:
            port += 1


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Build internship dashboard.")
    parser.add_argument("--offline", action="store_true", help="build dist-offline for file:// use")
    parser.add_argument("--serve", action="store_true", help="build dist and serve locally")
    parser.add_argument("--tags-snapshot", type=Path, help="use an exported report-tags JSON snapshot, including for offline builds")
    args = parser.parse_args()

    builder = Builder(offline=args.offline, tags_snapshot=args.tags_snapshot)
    builder.build()
    if args.serve:
        serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
