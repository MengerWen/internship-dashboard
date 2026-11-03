"""在既有三周期报告上加入沪市口径和两市对照。"""
import html
import re

from factor_atlas_comparison import compare_contexts, decode_summary


def comparison_data(datasets, root):
    references = {}
    identities = {}
    for key in datasets:
        path = root/'content/assets/szse683-2026-11-01'/key/'summary.js'
        loaded, data = decode_summary(path)
        if loaded != key:
            raise ValueError('深市汇总上下文不符')
        references[key] = data
        identities[key] = data['evaluation_proof']['collection_sha256']
    if set(identities.values()) != {'3837fdfe461bf053eeb1f59d6aef8f6e2d550dfe3c11aac2875cd802b11549f6'}:
        raise ValueError('深市对照集合身份改变')
    return compare_contexts(datasets, references)


def adapt_template(template, proof, datasets, slug, publication_date, comparison, encode, table, trial=False):
    """保留既定布局，沪市内容均由本次验收输入生成。"""
    full=datasets['full-10m']
    metadata=[f['metadata'] for f in full['factors']]
    identities={m['scope_sha256'] for m in metadata}
    if identities != {'4137a50de897f42939892ad814bd4417e8791823d0fea34eb19db5f1221a6666'}:
        raise ValueError('沪市scope身份不符')
    definition='''<section id="definition"><div class="section-head"><span class="num">01</span><div><h2>沪市340列因子与冻结定义</h2><p class="subtle">272列既有行为、买侧24列与卖侧24列撤单相位、20列深度匹配；保留原始方向。</p></div></div><p>列序、参数和定义绑定沪市冻结生产清单。逐列定义及方向见下方明细，沪深配对只用于比较同名列的统计，不拼接两个市场的数值。</p><p>沪市scope没有登记定义域，原值分箱沿用共同v7注册表的显示范围；撤单相位为[-1,1]，深度匹配为[0,1]。范围外数值单独计数，不裁剪。完整元数据保留scope身份及可对应的登记身份。</p></section>'''
    template=re.sub(r'<section id="definition">.*?</section>',lambda _:definition,template,flags=re.S)
    if trial:
        segment_text='试运行仅使用原601日中的10个日期；full与base指向同一组试运行样本。'
    else:
        base=next(r for r in proof['datasets'] if r['id']=='base-10m')
        inc=next(r for r in proof['datasets'] if r['id']=='increment-10m')
        segment_text=f'基期截至2026-06-30，共601日、{base["stock_days"]:,}股票日。增量为2026-07-01至10-30，共82日、{inc["stock_days"]:,}股票日。两段不重叠，合计683日。'
    template=re.sub(r'基期截至2026-06-30，共601日.*?两段不重叠，合计683日。',lambda _:segment_text,template)
    template=re.sub(r'<p>9月16日使用.*?</p>','',template)
    template=template.replace('深市344','沪市340').replace('344列','340列').replace('344因子','340因子').replace('<strong>344</strong>','<strong>340</strong>')
    template=template.replace('24 深度匹配','20 深度匹配').replace('深度匹配24列','深度匹配20列')
    template=template.replace('1,957,362',f'{proof["stock_days"]:,}').replace('szse683-2026-11-01',slug)
    template=template.replace('成果归档 2026.11.01 · 评价完成 2026.11.02','成果归档 '+publication_date.strftime('%Y.%m.%d'))
    template=re.sub(r'37个签收批次，683日、340列、.*?恢复只复用已签收且重新校验的结果。',
        lambda _:f'{proof["dates"]}日、340列、{proof["stock_days"]:,}股票日；因子集合与本次评价身份分别校验。',template)
    template=template.replace('3837fdfe461bf053eeb1f59d6aef8f6e2d550dfe3c11aac2875cd802b11549f6',proof['collection_sha256'])
    template=template.replace('6614fc78927452ea9f45ab6fc7d15f7d9515cef41270a5ab6db3d1d8f9a7b784',proof['feature_manifest_sha256'])
    template=re.sub(r'<tr><th>冻结参数文件SHA-256</th><td>.*?</td></tr>',
        '<tr><th>沪市scope SHA-256</th><td><code>'+next(iter(identities))+'</code></td></tr>',template)
    section='''<section id="market-comparison"><div class="section-head"><div><h2>沪深同名列对照</h2><p class="subtle">逐列并列两市Pearson IC、Rank IC、Rank IC NW t、Rank ICIR和G10−G1。汇总按全部及四类来源计算配对列数、Rank IC同号比例和列间排序相关；缺失不填零，常数排序不生成相关。</p></div></div>'''
    if comparison:
        section+=f'<p>配对{len(comparison["columns"])}列；沪市未配对{len(comparison["sse_only"])}列，深市未配对{len(comparison["szse_only"])}列。精确列名优先，其次按唯一定义和方向配对。两市各自使用订单重建、冻结参数、股票池和分钟价格来源；名称相同不代表输入或数值等价。</p>'
        names={'full':'合并683日','base':'原601日','increment':'新增82日','10m':'10分钟','lunch':'午间','close':'收盘'}
        options=''.join('<option value="'+html.escape(k)+'">'+' / '.join(names[x] for x in k.split('-'))+'</option>' for k in comparison['contexts'])
        section+='<label>对照区间与周期<select id="comparison-context">'+options+'</select></label><div id="comparison-summary" class="table-scroll"></div><details><summary>展开全部配对列</summary><div id="comparison-columns" class="table-scroll scroll-table"></div></details><details><summary>未配对列</summary>'+table(['市场','列名'],[['沪市',x] for x in comparison['sse_only']]+[['深市',x] for x in comparison['szse_only']])+'</details><div class="download-row"><a href="../assets/'+slug+'/market-comparison.csv.gz" download data-file-download="market-comparison.csv.gz">下载两市完整对照 CSV.gz</a></div>'
        section+='<script id="market-comparison-data" type="application/octet-stream">'+encode(comparison)+'</script>'
    else:
        section+='<p>10日试运行不生成与深市全期统计的对照；正式构建须提供相同日期的九份市场汇总。</p>'
    section+='</section>'
    template=template.replace('__EXPLORER__',section+'__EXPLORER__')
    template=template.replace('<a href="#factors">逐列浏览</a>','<a href="#market-comparison">沪深同名列</a><a href="#factors">逐列浏览</a>')
    if trial:
        template=template.replace('<option value="increment">新增82日</option>','').replace('683日','10日试运行').replace('原601日','原601日内10日')
        template=re.sub(r'<details><summary>601日与82日方向延续.*?</details>','',template,flags=re.S)
        template=template.replace('2024.01.02 — 2026.10.30',full['dates'][0]+' — '+full['dates'][-1])
    return template


def markdown(publication_date, target, proof, paired):
    title='沪市340因子：683日、增量区间与三个收益周期'
    return f'''---
title: "{title}"
date: {publication_date.isoformat()}
stage: factor
show_source: {target.name}
show_allow_downloads: true
summary: "沪市340列的683日观察评价，分别展示原601日、新增82日和三个收益周期，并附沪深同名列对照。"
---

# {title}

结果覆盖2024年1月2日至2026年10月30日，共683日、340列、{proof['stock_days']:,}股票日。原601日、新增82日与合并683日分别展示，收益周期为10分钟、午间和收盘。逐因子明细和完整精度下载沿用已有方式。

价格来自封存的米筐分钟线，共同起点为09:36分钟VWAP；终点为09:46分钟VWAP、11:30分钟VWAP和15:00分钟收盘价。价格不复权，缺成交或无效价格保留缺失，不向其他时点回退。因子股票日左连接价格，额外上市股票不扩展评价样本。

每日IC至少使用30只成对股票，平均秩10/40分组保留并列值同组。汇总按有效日等权，Newey–West使用Bartlett lag 1，ICIR未年化。新增82日单独展示，不自动视为严格样本外；统计保留原始方向，毛收益未扣成本。

沪深对照共配对{paired}列，按列名优先、唯一定义与方向补配，并列两市的相关与组差统计。两个市场的股票池分别保留。沪市scope未登记定义域，显示分箱沿用共同v7注册表及说明范围，越界单独计数、不裁剪。
'''
