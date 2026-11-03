(function () {
  "use strict";

  window.JournalVariants = window.JournalVariants || {};

  window.JournalVariants.B = function (root, api) {
    var esc = api.esc;
    var days = api.data.days.slice().sort(function (a, b) {
      return String(b.date).localeCompare(String(a.date));
    });
    var months = Array.from(new Set(days.map(function (day) {
      return day.date.slice(0, 7);
    })));
    var latestMonth = months[0] || "all";
    var state = { month: latestMonth, track: "all", query: "" };
    var entries = days.map(function (day) {
      return { day: day, tasks: api.dayTasks(day) };
    });
    var weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];

    function monthLabel(month) {
      if (month === "all") return "全部日期";
      return month.slice(0, 4) + "年 " + Number(month.slice(5)) + "月";
    }

    function trackLabel(chain) {
      var track = api.track(chain.track);
      return track ? track.label : "研究记录";
    }

    function matchingEntries() {
      var tokens = state.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
      return entries.reduce(function (result, entry) {
        if (state.month !== "all" && entry.day.date.slice(0, 7) !== state.month) return result;
        var tasks = entry.tasks.filter(function (point) {
          if (state.track !== "all" && point.chain.track !== state.track) return false;
          var haystack = [entry.day.date, entry.day.headline, point.chain.label,
            point.chain.short, trackLabel(point.chain), point.note, point.outcome]
            .filter(Boolean).join(" ").toLocaleLowerCase();
          return tokens.every(function (token) { return haystack.indexOf(token) !== -1; });
        });
        if (tasks.length) result.push({ day: entry.day, tasks: tasks, total: entry.tasks.length });
        return result;
      }, []);
    }

    function taskRow(point) {
      return '<li class="b-task">' +
        '<div class="b-task-identity"><span class="b-task-track">' + esc(trackLabel(point.chain)) +
        '</span>' + api.chainLink(point.chain.id, point.chain.label) + '</div>' +
        '<div class="b-task-body"><p class="b-task-progress">' + esc(point.note || "本工作点未登记注解") + '</p>' +
        (point.outcome === "dropped" ? '<p class="b-task-outcome">历史方案未采用</p>' : point.outcome === "parked" ? '<p class="b-task-outcome">暂搁</p>' : "") + '</div>' +
        '<div class="b-task-action">' + api.pointLink(point, "详情") + '</div></li>';
    }

    function dayEntry(entry) {
      var day = entry.day;
      var weekday = weekdays[new Date(day.date + "T00:00:00Z").getUTCDay()];
      var isLatest = days.length && day.date === days[0].date;
      var countText = entry.tasks.length === entry.total
        ? "当天 " + entry.total + " 项工作"
        : "显示 " + entry.tasks.length + " / " + entry.total + " 项工作";
      return '<article class="b-entry' + (isLatest ? " is-latest" : "") + '" aria-labelledby="b-day-' + esc(day.date) + '">' +
        '<header class="b-date-column"><div class="b-date-topline"><time datetime="' + esc(day.date) + '">' +
        esc(day.date.slice(0, 4)) + ' / ' + esc(day.date.slice(5, 7)) + '</time>' +
        (isLatest ? '<span class="b-latest">最新记录</span>' : "") + '</div>' +
        '<div class="b-date-number"><span>' + esc(day.date.slice(8)) + '</span><span class="b-weekday">' + esc(weekday) + '</span></div>' +
        '<h2 id="b-day-' + esc(day.date) + '">' + esc(day.headline || "当日研究记录") + '</h2>' +
        '<p class="b-day-count">' + countText + '</p>' +
        '<button type="button" class="b-read-day subtle-button" data-b-day="' + esc(day.date) + '">阅读完整当日记录</button></header>' +
        '<div class="b-work-column"><div class="b-column-heading" aria-hidden="true"><span>研究链 / 方向</span><span>当天进展</span><span>记录</span></div>' +
        '<ol class="b-task-list">' + entry.tasks.map(taskRow).join("") + '</ol></div></article>';
    }

    root.innerHTML = '<section class="b-daybook" aria-label="按日日志">' +
      '<div class="b-heading"><div><h1>按日日志</h1><p>先看这一天做了什么，再沿着研究链继续读。</p></div>' +
      '<p class="b-heading-date">记录截至 <time datetime="' + esc(api.data.asOf) + '">' + esc(api.data.asOf) + '</time></p></div>' +
      '<div class="b-controls"><label class="b-search-label" for="b-query"><span>查找记录</span>' +
      '<input id="b-query" name="b-query" type="search" placeholder="链名、当天进展或日期" autocomplete="off"></label>' +
      '<label class="b-track-label" for="b-track"><span>研究方向</span><select id="b-track" name="b-track">' +
      '<option value="all">全部方向</option>' + api.data.tracks.map(function (track) {
        return '<option value="' + esc(track.id) + '">' + esc(track.label) + '</option>';
      }).join("") + '</select></label>' +
      '<button class="b-clear subtle-button" type="button" data-b-clear hidden>清除条件</button></div>' +
      '<nav class="b-month-nav" aria-label="选择日志月份"></nav>' +
      '<div class="b-reading-meta"><p class="b-scope"></p><p class="b-result-summary" role="status" aria-live="polite" aria-atomic="true"></p></div>' +
      '<div class="b-entries"></div><div class="b-bottom-nav"></div></section>';

    var monthNav = root.querySelector(".b-month-nav");
    var scope = root.querySelector(".b-scope");
    var summary = root.querySelector(".b-result-summary");
    var entryList = root.querySelector(".b-entries");
    var bottomNav = root.querySelector(".b-bottom-nav");
    var queryInput = root.querySelector("#b-query");
    var trackSelect = root.querySelector("#b-track");
    var clearButton = root.querySelector(".b-clear");

    function render() {
      var filtered = matchingEntries();
      var taskCount = filtered.reduce(function (count, entry) { return count + entry.tasks.length; }, 0);
      monthNav.innerHTML = '<span class="b-month-label">按月回看</span><div class="b-month-buttons">' +
        months.map(function (month) {
          var dayCount = days.filter(function (day) { return day.date.slice(0, 7) === month; }).length;
          return '<button type="button" class="b-month-button' + (state.month === month ? " is-active" : "") +
            '" data-b-month="' + esc(month) + '" aria-pressed="' + (state.month === month) +
            '" aria-label="' + esc(monthLabel(month)) + '，' + dayCount + ' 个记录日"><span>' +
            esc(month.slice(0, 4)) + ' / <strong>' + Number(month.slice(5)) + '</strong></span><span class="b-month-count">' + dayCount + ' 天</span></button>';
        }).join("") + '<button type="button" class="b-all-months' + (state.month === "all" ? " is-active" : "") +
        '" data-b-month="all" aria-pressed="' + (state.month === "all") + '">全部日期</button></div>';

      var inScope = days.filter(function (day) { return state.month === "all" || day.date.slice(0, 7) === state.month; });
      var rangeText = inScope.length
        ? inScope[inScope.length - 1].date + " 至 " + inScope[0].date
        : "暂无日期";
      scope.textContent = monthLabel(state.month) + " · " + rangeText + " · 最新在前";
      summary.textContent = filtered.length + " 个记录日 / " + taskCount + " 项工作";
      clearButton.hidden = state.track === "all" && !state.query;
      entryList.innerHTML = filtered.length
        ? filtered.map(dayEntry).join("")
        : '<div class="b-empty empty"><h2>没有匹配的工作记录</h2><p>可换个关键词、选择其他方向，或切换月份。</p>' +
          '<button type="button" class="button" data-b-reset>查看本月全部记录</button></div>';

      var monthIndex = months.indexOf(state.month);
      var olderMonth = monthIndex >= 0 ? months[monthIndex + 1] : null;
      var newerMonth = monthIndex > 0 ? months[monthIndex - 1] : null;
      bottomNav.innerHTML = state.month === "all" ? '<p>已展开全部登记日期。</p>' :
        '<p>已到' + esc(monthLabel(state.month)) + '的开头</p><div>' +
        (olderMonth ? '<button type="button" class="button" data-b-month="' + esc(olderMonth) + '">继续看 ' + esc(monthLabel(olderMonth)) + '</button>' : "") +
        (newerMonth ? '<button type="button" class="subtle-button" data-b-month="' + esc(newerMonth) + '">返回 ' + esc(monthLabel(newerMonth)) + '</button>' : "") + '</div>';
    }

    root.oninput = function (event) {
      if (event.target === queryInput) {
        state.query = queryInput.value;
        render();
      }
    };

    root.onchange = function (event) {
      if (event.target === trackSelect) {
        state.track = trackSelect.value;
        render();
      }
    };

    root.onclick = function (event) {
      var target = event.target.closest("button");
      if (!target || !root.contains(target)) return;
      if (target.hasAttribute("data-b-month")) {
        var wasAtBottom = Boolean(target.closest(".b-bottom-nav"));
        var month = target.getAttribute("data-b-month");
        state.month = month;
        render();
        var selected = monthNav.querySelector('[data-b-month="' + month + '"]');
        if (selected) selected.focus({ preventScroll: true });
        if (wasAtBottom) monthNav.scrollIntoView({ block: "start", behavior: "instant" });
      } else if (target.hasAttribute("data-b-clear") || target.hasAttribute("data-b-reset")) {
        state.track = "all";
        state.query = "";
        trackSelect.value = "all";
        queryInput.value = "";
        render();
        queryInput.focus({ preventScroll: true });
      } else if (target.hasAttribute("data-b-day")) {
        api.openDay(target.getAttribute("data-b-day"));
      } else if (target.hasAttribute("data-open-point")) {
        event.stopPropagation();
        api.openPoint(target.getAttribute("data-open-date"), target.getAttribute("data-open-point"));
      } else if (target.hasAttribute("data-open-chain")) {
        event.stopPropagation();
        api.openChain(target.getAttribute("data-open-chain"));
      }
    };

    render();
  };
})();
