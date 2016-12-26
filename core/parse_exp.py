def partition(exp, op, container):
    # one is always found because of the condition used in parse_exp
    index = next(index for index, value in enumerate(exp) if value == op)
    return container([container(exp[:index]), exp[index], container(exp[index+1:])])


def parse_exp(exp, operators, container=list):
    # print(repr(exp))
    for op in operators:
        if op in exp and exp != op:
            result = []
            for i in partition(exp, op, container):
                # print('\t', repr(i))
                if isinstance(i, container):
                    sub_result = parse_exp(i, operators, container)
                    if sub_result:  # only put in result non-empty stuf
                        if len(sub_result) == 1:
                            result.append(sub_result[0])
                        else:
                            result.append(sub_result)
                else:
                    result.append(i)
            return container(result)
    if isinstance(exp, container):
        return exp
    else:
        return container(exp)
