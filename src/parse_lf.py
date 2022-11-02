git def separate_parens(expression):
    new_expression = []
    for char in expression:
        if char == "(":
            new_expression.append(" ( ")
        elif char == ")":
            new_expression.append(" ) ")
        elif char == ".":
            new_expression.append(" . ")
        elif char == ",":
            new_expression.append(" ")
        else:
            new_expression.append(char)
    return ''.join(new_expression)


def parse(expression, index):
    # expression can be a lambda expression or a function application
    # returns an expression an the index of the first element after the closing ) of the expression
    if expression[index] == "lambda":
        typed_variable = expression[index+1]
        body, next_index = parse(expression, index+3)
        lam_args = [typed_variable, body]
        return ["lambda", lam_args], next_index+1
    else:
        pred = expression[index]
        args, next_index = parse_arguments(expression, [], index+2)
        return [pred, args], next_index


def parse_arguments(arg_string, args, next_index):
    next_piece = arg_string[next_index]
    if next_piece == ")":
        return args, next_index+1
    elif next_piece != "(":
        if arg_string[next_index+1] != "(":
            args.append(next_piece)
            return parse_arguments(arg_string, args, next_index+1)
        else:
            children_args, new_next_index = parse_arguments(arg_string, [], next_index+2)
            arg = [next_piece, children_args]
            args.append(arg)
            return parse_arguments(arg_string, args, new_next_index)
    else:
        arg, new_next_index = parse(arg_string, next_index)
        args.append(arg)
        return parse_arguments(arg_string, args, new_next_index)


def make_expression_dict():
    expression_dict = {}
    current_sent = ""
    with open("./LF_files/Adam_lf.txt", "r") as in_file:
        for line in in_file:
            if line.startswith("Sent:"):
                current_sent = line
            elif line.startswith("Sem:"):
                split = separate_parens(line.strip()[5:]).split()
                if split:
                    exp_list, _ = parse(split, 0)
                    expression_dict[current_sent] = exp_list
    return expression_dict


exp_dict = make_expression_dict()
with open("test_lf_parsing.txt", "w") as test_file:
    for sent, sem in exp_dict.items():
        test_file.write(sent)
        test_file.write(str(sem))
        test_file.write('\n\n')
