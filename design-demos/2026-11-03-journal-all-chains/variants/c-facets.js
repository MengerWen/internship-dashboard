/* C：七个方向平铺；每区使用相同的自然日纵轴，所有研究链始终在图中。 */
(function () {
  'use strict';

  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.C = function (root, api) {
    const esc = api.esc;
    const data = api.data;
    const tracks = data.tracks || [];
    const chains = data.chains || [];
    const points = api.points({ reverse: false });
    const handoffs = data.handoffs || [];
    const dates = (data.days || []).map(function (day) { return day.date; }).sort();
    const start = dates[0] || data.asOf;
    const end = data.asOf || dates[dates.length - 1] || start;
    const dayMs = 86400000;
    const stamp = function (date) { return Date.parse(date + 'T00:00:00Z'); };
    const firstStamp = stamp(start);
    const span = Math.max(1, Math.round((stamp(end) - firstStamp) / dayMs));
    const offset = function (date) { return (stamp(date) - firstStamp) / dayMs; };
    const y = function (date) { return (offset(date) / span * 100).toFixed(4); };
    const shortDate = function (date) {
      return Number(date.slice(5, 7)) + '/' + Number(date.slice(8, 10));
    };
    const byChain = new Map(chains.map(function (chain) { return [chain.id, []]; }));
    points.forEach(function (point) {
      if (byChain.has(point.chain.id)) byChain.get(point.chain.id).push(point);
    });
    const records = chains.map(function (chain) {
      const rows = byChain.get(chain.id);
      const track = api.track(chain.track);
      return {
        chain: chain,
        points: rows,
        search: [chain.label, chain.short, chain.purpose, chain.fate_note,
          track ? track.label : '', rows.map(function (point) {
            return point.date + ' ' + point.note + ' ' + (point.day.headline || '');
          }).join(' ')].filter(Boolean).join(' ').toLocaleLowerCase()
      };
    });
    const recordMap = new Map(records.map(function (record) { return [record.chain.id, record]; }));
    let selected = '';
    let query = '';

    function calendarGrid() {
      const bands = [];
      const rules = [];
      for (let day = 0; day <= span; day += 1) {
        const date = new Date(firstStamp + day * dayMs);
        const weekday = date.getUTCDay();
        if (weekday === 6) {
          bands.push('<span class="cf-weekend" style="top:' + (day / span * 100).toFixed(4) +
            '%;height:' + (Math.min(2, span - day) / span * 100).toFixed(4) + '%"></span>');
        }
        if (weekday === 1 || date.getUTCDate() === 1) {
          rules.push('<span class="cf-calendar-rule' + (date.getUTCDate() === 1 ? ' is-month' : '') +
            '" style="top:' + (day / span * 100).toFixed(4) + '%"></span>');
        }
      }
      return bands.join('') + rules.join('');
    }

    function dateAxis() {
      const labels = [{ date: start, edge: 'start' }];
      const cursor = new Date(firstStamp);
      cursor.setUTCDate(1);
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
      while (cursor.getTime() < stamp(end)) {
        const date = cursor.toISOString().slice(0, 10);
        if (offset(date) > 5 && span - offset(date) > 8) labels.push({ date: date, edge: '' });
        cursor.setUTCMonth(cursor.getUTCMonth() + 1);
      }
      if (end !== start) labels.push({ date: end, edge: 'end' });
      return labels.map(function (label) {
        return '<time class="cf-axis-date' + (label.edge ? ' is-' + label.edge : '') +
          '" datetime="' + esc(label.date) + '" style="top:' + y(label.date) + '%">' +
          shortDate(label.date) + '</time>';
      }).join('');
    }

    const grid = calendarGrid();
    const axis = dateAxis();

    function chainColumn(record) {
      const chain = record.chain;
      const rows = record.points;
      const segments = rows.slice(1).map(function (point, index) {
        const previous = rows[index];
        const gap = offset(point.date) - offset(previous.date);
        return '<span class="cf-chain-segment' + (gap > 3 ? ' is-gap' : '') + '" style="top:' +
          y(previous.date) + '%;height:' + (gap / span * 100).toFixed(4) + '%"></span>';
      }).join('');
      const marks = rows.map(function (point) {
        return '<button type="button" class="cf-workpoint" data-open-point="' + esc(chain.id) +
          '" data-open-date="' + esc(point.date) + '" style="top:' + y(point.date) +
          '%" aria-label="' + esc(point.date + '，' + chain.label + '：' + point.note) + '">' +
          '<span class="cf-point-mark" aria-hidden="true"></span></button>';
      }).join('');
      return '<section class="cf-chain" data-all-chain="' + esc(chain.id) + '">' +
        '<button type="button" class="cf-chain-name" data-open-chain="' + esc(chain.id) +
        '" aria-label="阅读' + esc(chain.label) + '，' + rows.length + '个记录日">' +
        '<span>' + esc(chain.short || chain.label) + '</span></button>' +
        '<div class="cf-chain-lane">' + segments + marks +
        (rows.length ? '' : '<span class="cf-unrecorded">暂无逐日记录</span>') + '</div></section>';
    }

    function facet(track) {
      const members = records.filter(function (record) { return record.chain.track === track.id; });
      const count = members.reduce(function (sum, record) { return sum + record.points.length; }, 0);
      const wide = members.length > 11;
      return '<section class="cf-facet' + (wide ? ' cf-facet--wide' : '') + '" aria-labelledby="cf-track-' +
        esc(track.id) + '"><header class="cf-facet-heading"><h2 id="cf-track-' + esc(track.id) + '">' +
        esc(track.label) + '</h2><p><b>' + members.length + '</b> 条链<span>' + count +
        ' 个工作点</span></p></header><div class="cf-chart" style="--cf-columns:' + Math.max(1, members.length) +
        ';--cf-hit-height:calc(var(--cf-plot-height) / ' + span + ')">' +
        '<div class="cf-axis-heading">' + esc(start.slice(0, 4)) + '</div>' +
        '<div class="cf-calendar" aria-hidden="true">' + grid + '</div>' +
        '<div class="cf-date-axis" aria-label="自然日日期轴">' + axis + '</div>' +
        '<div class="cf-chain-columns">' + members.map(chainColumn).join('') +
        '</div></div><p class="cf-facet-foot">自然日纵轴，与其他方向对齐</p></section>';
    }

    root.innerHTML = '<div class="cf-page"><header class="page-heading cf-page-heading"><div>' +
      '<h1>七个方向，铺开全部研究链</h1><p>每个方向一幅图，全部链条默认展开。链名在上，日期向下；点选链名或工作点，接着读具体进展。</p>' +
      '</div><p class="cf-period"><time datetime="' + esc(start) + '">' + shortDate(start) +
      '</time><span>至</span><time datetime="' + esc(end) + '">' + shortDate(end) +
      '</time><small>' + chains.length + ' 条链 / ' + dates.length + ' 个记录日 / ' + points.length +
      ' 个工作点</small></p></header><div class="cf-tools"><label class="field cf-search">' +
      '<span>查找</span><input type="search" data-cf-search placeholder="链名、日期或进展" aria-describedby="cf-search-status"></label>' +
      '<button type="button" class="button" data-cf-reset>清除标亮</button>' +
      '<p id="cf-search-status" role="status" aria-live="polite">全部 ' + chains.length + ' 条链均在图中</p></div>' +
      '<div class="cf-key" aria-label="图谱读法"><span><i class="cf-key-dot" aria-hidden="true"></i>当日工作点</span>' +
      '<span><i class="cf-key-gap" aria-hidden="true"></i>超过 3 日的记录间隔</span>' +
      '<span><i class="cf-key-weekend" aria-hidden="true"></i>周末底纹</span><span>七图使用同一时间范围，未记录的日期保留间距</span></div>' +
      '<div class="cf-grid">' + tracks.map(facet).join('') + '</div>' +
      '<aside class="cf-relations" aria-labelledby="cf-relations-title"><h2 id="cf-relations-title">跨链承接</h2>' +
      '<div data-cf-relations><p>点选链名或工作点，图中会标亮已登记的关联链。来源、后续和承接说明可在阅读层中查看。</p></div></aside></div>';

    function renderRelations() {
      const container = root.querySelector('[data-cf-relations]');
      const record = recordMap.get(selected);
      if (!record) {
        container.innerHTML = '<p>点选链名或工作点，图中会标亮已登记的关联链。来源、后续和承接说明可在阅读层中查看。</p>';
        return;
      }
      const edges = handoffs.filter(function (edge) { return edge.from === selected || edge.to === selected; });
      container.innerHTML = '<p class="cf-relations-selected">当前标亮：<strong>' + esc(record.chain.label) + '</strong></p>' +
        (edges.length ? '<ul>' + edges.map(function (edge) {
          const incoming = edge.to === selected;
          const otherId = incoming ? edge.from : edge.to;
          const other = api.chain(otherId);
          const otherTrack = other ? api.track(other.track) : null;
          return '<li><span class="cf-relation-direction">' + (incoming ? '来自' : '后续') + '</span><div>' +
            api.chainLink(otherId) + (otherTrack ? '<span class="cf-relation-track">' + esc(otherTrack.label) + '</span>' : '') +
            '<p><time datetime="' + esc(edge.date) + '">' + esc(edge.date) + '</time> ' +
            esc(edge.type || '') + '。' + esc(edge.note || '') + '</p></div></li>';
        }).join('') + '</ul>' : '<p>这条链当前未登记跨链承接。</p>');
    }

    function updateHighlights() {
      const term = query.trim().toLocaleLowerCase();
      const related = new Set();
      handoffs.forEach(function (edge) {
        if (edge.from === selected) related.add(edge.to);
        if (edge.to === selected) related.add(edge.from);
      });
      let matchedChains = 0;
      let matchedPoints = 0;
      root.querySelectorAll('[data-all-chain]').forEach(function (column) {
        const id = column.getAttribute('data-all-chain');
        const record = recordMap.get(id);
        const matched = Boolean(term && record.search.includes(term));
        if (matched) matchedChains += 1;
        column.classList.toggle('is-search-match', matched);
        column.classList.toggle('is-selected', id === selected);
        column.classList.toggle('is-related', related.has(id));
        column.querySelectorAll('[data-open-point]').forEach(function (mark, index) {
          const point = record.points[index];
          const pointMatch = Boolean(term && [point.date, point.note, point.chain.label,
            point.chain.short, point.day.headline].filter(Boolean).join(' ').toLocaleLowerCase().includes(term));
          mark.classList.toggle('is-search-match', pointMatch);
          if (pointMatch) matchedPoints += 1;
        });
      });
      root.querySelector('#cf-search-status').textContent = term
        ? '标亮 ' + matchedChains + ' 条链、' + matchedPoints + ' 个工作点；全部 ' + chains.length + ' 条链仍在图中'
        : '全部 ' + chains.length + ' 条链均在图中' + (selected ? '；当前链及其承接已标亮' : '');
    }

    root.addEventListener('input', function (event) {
      if (!event.target.matches('[data-cf-search]')) return;
      query = event.target.value;
      updateHighlights();
    });
    root.addEventListener('click', function (event) {
      if (event.target.closest('[data-cf-reset]')) {
        selected = '';
        query = '';
        root.querySelector('[data-cf-search]').value = '';
        updateHighlights();
        renderRelations();
        return;
      }
      const target = event.target.closest('[data-open-point], [data-open-chain]');
      if (!target || !root.contains(target)) return;
      selected = target.getAttribute('data-open-point') || target.getAttribute('data-open-chain');
      updateHighlights();
      renderRelations();
    });
  };
}());
