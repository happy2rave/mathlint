"""Derivatives and integrals, worked out the way a course teaches them.

Derivatives are taken apart here rather than handed to SymPy, because the
interesting part is *which rule applies and why* — the product rule announces
its ``u`` and ``v``, the chain rule announces its inner function. Integrals lean
on SymPy's own by-hand integrator (``integral_steps``), whose rule tree is
turned back into sentences.
"""

from __future__ import annotations

import sympy as sp
from sympy.integrals import manualintegrate as mi

from ..i18n import msg
from ..parse.plain import read_as
from .solution import Solution

MAX_STEPS = 60
_U = sp.Symbol("u")


def differentiate_solution(expression: sp.Expr, variable: sp.Symbol) -> Solution:
    """Differentiate ``expression``, naming the rule behind every step."""
    solution = Solution(
        operation="diff",
        title=msg(
            "Derivative of {expression} with respect to {variable}",
            expression=_show(expression),
            variable=variable,
        ),
    )
    solution.add(msg("Start from"), expression=sp.Derivative(expression, variable))
    derivative = _derive(expression, variable, solution)
    tidy = sp.simplify(derivative)
    if tidy != derivative:
        solution.add(msg("Put it together and tidy up"), expression=tidy)
    else:
        solution.add(msg("Put it together"), expression=tidy)
    solution.result = tidy
    solution.summary = f"d/d{variable} [{_show(expression)}] = {_show(tidy)}"
    return solution


def _derive(expression: sp.Expr, variable: sp.Symbol, solution: Solution) -> sp.Expr:
    if len(solution.steps) > MAX_STEPS:
        return sp.diff(expression, variable)
    if not expression.has(variable):
        return sp.Integer(0)
    if expression == variable:
        return sp.Integer(1)

    if isinstance(expression, sp.Add):
        solution.add(
            msg("Differentiate a sum term by term: (f + g)' = f' + g'"),
            expression=expression,
        )
        return sp.Add(*[_derive(term, variable, solution) for term in expression.args])

    if isinstance(expression, sp.Mul):
        return _derive_product(expression, variable, solution)

    if isinstance(expression, sp.Pow):
        return _derive_power(expression, variable, solution)

    if isinstance(expression, sp.Function) and len(expression.args) == 1:
        return _derive_function(expression, variable, solution)

    solution.add(
        msg("SymPy works this piece out directly"),
        expression=sp.Derivative(expression, variable),
    )
    return sp.diff(expression, variable)


def _derive_product(expression: sp.Mul, variable: sp.Symbol, solution: Solution) -> sp.Expr:
    constants = [factor for factor in expression.args if not factor.has(variable)]
    varying = [factor for factor in expression.args if factor.has(variable)]
    coefficient = sp.Mul(*constants) if constants else sp.Integer(1)

    if constants and varying:
        solution.add(
            msg(
                "A constant factor comes along for the ride: (c f)' = c f', with c = {coefficient}",
                coefficient=_show(coefficient),
            ),
            expression=expression,
        )
    if len(varying) == 1:
        return coefficient * _derive(varying[0], variable, solution)

    first = varying[0]
    rest = sp.Mul(*varying[1:])
    if _is_quotient(rest):
        numerator, denominator = first, sp.Pow(rest.base, -rest.exp)
        solution.add(
            msg(
                "Quotient rule: (u/v)' = (u'v - uv') / v^2, with u = "
                "{numerator} and v = {denominator}",
                numerator=_show(numerator),
                denominator=_show(denominator),
            ),
            expression=numerator / denominator,
        )
        du = _derive(numerator, variable, solution)
        dv = _derive(denominator, variable, solution)
        return coefficient * (du * denominator - numerator * dv) / denominator**2

    solution.add(
        msg(
            "Product rule: (uv)' = u'v + uv', with u = {first} and v = {rest}",
            first=_show(first),
            rest=_show(rest),
        ),
        expression=first * rest,
    )
    du = _derive(first, variable, solution)
    dv = _derive(rest, variable, solution)
    return coefficient * (du * rest + first * dv)


def _derive_power(expression: sp.Pow, variable: sp.Symbol, solution: Solution) -> sp.Expr:
    base, exponent = expression.args

    if not exponent.has(variable):
        if base == variable:
            result = exponent * variable ** (exponent - 1)
            solution.add(
                msg(
                    "Power rule: d/d{variable} {variable}^n = n "
                    "{variable}^(n-1), with n = {exponent}",
                    variable=variable,
                    exponent=_show(exponent),
                ),
                expression=result,
            )
            return result
        solution.add(
            msg(
                "Chain rule with the power rule: (u^n)' = n u^(n-1) u', with "
                "u = {base} and n = {exponent}",
                base=_show(base),
                exponent=_show(exponent),
            ),
            expression=expression,
        )
        return exponent * base ** (exponent - 1) * _derive(base, variable, solution)

    if not base.has(variable):
        if base == sp.E:
            solution.add(
                msg("The exponential is its own derivative: (e^u)' = e^u u'"),
                expression=expression,
            )
            return expression * _derive(exponent, variable, solution)
        solution.add(
            msg("Exponential with base {base}: (a^u)' = a^u ln(a) u'", base=_show(base)),
            expression=expression,
        )
        return expression * sp.log(base) * _derive(exponent, variable, solution)

    solution.add(
        msg(
            "The variable is in the base and in the exponent, so use "
            "logarithmic differentiation: with y = u^v, ln y = v ln u, "
            "so y'/y = (v ln u)'"
        ),
        expression=expression,
    )
    inner = sp.expand(exponent * sp.log(base))
    solution.add(f"Differentiate {_show(inner)}", expression=sp.Derivative(inner, variable))
    return expression * _derive(inner, variable, solution)


def _derive_function(expression: sp.Expr, variable: sp.Symbol, solution: Solution) -> sp.Expr:
    inner = expression.args[0]
    name = type(expression).__name__
    outer_derivative = sp.diff(type(expression)(variable), variable)

    if inner == variable:
        solution.add(
            msg(
                "Standard derivative: d/d{variable} {name}({variable}) = {outer_derivative}",
                variable=variable,
                name=name,
                outer_derivative=_show(outer_derivative),
            ),
            expression=outer_derivative,
        )
        return outer_derivative

    solution.add(
        msg(
            "Chain rule: ({name}(u))' = {subs} * u', with u = {inner}",
            name=name,
            subs=_show(outer_derivative.subs(variable, _U)),
            inner=_show(inner),
        ),
        expression=expression,
    )
    return outer_derivative.subs(variable, inner) * _derive(inner, variable, solution)


def _is_quotient(expression: sp.Expr) -> bool:
    return isinstance(expression, sp.Pow) and expression.exp.is_Number and expression.exp < 0


def integrate_solution(
    expression: sp.Expr,
    variable: sp.Symbol,
    lower: sp.Expr | None = None,
    upper: sp.Expr | None = None,
) -> Solution:
    """Integrate ``expression``, explaining the method SymPy would use by hand."""
    definite = lower is not None and upper is not None
    title = msg(
        "Integral of {expression} with respect to {variable}",
        expression=_show(expression),
        variable=variable,
    )
    if definite:
        title += msg(", from {lower} to {upper}", lower=_show(lower), upper=_show(upper))
    solution = Solution(operation="integrate", title=title)
    integral = (
        sp.Integral(expression, (variable, lower, upper))
        if definite
        else sp.Integral(expression, variable)
    )
    solution.add(msg("Start from"), expression=integral)

    antiderivative = _written_out(expression, variable, solution)
    if antiderivative is None:
        rule = mi.integral_steps(expression, variable)
        _explain(rule, solution)
        antiderivative = sp.simplify(mi.manualintegrate(expression, variable))
    if antiderivative.has(sp.Integral):
        antiderivative = sp.simplify(sp.integrate(expression, variable))
        solution.add(
            msg("There is no standard by-hand method for this one, so this is SymPy's answer"),
            expression=antiderivative,
        )

    if not definite:
        solution.add(
            msg("An indefinite integral is only fixed up to a constant, so add + C"),
            expression=antiderivative + sp.Symbol("C"),
        )
        solution.result = antiderivative
        solution.summary = msg(
            "int {expression} d{variable} = {antiderivative} + C",
            expression=_show(expression),
            variable=variable,
            antiderivative=_show(antiderivative),
        )
        return solution

    solution.add(msg("Write the antiderivative as F"), expression=antiderivative)
    solution.add(
        msg(
            "A definite integral is F({upper}) - F({lower})", upper=_show(upper), lower=_show(lower)
        ),
        expression=(antiderivative.subs(variable, upper) - antiderivative.subs(variable, lower)),
    )
    value = sp.simplify(antiderivative.subs(variable, upper) - antiderivative.subs(variable, lower))
    solution.add(msg("Work it out"), expression=value)
    solution.result = value
    solution.summary = msg(
        "int from {lower} to {upper} of {expression} d{variable} = {value}",
        lower=_show(lower),
        upper=_show(upper),
        expression=_show(expression),
        variable=variable,
        value=_show(value),
    )
    return solution


def _written_out(expression: sp.Expr, variable: sp.Symbol, solution: Solution):
    """Partial fractions or a trigonometric substitution, in full, when one fits."""
    from .integration_methods import differentiates_back, partial_fractions, trig_substitution

    for method in (partial_fractions, trig_substitution):
        mark = len(solution.steps)
        try:
            antiderivative = method(expression, variable, solution)
        except (NotImplementedError, ValueError, TypeError, ZeroDivisionError):
            antiderivative = None
        if antiderivative is not None and differentiates_back(antiderivative, expression, variable):
            return antiderivative
        del solution.steps[mark:]
    return None


def _add(solution: Solution, text: str, expression: sp.Expr | None = None) -> None:
    solution.add(text, expression=_undummy(expression))


def _explain(rule, solution: Solution, depth: int = 0) -> None:
    """Turn one of SymPy's integration rules into a sentence, and recurse."""
    if depth > 8 or len(solution.steps) > MAX_STEPS:
        return
    name = type(rule).__name__

    if isinstance(rule, mi.AlternativeRule):
        _explain(rule.alternatives[0], solution, depth)
        return

    if isinstance(rule, mi.AddRule):
        _add(solution, msg("Integrate term by term"), expression=rule.integrand)
        for substep in rule.substeps:
            _explain(substep, solution, depth + 1)
        return

    if isinstance(rule, mi.ConstantTimesRule):
        _add(
            solution,
            msg("Pull the constant {constant} out in front", constant=_show(rule.constant)),
            expression=rule.constant * sp.Integral(rule.other, rule.variable),
        )
        _explain(rule.substep, solution, depth + 1)
        return

    if isinstance(rule, mi.URule):
        derivative = sp.diff(rule.u_func, rule.variable)
        _add(
            solution,
            msg(
                "Substitute u = {u_func}, so du = {derivative} d{variable}",
                u_func=_show(rule.u_func),
                derivative=_show(derivative),
                variable=rule.variable,
            ),
            expression=rule.integrand,
        )
        _explain(rule.substep, solution, depth + 1)
        return

    if isinstance(rule, mi.PartsRule):
        _add(
            solution,
            msg(
                "Integration by parts: int u dv = u v - int v du, with u = "
                "{u} and dv = {dv} d{variable}",
                u=_show(rule.u),
                dv=_show(rule.dv),
                variable=rule.variable,
            ),
            expression=rule.integrand,
        )
        _explain(rule.v_step, solution, depth + 1)
        _explain(rule.second_step, solution, depth + 1)
        return

    if isinstance(rule, mi.CyclicPartsRule):
        _add(
            solution,
            msg(
                "Integration by parts twice brings the original integral "
                "back, so move it to the left-hand side and solve for it"
            ),
            expression=rule.integrand,
        )
        return

    if isinstance(rule, mi.RewriteRule):
        _add(
            solution,
            msg("Rewrite it as {rewritten}", rewritten=_show(rule.rewritten)),
            expression=rule.rewritten,
        )
        _explain(rule.substep, solution, depth + 1)
        return

    if isinstance(rule, mi.PiecewiseRule):
        _add(
            solution, msg("This splits into cases; here is the main one"), expression=rule.integrand
        )
        if rule.subfunctions:
            _explain(rule.subfunctions[0][0], solution, depth + 1)
        return

    if isinstance(rule, mi.DontKnowRule):
        _add(
            solution,
            msg("There is no standard by-hand method for this integrand"),
            expression=rule.integrand,
        )
        return

    if name in _SPECIAL_FUNCTIONS:
        _add(
            solution,
            msg(
                "This integrand has no elementary antiderivative — the "
                "answer needs the {function}, which is not "
                "something you work out by hand",
                function=_SPECIAL_FUNCTIONS[name],
            ),
            expression=_evaluate(rule),
        )
        return

    text = _SIMPLE_RULES.get(name)
    if text is None:
        text = msg("Apply the standard {spaced}", spaced=_spaced(name))
    _add(solution, text, expression=_evaluate(rule))


#: Rules whose answers are written with special functions, not elementary ones.
_SPECIAL_FUNCTIONS = {
    "ErfRule": msg("error function erf"),
    "EiRule": msg("exponential integral Ei"),
    "LiRule": msg("logarithmic integral li"),
    "SiRule": msg("sine integral Si"),
    "CiRule": msg("cosine integral Ci"),
    "ShiRule": msg("hyperbolic sine integral Shi"),
    "ChiRule": msg("hyperbolic cosine integral Chi"),
    "FresnelCRule": msg("Fresnel integral C"),
    "FresnelSRule": msg("Fresnel integral S"),
    "PolylogRule": "polylogarithm",
    "UpperGammaRule": msg("upper incomplete gamma function"),
}


_SIMPLE_RULES = {
    "ConstantRule": msg("The integral of a constant c is c times the variable"),
    "PowerRule": msg("Power rule: int u^n du = u^(n+1)/(n+1), as long as n is not -1"),
    "NestedPowRule": msg("Power rule on the nested power"),
    "ReciprocalRule": msg("int 1/u du = ln|u|"),
    "ExpRule": msg("int a^u du = a^u / ln(a), and int e^u du = e^u"),
    "SinRule": msg("int sin(u) du = -cos(u)"),
    "CosRule": msg("int cos(u) du = sin(u)"),
    "SinhRule": msg("int sinh(u) du = cosh(u)"),
    "CoshRule": msg("int cosh(u) du = sinh(u)"),
    "TrigRule": msg("Standard trigonometric integral"),
    "Sec2Rule": msg("int sec^2(u) du = tan(u)"),
    "Csc2Rule": msg("int csc^2(u) du = -cot(u)"),
    "SecTanRule": msg("int sec(u) tan(u) du = sec(u)"),
    "CscCotRule": msg("int csc(u) cot(u) du = -csc(u)"),
    "ArctanRule": msg("int 1/(u^2 + 1) du = arctan(u)"),
    "ArcsinRule": msg("int 1/sqrt(1 - u^2) du = arcsin(u)"),
    "ArcsinhRule": msg("int 1/sqrt(u^2 + 1) du = arcsinh(u)"),
    "AtomicRule": msg("This is a standard integral"),
    "DerivativeRule": msg("The integral undoes the derivative"),
}


def _evaluate(rule) -> sp.Expr | None:
    try:
        return sp.simplify(rule.eval())
    except Exception:  # pragma: no cover - a rule that cannot evaluate on its own
        return None


def _undummy(expression: sp.Expr | None) -> sp.Expr | None:
    """SymPy's substitution variable is a Dummy printed as _u; write it as u."""
    if expression is None:
        return None
    dummies = expression.atoms(sp.Dummy)
    return expression.xreplace({dummy: sp.Symbol(dummy.name.lstrip("_")) for dummy in dummies})


def _spaced(name: str) -> str:
    stem = name[:-4] if name.endswith("Rule") else name
    spaced = "".join(" " + char.lower() if char.isupper() else char for char in stem)
    return spaced.strip() + " rule"


def _show(value: sp.Expr) -> str:
    return read_as(value)
