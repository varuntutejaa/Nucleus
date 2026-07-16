import operator

OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
}


def evaluate(value, rule):

    op = OPS[rule["operator"]]

    return op(float(value), rule["threshold"])