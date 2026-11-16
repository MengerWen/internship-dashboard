"""Attach checked Shanghai diagnostics to the 11.16 comparison report."""
from __future__ import annotations

import argparse
import base64
import gzip
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

import yaml

from pack_factor_comparison_data import read_market_data


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "content/daily/2026-11-16.show.html"
ASSETS = ROOT / "content/assets/factor-strategy-comparison"
INDEX = ASSETS / "sse-atlas.json"


def checked_packet(path, expected):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f"诊断签收 SHA-256 不符：{path.name}")
    value = json.loads(gzip.decompress(raw))
    if value["schema"] != "sse-candidate-diagnostics-v1":
        raise ValueError(f"未知沪市诊断格式：{path.name}")
    return value


def registry(research):
    scripts = research / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("candidate_inventory", scripts / "szse344_d24_inventory.py")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    return {row["variant_id"]: row for row in source.metadata(research)["candidates"]}


def atlas(packets, research):
    all_ids = registry(research)
    dates = packets[0]["dates"]
    if len(dates) != 566 or dates != sorted(set(dates)):
        raise ValueError("沪市诊断日期覆盖不符")
    results, faults, input_days = {}, {}, {}
    labels = {(p["preparation_sha256"],p["carry_sha256"]) for p in packets}
    if len(labels) != 1:
        raise ValueError("沪市诊断标签身份不一致")
    for packet in packets:
        if packet["dates"] != dates:
            raise ValueError("分账户沪市日历不同")
        for key, item in packet["variants"].items():
            if key in results and (results[key]["kind"] != "industry" or key not in packet["sources"]["variants"]):
                raise ValueError(f"重复沪市统计：{key}")
            results[key] = item
        faults.update(packet["sources"]["failures"])
        input_days.update(packet["input_days"])
    if not results.keys() <= all_ids.keys():
        raise ValueError("检测到未登记沪市列")
    atlas_data = dict(full=True,registry=len(all_ids),dates=dates,meta=[],results={},other=[],missing=[])
    library = research / "research/factor-candidates/families"
    families = {}
    for key, row in all_ids.items():
        if key not in results:
            atlas_data["missing"].append(dict(id=key,reason=faults.get(key, "未取得已签收沪市结果")))
            continue
        family_id = row["family_id"]
        if family_id not in families:
            families[family_id] = yaml.safe_load((library / (family_id + ".yaml")).read_bytes())
        family = families[family_id]
        variant, = (v for v in family["variants"] if v["variant_id"] == key)
        column = row["aliases"].get("sse") or row["column"] or key
        entry = dict(id=key,family=family_id,name=family["name"],column=column,definition=variant["definition"],
                     hypothesis=family["logic"]["prediction"],inputDays=input_days.get(key))
        result = results[key]
        detail = result["results"]
        if result["kind"] == "stock":
            for h in ("morning","close"):
                if len(detail[h]["daily"])!=566 or set(detail[h]["periods"])!={"all","oof","test_seen","test_unseen"}:
                    raise ValueError(f"日度或阶段结果不完整：{key}/{h}")
            atlas_data["meta"].append(entry)
            atlas_data["results"][key] = detail
        else:
            atlas_data["other"].append(dict(entry,kind=result["kind"],results=detail))
    return atlas_data


def encode(value):
    raw = json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    return base64.b64encode(gzip.compress(raw,mtime=0)).decode("ascii")


NEEDLE = "    for (const option of form.elements.tradeFraction.options) {"
LOADER = """    // Shanghai candidate atlas
    try {
      const asset = document.createElement('script');
      const base = location.protocol === 'about:' ? 'assets/' : '../assets/';
      asset.src = new URL(base + 'factor-strategy-comparison/__ASSET_FILE__', document.baseURI);
      await new Promise((resolve,reject) => {
        asset.onload = resolve;
        asset.onerror = reject;
        document.head.append(asset);
      });
      const encoded = window.csi2000SseAtlas;
      delete window.csi2000SseAtlas;
      const bytes = Uint8Array.from(atob(encoded), letter => letter.charCodeAt(0));
      data.shFactorAtlas = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
    } catch {
      data.shFactorAtlas.loadNotice = '全量沪市资料加载失败。当前可看 6 列先行结果。';
    }
    // End Shanghai candidate atlas
"""


def assemble(template, atlas_data, output, *, inline=False, receipts=()):
    template = re.sub(r"    // Shanghai candidate atlas\n[\s\S]*?    // End Shanghai candidate atlas\n", "", template)
    key = "csi2000-market-data"
    block = re.search(fr'(<script\b[^>]*\bid="{key}"[^>]*>)([^<]+)(</script>)',template)
    if block is None or template.count(NEEDLE)!=1:
        raise ValueError("11.16 报告模板缺少已知数据或渲染入口")
    data = read_market_data(template)
    if data["dates"] != atlas_data["dates"]:
        raise ValueError("沪市因子与策略报告的日历不同")
    if inline:
        data["shFactorAtlas"] = atlas_data
        start = '<script id="csi2000-market-data" type="application/octet-stream">'
        template = template[:block.start()]+start+encode(data)+block.group(3)+template[block.end():]
    else:
        packed = encode(atlas_data)
        asset = "sse-diagnostics-" + sha256(packed.encode()).hexdigest()[:12] + ".js"
        payload = f'window.csi2000SseAtlas="{packed}";\n'.encode("ascii")
        ASSETS.mkdir(parents=True,exist_ok=True)
        (ASSETS/asset).write_bytes(payload)
        INDEX.write_text(json.dumps(dict(schema="sse-atlas-sidecar-v1",file=asset,sha256=sha256(payload).hexdigest(),
            days=len(atlas_data["dates"]),registered=atlas_data["registry"],
            published=atlas_data["registry"]-len(atlas_data["missing"]),sources=list(receipts)),
            indent=2)+"\n",encoding="utf-8")
        template = template.replace(NEEDLE,LOADER.replace("__ASSET_FILE__",asset)+NEEDLE)
        template = template.replace(" · 本地设计讨论稿","").replace(" · 11.16 比较页 Demo"," · 11.16 因子评测与策略比较")
    output.write_text(template,encoding="utf-8",newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research",type=Path,required=True)
    parser.add_argument("--template",type=Path,default=REPORT)
    parser.add_argument("--packet",type=str,nargs=2,action="append",required=True,metavar=("PATH","SHA256"))
    parser.add_argument("--output",type=Path,default=REPORT)
    parser.add_argument("--inline",action="store_true")
    args = parser.parse_args()
    packets = [checked_packet(Path(path),digest.lower()) for path,digest in args.packet]
    receipts = [
        dict(account=p["account"],revision=p["revision"],sha256=record[1].lower())
        for p,record in zip(packets,args.packet,strict=True)
    ]
    assemble(args.template.read_text(encoding="utf-8"),atlas(packets,args.research),args.output,
             inline=args.inline,receipts=receipts)


if __name__ == "__main__":
    main()
