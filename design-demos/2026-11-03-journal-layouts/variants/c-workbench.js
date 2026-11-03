/* C：以单条研究链为阅读单位，目录与承接均在工作台内切换。 */
(function () {
  'use strict';

  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.C = function (root, api) {
    const esc = api.esc;
    const tracks = api.data.tracks || [];
    const chains = api.data.chains || [];
    const handoffs = api.data.handoffs || [];
    const records = chains.map(function (chain) {
      const points = api.points({ chainId: chain.id, reverse: false });
      const track = api.track(chain.track);
      return {
        chain: chain,
        points: points,
        first: points[0],
        last: points[points.length - 1],
        search: [chain.label, chain.short, chain.purpose, chain.fate_note,
          track ? track.label : '', points.map(function (point) { return point.note; }).join(' ')]
          .filter(Boolean).join(' ').toLocaleLowerCase()
      };
    });
    const byId = new Map(records.map(function (record) { return [record.chain.id, record]; }));
    const initial = byId.get('corrected-factor-344') || records.find(function (record) {
      return record.points.length >= 10;
    }) || records[0];
    const state = {
      selected: initial ? initial.chain.id : '',
      query: '',
      track: 'all',
      month: 'all',
      directoryOpen: false
    };
    const fateLabels = {
      landed: '阶段记录',
      folded: '并入后续工作',
      dropped: '未采用'
    };

    function shortDate(date) {
      return date ? Number(date.slice(5, 7)) + '/' + Number(date.slice(8, 10)) : '暂无记录';
    }

    function fullDate(date) {
      return date ? date.replace(/-/g, '.') : '暂无记录';
    }

    function monthLabel(month) {
      return month.slice(0, 4) + '年' + Number(month.slice(5, 7)) + '月';
    }

    function trackLabel(chain) {
      const track = api.track(chain.track);
      return track ? track.label : chain.track || '未分类';
    }

    function localChainButton(id, text, extraClass) {
      const chain = api.chain(id);
      if (!chain) return '<span>' + esc(text || id) + '</span>';
      return '<button type="button" class="wb-local-link ' + (extraClass || '') + '" data-wb-select="' +
        esc(id) + '">' + esc(text || chain.label) + '</button>';
    }

    function directoryItem(record) {
      const selected = record.chain.id === state.selected;
      return '<li><button type="button" class="wb-directory-item' + (selected ? ' is-selected' : '') +
        '" data-wb-select="' + esc(record.chain.id) + '" aria-pressed="' + selected + '">' +
        '<span class="wb-directory-name">' + esc(record.chain.label) + '</span>' +
        '<span class="wb-directory-meta"><span>' + esc(trackLabel(record.chain)) + '</span>' +
        '<span>' + record.points.length + '个记录日</span></span>' +
        '<span class="wb-directory-period">' +
        (record.first ? fullDate(record.first.date) + ' — ' + fullDate(record.last.date) : '尚无逐日记录') +
        (selected ? '<span class="wb-selected-label">当前阅读</span>' : '') + '</span></button></li>';
    }

    function relationItem(edge, incoming) {
      const otherId = incoming ? edge.from : edge.to;
      const other = api.chain(otherId);
      const sourceDate = edge.source_date || edge.date;
      const dates = sourceDate && sourceDate !== edge.date
        ? shortDate(sourceDate) + '来源记录 / ' + shortDate(edge.date) + '承接'
        : shortDate(edge.date || sourceDate);
      return '<li class="wb-relation"><p class="wb-relation-meta"><time datetime="' +
        esc(edge.date || sourceDate || '') + '">' + esc(dates) + '</time>' +
        (edge.type ? '<span>' + esc(edge.type) + '</span>' : '') + '</p>' +
        localChainButton(otherId, other ? other.label : otherId) +
        '<p class="wb-relation-note">' + esc(edge.note || '此处登记了承接关系，尚无补充说明。') + '</p></li>';
    }

    function renderRelations(chain) {
      const incoming = handoffs.filter(function (edge) { return edge.to === chain.id; });
      const outgoing = handoffs.filter(function (edge) { return edge.from === chain.id; });
      function group(title, edges, isIncoming) {
        return '<section class="wb-relation-group"><h4>' + title + '<span>' + edges.length + '</span></h4>' +
          (edges.length ? '<ul>' + edges.map(function (edge) {
            return relationItem(edge, isIncoming);
          }).join('') + '</ul>' : '<p class="wb-no-relation">暂无已登记的' +
            (isIncoming ? '来源' : '后续') + '关系。</p>') + '</section>';
      }
      return '<aside class="wb-relations" aria-labelledby="wb-relations-title">' +
        '<h3 id="wb-relations-title">承接关系</h3><p class="wb-relations-help">点击链名，在工作台里接着读。</p>' +
        group('从哪里接来', incoming, true) + group('交给谁继续', outgoing, false) + '</aside>';
    }

    function renderTimeline(record) {
      const months = new Map();
      record.points.forEach(function (point) {
        const month = point.date.slice(0, 7);
        if (!months.has(month)) months.set(month, []);
        months.get(month).push(point);
      });
      const visible = state.month === 'all' ? Array.from(months.entries()) :
        Array.from(months.entries()).filter(function (entry) { return entry[0] === state.month; });
      const count = visible.reduce(function (sum, entry) { return sum + entry[1].length; }, 0);
      return '<section class="wb-progress" aria-labelledby="wb-progress-title">' +
        '<div class="wb-progress-heading"><h3 id="wb-progress-title">按日期看推进</h3>' +
        '<span>' + (state.month === 'all' ? '完整时间线' : esc(monthLabel(state.month))) + '，' + count +
        '个记录日</span></div>' +
        '<nav class="wb-month-nav" aria-label="进展月份"><button type="button" class="button' +
        (state.month === 'all' ? ' is-active' : '') + '" data-wb-month="all" aria-pressed="' +
        (state.month === 'all') + '">全部 ' + record.points.length + '日</button>' +
        Array.from(months.entries()).map(function (entry) {
          return '<button type="button" class="button' + (state.month === entry[0] ? ' is-active' : '') +
            '" data-wb-month="' + entry[0] + '" aria-pressed="' + (state.month === entry[0]) + '">' +
            Number(entry[0].slice(5, 7)) + '月 <span>' + entry[1].length + '日</span></button>';
        }).join('') + '</nav>' +
        (visible.length ? visible.map(function (entry) {
          return '<section class="wb-month-section"><h4 class="wb-month-title">' + esc(monthLabel(entry[0])) +
            '</h4><ol class="wb-timeline">' + entry[1].map(function (point) {
              return '<li class="wb-progress-point"><time class="wb-point-date" datetime="' + esc(point.date) +
                '">' + shortDate(point.date) + '</time><div class="wb-point-content"><p class="wb-point-note">' +
                esc(point.note || '本日尚未补写这条研究链的进展。') + '</p>' +
                (['dropped', 'parked'].includes(point.outcome) && fateLabels[point.outcome] ? '<p class="wb-point-outcome">方案去向：' +
                  esc(fateLabels[point.outcome]) + '</p>' : '') +
                api.pointLink(point, '阅读这条进展') + '</div></li>';
            }).join('') + '</ol></section>';
        }).join('') : '<p class="empty">这条研究链尚无逐日记录。</p>') + '</section>';
    }

    function renderDetail(record) {
      if (!record) return '<section class="empty"><h2>暂无研究链</h2><p>当前内容源中没有可阅读的研究链。</p></section>';
      const chain = record.chain;
      const sourceCount = (chain.source_refs || []).length;
      const range = record.first ? fullDate(record.first.date) + ' — ' + fullDate(record.last.date) : '尚无逐日记录';
      return '<article class="wb-detail" aria-labelledby="wb-detail-title"><header class="wb-detail-header">' +
        '<p class="wb-detail-meta"><span>' + esc(trackLabel(chain)) + '</span><span>' + record.points.length +
        '个记录日</span><span>' + range + '</span></p>' +
        '<h2 id="wb-detail-title" class="wb-detail-title" tabindex="-1">' + esc(chain.label) + '</h2>' +
        '<p class="wb-purpose">' + esc(chain.purpose || '这条研究链尚未补写目标说明。') + '</p>' +
        '<div class="wb-conclusion"><span class="wb-fate">' +
        esc(fateLabels[chain.fate] || (chain.status === 'done' ? '阶段已收口' : '进行中')) +
        '</span><p>' + esc(chain.fate_note || '暂无阶段状态说明。') + '</p></div>' +
        '<div class="wb-summary-actions">' + api.chainLink(chain.id, '完整资料与原始依据') +
        (sourceCount ? '<span>' + sourceCount + '份来源资料</span>' : '') + '</div>' +
        (record.first ? '<div class="wb-endpoints" aria-label="这条研究链的起点与最新进展">' +
          '<div><p class="wb-endpoint-label">起点 <time datetime="' + esc(record.first.date) + '">' +
          shortDate(record.first.date) + '</time></p><p class="wb-endpoint-note">' +
          esc(record.first.note || '尚未补写本链进展。') + '</p></div>' +
          '<div><p class="wb-endpoint-label">最近记录 <time datetime="' + esc(record.last.date) + '">' +
          shortDate(record.last.date) + '</time></p><p class="wb-endpoint-note">' +
          esc(record.last.note || '尚未补写本链进展。') + '</p></div></div>' : '') +
        '</header><div class="wb-detail-body">' + renderTimeline(record) + renderRelations(chain) + '</div></article>';
    }

    function render(options) {
      options = options || {};
      const oldList = root.querySelector('.wb-directory-list');
      const oldScroll = oldList ? oldList.scrollTop : 0;
      const oldSearch = root.querySelector('[data-wb-search]');
      const caret = oldSearch && document.activeElement === oldSearch ? oldSearch.selectionStart : null;
      const query = state.query.trim().toLocaleLowerCase();
      const filtered = records.filter(function (record) {
        return (state.track === 'all' || record.chain.track === state.track) && (!query || record.search.includes(query));
      }).sort(function (a, b) {
        return (b.last ? b.last.date : '').localeCompare(a.last ? a.last.date : '') ||
          a.chain.label.localeCompare(b.chain.label, 'zh-CN');
      });
      const record = byId.get(state.selected);
      const selectedIsVisible = filtered.some(function (item) { return item.chain.id === state.selected; });

      root.innerHTML = '<div class="wb-workbench"><header class="page-heading wb-page-heading">' +
        '<div><h1>链条工作台</h1><p>先选一条研究线，按日期读它的推进与承接。</p></div>' +
        '<p class="wb-asof">记录截至 <time datetime="' + esc(api.data.asOf) + '">' +
        fullDate(api.data.asOf) + '</time></p></header>' +
        '<div class="wb-layout"><aside class="wb-directory' + (state.directoryOpen ? ' is-expanded' : '') +
        '" aria-label="研究链目录"><div class="wb-directory-desktop-title"><h2>研究链目录</h2><span>' +
        chains.length + '条</span></div>' +
        '<button type="button" class="wb-directory-toggle" data-wb-directory aria-controls="wb-directory-body" aria-expanded="' +
        state.directoryOpen + '"><span><b>研究链目录</b><span>' + chains.length + '条研究链</span></span>' +
        '<span>' + (state.directoryOpen ? '收起目录 −' : '选择研究链 +') + '</span></button>' +
        '<div id="wb-directory-body" class="wb-directory-body"><div class="wb-directory-controls">' +
        '<label for="wb-search">查找研究链</label><input id="wb-search" type="search" data-wb-search value="' +
        esc(state.query) + '" placeholder="链名、目标或进展关键词">' +
        '<label for="wb-track">研究方向</label><select id="wb-track" data-wb-track><option value="all"' +
        (state.track === 'all' ? ' selected' : '') + '>全部方向（' + chains.length + '）</option>' +
        tracks.map(function (track) {
          const count = chains.filter(function (chain) { return chain.track === track.id; }).length;
          return '<option value="' + esc(track.id) + '"' + (state.track === track.id ? ' selected' : '') + '>' +
            esc(track.label) + '（' + count + '）</option>';
        }).join('') + '</select><div class="wb-directory-result"><span role="status" aria-live="polite">' +
        '找到 ' + filtered.length + ' 条研究链</span>' +
        (state.query || state.track !== 'all' ? '<button type="button" data-wb-reset>清除筛选</button>' : '') +
        '</div></div>' +
        (!selectedIsVisible && record ? '<div class="wb-filter-notice">当前阅读的研究链不在筛选结果中。' +
          '<button type="button" data-wb-reset>显示全部研究链</button></div>' : '') +
        '<div class="wb-directory-list"><ul>' + (filtered.length ? filtered.map(directoryItem).join('') :
          '<li class="wb-no-results">没有找到符合条件的研究链。试试其他关键词，或清除筛选。</li>') +
        '</ul></div><p class="wb-directory-footnote">按最近记录排序。筛选只影响目录。</p></div></aside>' +
        renderDetail(record) + '</div></div>';

      const newList = root.querySelector('.wb-directory-list');
      if (newList && !options.resetList) newList.scrollTop = oldScroll;
      if (options.focusSearch) {
        const search = root.querySelector('[data-wb-search]');
        search.focus({ preventScroll: true });
        if (caret !== null) search.setSelectionRange(caret, caret);
      } else if (options.focusHeading) {
        const heading = root.querySelector('#wb-detail-title');
        if (heading) heading.focus();
      } else if (options.focusSelector) {
        const target = root.querySelector(options.focusSelector);
        if (target) target.focus({ preventScroll: true });
      }
    }

    root.addEventListener('click', function (event) {
      const target = event.target.closest('button');
      if (!target || !root.contains(target)) return;
      if (target.hasAttribute('data-wb-select')) {
        const id = target.getAttribute('data-wb-select');
        if (!byId.has(id)) return;
        state.selected = id;
        state.month = 'all';
        state.directoryOpen = false;
        render({ focusHeading: true });
      } else if (target.hasAttribute('data-wb-directory')) {
        state.directoryOpen = !state.directoryOpen;
        render({ focusSelector: '[data-wb-directory]' });
      } else if (target.hasAttribute('data-wb-month')) {
        state.month = target.getAttribute('data-wb-month');
        render({ focusSelector: '[data-wb-month="' + state.month + '"]' });
      } else if (target.hasAttribute('data-wb-reset')) {
        state.query = '';
        state.track = 'all';
        render({ focusSearch: true, resetList: true });
      }
    });

    root.addEventListener('input', function (event) {
      if (!event.target.matches('[data-wb-search]')) return;
      state.query = event.target.value;
      if (event.isComposing) return;
      render({ focusSearch: true, resetList: true });
    });

    root.addEventListener('compositionend', function (event) {
      if (!event.target.matches('[data-wb-search]')) return;
      state.query = event.target.value;
      render({ focusSearch: true, resetList: true });
    });

    root.addEventListener('change', function (event) {
      if (!event.target.matches('[data-wb-track]')) return;
      state.track = event.target.value;
      render({ focusSelector: '[data-wb-track]', resetList: true });
    });

    render();
  };
})();
