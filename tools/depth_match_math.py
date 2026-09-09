"""Presentation formulas for the accepted depth-match definitions."""

from cancel_phase_math import row, mi, mn, mo, text, sub, frac, parens, equation, report_equations


def formulas():
    q, d1, d2 = mi('Q'), sub(mi('D'), mn(1)), sub(mi('D'), mn(2))
    both = lambda *items: row(*sum(([item, mo('∧')] for item in items[:-1]), []), items[-1])
    indicator = lambda value: row(text('𝟙'), parens(value, '{', '}'))
    condition = lambda value: indicator(value)
    v1 = sub(mi('v'), mn(1))
    equal = lambda a, b: row(a, mo('='), b)
    values = [
        condition(both(mi('A'), equal(q, d1))),
        row(v1, indicator(mi('E'))),
        row(v1, indicator(sub(mi('R'), mn(2)))),
        row(v1, indicator(sub(mi('B'), mn(1)))),
        condition(both(mi('A'), row(d1, mo('≥'), mn(100)), equal(q, row(mn(100), parens(frac(d1, mn(100)), '⌊', '⌋'))))),
        row(indicator(mi('A')), indicator(row(q, mo('≤'), d1)), text('max'), parens(row(mn(0), mo(','), mn(1), mo('−'), frac(row(d1, mo('−'), q), row(mn('0.01'), d1))))),
        row(v1, indicator(both(row(sub(d1, text('now')), mo('≠'), sub(d1, text('lag'))), equal(sub(mi('p'), text('1,now')), sub(mi('p'), text('1,lag')))))),
        row(v1, sub(v1, text('prev')), indicator(both(row(mi('Δt'), mo('≤'), mn(1000), text(' ms')), row(q, mo('≠'), sub(q, text('prev')))))),
        condition(both(mi('A'), sub(mi('R'), mn(2)), row(d2, mo('>'), mn(0)), equal(q, row(d1, mo('+'), d2)))),
        condition(both(row(q, mo('>'), d1), mi('A'), sub(mi('B'), mn(1)), mi('E'), text('100ms 内全撤余量'), text('无被动成交'))),
        row(v1, '<msup>' + mn(2) + row(mo('−'), frac(row(text('09:35'), mo('−'), sub(mi('t'), text('submit'))), row(mn(60), text(' s')))) + '</msup>'),
    ]
    n, c, pm = mi('N'), sub(mi('C'), text('side')), sub(mi('p'), mi('m'))
    entropy = row(mo('−'), '<munderover>' + mo('∑') + row(mi('m'), mo('='), mn(1)) + mn(5) + '</munderover>', pm, text('log'), parens(pm))
    persistent = row(frac(c, n), mo('×'), frac(entropy, row(text('log'), parens(mn(5)))))
    result = {f'DM{i:02}': equation(sub(mi('v'), mn(i)), value) for i, value in enumerate(values, 1)}
    result['DM12'] = equation(sub(mi('f'), text('12,side')), persistent)
    result['BINS'] = equation(pm, frac(sub(mi('C'), text('m,side')), c))
    result['AGGREGATE'] = equation(sub(mi('f'), text('k,side')), frac(row('<munder>' + mo('∑') + text('i ∈ 当日该侧已观察订单') + '</munder>', sub(mi('v'), text('k,i'))), n))
    output = {key: '<math xmlns="http://www.w3.org/1998/Math/MathML" displaystyle="true" data-equation="' + key + '">' + value + '</math>' for key, value in result.items()}
    shared = report_equations()
    output.update({key: shared[key] for key in ('RETURN', 'VWAP', 'IC', 'ICIR', 'OLS_MODEL')})
    return output


def render_math(template):
    for key, value in formulas().items():
        template = template.replace('__DEPTH_MATH_' + key + '__', value)
    if '__DEPTH_MATH_' in template:
        raise ValueError('Unknown depth-match formula')
    return template
