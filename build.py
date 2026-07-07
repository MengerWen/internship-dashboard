from __future__ import annotations

import argparse
import html as html_lib
import json
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
    def __init__(self, offline: bool = False) -> None:
        self.offline = offline
        self.out_dir = OFFLINE_DIR if offline else DIST_DIR
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
                "pymdownx.details",
                "pymdownx.superfences",
                "admonition",
                "codehilite",
            ],
            extension_configs={
                "toc": {"slugify": uslugify, "permalink": False},
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
            self.warnings.append(f"{path.relative_to(ROOT)} 发布时间来自 mtime,可能不准")

        if git_last:
            updated = git_last
        else:
            updated = mtime
            self.warnings.append(f"{path.relative_to(ROOT)} 更新时间来自 mtime,可能不准")
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

        for path in primary_paths:
            try:
                post = frontmatter.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                self.warnings.append(f"{path.relative_to(ROOT)} frontmatter 读取失败: {exc}")
                continue

            meta = dict(post.metadata)
            date_value = str(meta.get("date") or path.stem)
            try:
                date_key = datetime.fromisoformat(date_value).date().isoformat()
            except ValueError:
                self.warnings.append(f"{path.relative_to(ROOT)} 日期解析失败,已跳过")
                continue

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
            published_at, updated_at, time_source = self.daily_times(path, meta)
            show_md = daily_dir / f"{date_key}.show.md"
            show_html = daily_dir / f"{date_key}.show.html"
            has_show = False
            show_type: str | None = None
            show_path: str | None = None
            show_title: str | None = None
            show_content: str | None = None
            if show_html.exists() and show_md.exists():
                self.warnings.append(f"{date_key} 同时存在 .show.md 与 .show.html,已使用 .show.html")
            if show_html.exists():
                has_show = True
                show_type = "html"
                show_title = date_key
                show_content = show_html.read_text(encoding="utf-8")
                show_rel = Path("daily") / f"{date_key}.show.html"
                self.write_text(self.out_dir / show_rel, show_content)
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
                }
            )

        daily_entries.sort(key=lambda item: item["date"], reverse=True)
        self.daily_pages.sort(key=lambda page: page.key, reverse=True)
        return daily_entries

    def manifest(self, stage_entries: list[dict[str, Any]], daily_entries: list[dict[str, Any]]) -> dict[str, Any]:
        data = {
            "built_at": datetime.now(CN_TZ).isoformat(timespec="seconds"),
            "site_title": self.config["site_title"],
            "stages": self.config["stages"],
            "showcase": stage_entries,
            "daily": daily_entries,
        }
        self.write_text(
            self.out_dir / "manifest.json",
            json.dumps(data, ensure_ascii=False, indent=2),
        )
        return data

    def build_index_pages(self) -> None:
        index_dir = self.out_dir / "_index-pages"
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
        for page in self.showcase_pages:
            templates.append(
                f'<template id="showcase-{page.key}">\n{page.html}\n</template>'
            )
        for page in self.daily_pages:
            templates.append(f'<template id="daily-{page.key}">\n{page.html}\n</template>')
        for page in self.daily_show_pages:
            templates.append(
                f'<template id="daily-show-{page.key}" data-show-type="{page.meta["show_type"]}">\n{page.html}\n</template>'
            )
        payload = (
            '<script type="application/json" id="inline-manifest">'
            + json.dumps(manifest, ensure_ascii=False)
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
    parser = argparse.ArgumentParser(description="Build internship dashboard.")
    parser.add_argument("--offline", action="store_true", help="build dist-offline for file:// use")
    parser.add_argument("--serve", action="store_true", help="build dist and serve locally")
    args = parser.parse_args()

    builder = Builder(offline=args.offline)
    builder.build()
    if args.serve:
        serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
