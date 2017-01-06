from sqf.base_tokenizer import tokenize

from sqf.exceptions import SQFParenthesisError, SQFParserError
from sqf.types import Statement, Code, Number, Boolean, Variable, Array, String
from sqf.keywords import KEYWORDS_MAPPING, ORDERED_OPERATORS, Keyword
from sqf.parser_types import Comment, Space, EndOfLine
from sqf.parse_exp import parse_exp


def identify_token(token):
    if isinstance(token, Comment):
        return token
    elif token == ' ':
        return Space()
    elif token == '\n':
        return EndOfLine()
    elif token in KEYWORDS_MAPPING:
        return KEYWORDS_MAPPING[token]
    elif token in ('true', 'false'):
        return Boolean(token == 'true')
    else:
        try:
            return Number(int(token))
        except ValueError:
            try:
                return Number(float(token))
            except ValueError:
                return Variable(token)


def parse_strings(all_tokens, identify_token):
    tokens = []
    string_mode = False
    string = ''
    for token in all_tokens:
        if token == '"':
            if string_mode:
                tokens.append(String(string))
                string = ''
                string_mode = False
            else:
                string_mode = True
        else:
            if string_mode:
                string += token
            else:
                tokens.append(identify_token(token))
    return tokens


def parse_comments(all_tokens):
    tokens = []
    bulk_comment_mode = False
    line_comment_mode = False
    comment = ''
    for token in all_tokens:
        if token == '/*' and not line_comment_mode:
            bulk_comment_mode = True
        elif token == '//' and not bulk_comment_mode:
            line_comment_mode = True

        if token == '*/' and bulk_comment_mode:
            bulk_comment_mode = False
            tokens.append(Comment(comment + token))
            comment = ''
        elif token == '\n' and line_comment_mode:
            line_comment_mode = False
            tokens.append(Comment(comment + token))
            comment = ''
        elif bulk_comment_mode or line_comment_mode:
            comment += token
        else:
            tokens.append(token)

    if bulk_comment_mode or line_comment_mode:
        tokens.append(Comment(comment))

    return tokens


def _analyse_tokens(tokens):
    ending = False
    if tokens and tokens[-1] == Keyword(';'):
        del tokens[-1]
        ending = True

    statement = parse_exp(tokens, ORDERED_OPERATORS, Statement)
    if isinstance(statement, Statement):
        statement._ending = ending
    else:
        statement = Statement([statement], ending=ending)

    return statement


def _analyse_array_tokens(tokens):
    result = []
    part = []
    first_comma_found = False
    for token in tokens:
        if token == Keyword(','):
            first_comma_found = True
            if not part:
                raise SQFParserError('Array syntax is `[item1, item2, ...]`')
            result.append(_analyse_tokens(part))
            part = []
        else:
            part.append(token)

    # an empty array is a valid array
    if part == [] and first_comma_found:
        raise SQFParserError('Array syntax is `[item1, item2, ...]`')
    result.append(_analyse_tokens(part))

    return result


def parse_block(all_tokens, analyse_tokens, analyse_array,
                start=0, block_lvl=0, parenthesis_lvl=0, rparenthesis_lvl=0):

    statements = []
    tokens = []
    i = start

    while i < len(all_tokens):
        token = all_tokens[i]

        if token == Keyword('['):
            expression, size = parse_block(all_tokens, analyse_tokens, analyse_array, i + 1,
                                           block_lvl=block_lvl,
                                           parenthesis_lvl=parenthesis_lvl,
                                           rparenthesis_lvl=rparenthesis_lvl+1)
            tokens.append(expression)
            i += size + 1
        elif token == Keyword('('):
            expression, size = parse_block(all_tokens, analyse_tokens, analyse_array, i + 1,
                                           block_lvl=block_lvl,
                                           parenthesis_lvl=parenthesis_lvl + 1,
                                           rparenthesis_lvl=rparenthesis_lvl)
            tokens.append(expression)
            i += size + 1
        elif token == Keyword('{'):
            expression, size = parse_block(all_tokens, analyse_tokens, analyse_array, i + 1,
                                           block_lvl=block_lvl + 1,
                                           parenthesis_lvl=parenthesis_lvl,
                                           rparenthesis_lvl=rparenthesis_lvl)
            tokens.append(expression)
            i += size + 1

        elif token == Keyword(']'):
            if rparenthesis_lvl == 0:
                raise SQFParenthesisError('Trying to close right parenthesis without them opened.')

            if statements:
                raise SQFParserError('A statement %s cannot be in an array' % Statement(statements))
            return Array(analyse_array(tokens)), i - start
        elif token == Keyword(')'):
            if parenthesis_lvl == 0:
                raise SQFParenthesisError('Trying to close parenthesis without opened parenthesis.')

            if tokens:
                statements.append(analyse_tokens(tokens))

            return Statement(statements, parenthesis=True), i - start
        elif token == Keyword('}'):
            if block_lvl == 0:
                raise SQFParenthesisError('Trying to close brackets without opened brackets.')

            if tokens:
                statements.append(analyse_tokens(tokens))

            return Code(statements), i - start
        elif token == Keyword(';'):
            tokens.append(Keyword(';'))
            statements.append(analyse_tokens(tokens))
            tokens = []
        else:
            tokens.append(token)
        i += 1

    if block_lvl != 0 or rparenthesis_lvl != 0 or parenthesis_lvl != 0:
        raise SQFParenthesisError('Brackets or parenthesis not closed')

    if tokens:
        statements.append(analyse_tokens(tokens))

    return Statement(statements), i - start


def parse(script):
    tokens = parse_strings(parse_comments(tokenize(script)), identify_token)
    return parse_block(tokens, _analyse_tokens, _analyse_array_tokens)[0]