"""Native MathML for the cancellation-phase report's mathematical definitions."""

from html import escape


def row(*parts):
    return '<mrow>' + ''.join(parts) + '</mrow>'


def token(tag, value):
    return f'<{tag}>{escape(str(value))}</{tag}>'


def mi(value):
    return token('mi', value)


def mn(value):
    return token('mn', value)


def mo(value):
    return token('mo', value)


def text(value):
    return token('mtext', value)


def sub(base, index):
    return '<msub>' + base + row(index) + '</msub>'


def square(base):
    return '<msup>' + base + mn(2) + '</msup>'


def frac(numerator, denominator):
    return '<mfrac>' + row(numerator) + row(denominator) + '</mfrac>'


def parens(value, left='(', right=')'):
    return row(mo(left), value, mo(right))


def summation(index, value):
    return row('<munder>' + mo('∑') + mi(index) + '</munder>', value)


def equation(left, right):
    return row(left, mo('='), right)


def report_equations():
    n, N, h, k, T, B = map(mi, ('n', 'N', 'h', 'k', 'T', 'B'))
    eh, gh = sub(mi('E'), h), sub(mi('G'), h)
    pair_count = row(n, parens(row(n, mo('−'), mn(1))))

    def cross(base, kind, scale=h):
        return sub(mi(base), row(text('cross-' + kind), mo(','), scale))

    def cross_count(index):
        return parens(row(square(n), mo('−'), summation(index, square(sub(n, mi(index))))))

    def cross_fit_term(first, second):
        return summation('j', row(text('sign'), parens(sub(mi(first), mi('j'))), sub(mi(second), mi('j'))))

    sharp = text('sharp')
    families = [
        frac(eh, row(pair_count, gh)),
        frac(cross('E', 'cycle'), row(cross_count('q'), gh)),
        row(frac(mn(1), mn(4)), parens(row(cross_fit_term('a', 'b'), mo('+'), cross_fit_term('b', 'a')), '[', ']')),
        row(frac(eh, row(square(N), gh)), mo('='), text('cph01'), mo('×'), frac(pair_count, square(N))),
        frac(cross('E', 'order'), row(cross_count('o'), gh)),
        frac(sub(mi('E'), sharp), row(pair_count, sub(mi('G'), sharp))),
        frac(cross('E', 'order', sharp), row(cross_count('o'), sub(mi('G'), sharp))),
    ]
    values = {f'FAMILY_{i}': value for i, value in enumerate(families, 1)}
    values.update({f'CPH_{i}': equation(text(f'cph{i:02}'), value) for i, value in enumerate(families, 1)})
    whk = sub(mi('w'), row(h, mo(','), k))
    mk = sub(mi('m'), k)
    sk_squared = square(parens(sub(mi('S'), k), '|', '|'))
    weighted_sum = lambda value: summation('k', row(mk, whk, value))
    exp = lambda value: row(text('exp'), parens(value))
    values.update(
        PHASE=equation(mi('φ'), row(text('age'), mo('mod'), T)),
        CYCLE=equation(mi('q'), parens(frac(text('age'), T), '⌊', '⌋')),
        BINS=equation(B, frac(T, row(mn(10), text(' ms')))),
        FOURIER=equation(sub(mi('S'), k), summation('i', exp(row(mo('−'), frac(row(mn(2), mi('π'), text('i'), k, sub(mi('b'), mi('i'))), B))))),
        FREQUENCIES=equation(k, row(mn(1), mo(','), mo('…'), mo(','), frac(B, mn(2)))),
        WEIGHT=equation(whk, exp(row(mo('−'), mn(2), square(mi('π')), square(parens(frac(row(k, h), T)))))),
        NORMALIZER=equation(gh, summation('k', row(mk, whk))),
        ENERGY=equation(eh, weighted_sum(parens(row(sk_squared, mo('−'), n)))),
        CYCLE_ENERGY=equation(cross('E', 'cycle'), weighted_sum(parens(row(sk_squared, mo('−'), summation('q', square(parens(sub(mi('S'), row(mi('q'), k)), '|', '|'))))))),
        ORDER_ENERGY=equation(cross('E', 'order'), weighted_sum(parens(row(sk_squared, mo('−'), summation('o', square(parens(sub(mi('S'), row(mi('o'), k)), '|', '|'))))))),
        SPLIT_A=equation(mi('a'), row(sub(mi('p'), row(mi('A'), mo(','), h)), mo('−'), frac(mn(1), B))),
        SPLIT_B=equation(mi('b'), row(sub(mi('p'), row(mi('B'), mo(','), h)), mo('−'), frac(mn(1), B))),
        RETURN=equation(sub(mi('r'), row(mi('d'), mo(','), mi('s'))), row(frac(sub(text('VWAP'), text('d,s,[09:44:00,09:45:00)')), sub(mi('P'), text('d,s,last trade <09:35:00'))), mo('−'), mn(1))),
        VWAP=equation(text('VWAP'), frac(summation('j ∈ W', row(sub(mi('P'), mi('j')), sub(mi('V'), mi('j')))), summation('j ∈ W', sub(mi('V'), mi('j'))))),
        ICIR=equation(text('ICIR'), frac(text('日均 Rank IC'), text('日度 Rank IC 标准差'))),
        MESSAGE_RATIO=frac(n, N),
        OLS_MODEL=equation(mi('r'), row(mi('α'), mo('+'), mi('β'), mi('x'), mo('+'), mi('ε'))),
        GROUP_SD=equation(text('标准差'), '<msqrt>' + text('有效日组内总体方差的平均') + '</msqrt>'),
    )
    centered = lambda name: parens(row(sub(mi(name), mi('i')), mo('−'), '<mover>' + mi(name) + mo('¯') + '</mover>'))
    values['IC'] = equation(text('IC'), frac(summation('i', row(centered('x'), centered('r'))), '<msqrt>' + row(summation('i', square(centered('x'))), summation('i', square(centered('r')))) + '</msqrt>'))
    return {key: '<math xmlns="http://www.w3.org/1998/Math/MathML" displaystyle="true" data-equation="' + key + '">' + value + '</math>' for key, value in values.items()}


def render_report_math(template):
    for key, value in report_equations().items():
        template = template.replace('__MATH_' + key + '__', value)
    if '__MATH_' in template:
        raise ValueError('Report contains an unknown mathematical expression')
    return template
