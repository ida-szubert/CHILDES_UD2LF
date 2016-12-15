import optparse
import json

optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="in_file", default="./lf_debug.txt", help="output of DepLambda")
optparser.add_option("-o", "--output", dest="out_file", default="./test_lf.txt", help="destination for re-formatted LFs")
optparser.add_option("-v", "--verbose", dest="verbose", default=True, help="whether to include original sentences and phenomena description")
optparser.add_option("-s", "--source", dest="source_file", default="/Users/ida/Desktop/RA/deplambda/lib_data/duck.txt", help="original source of the sentences")
(opts, _) = optparser.parse_args()


def read_in_lfs(in_file):
    expressions = []
    last_expression = ''
    for line in open(in_file, "r"):
        if line:
            split_line = line.split()
            if len(split_line) > 3:
                last_expression = ' '.join(split_line[3:])
            if line == "#####################\n":
                expressions.append(last_expression)
                last_expression = ''
    return expressions


def reformat(expressions, out_file, verbose, source_file):
    exp_dict = {}
    for i in range(len(expressions)):
        exp = expressions[i]
        split = separate_parens(exp).split()
        exp_list, _ = parse(split, 0)
        expression = list_to_string(exp_list)
        exp_dict[i] = expression
    if verbose:
        with open(out_file, "w") as out_f:
            with open(source_file, "r") as source:
                sent_counter = 0
                for l in source:
                    line = l.strip("\n")
                    if "{" in line:
                        sent = '"' + json.loads(line.lstrip("#"))['sentence'] + '"'
                        lf = exp_dict[sent_counter]
                        sent_counter += 1
                        out_f.write(sent)
                        out_f.write("\n\t")
                        out_f.write(lf)
                        out_f.write("\n")
                    elif line:
                        dscpt = "***" + line.lstrip("#") + " ***"
                        out_f.write(dscpt)
                        out_f.write("\n")
                    else:
                        out_f.write("\n")
    else:
        with open(out_file, "w") as out_f:
            for exp in exp_dict.values():
                out_f.write(exp)
                out_f.write("\n\n")


def list_to_string(exp_list):
    if isinstance(exp_list, str):
        return exp_list
    else:
        str_list = [exp_list[0]]
        if not exp_list[0].startswith("lambda"):
            str_list.append("(")
        for x in exp_list[1]:
            str_list.append(list_to_string(x))
            str_list.append(",")
        del str_list[-1]
        if not exp_list[0].startswith("lambda"):
            str_list.append(")")
        return ''.join(str_list)


def parse(expression, index):
    # expression can be a lambda expression or a function application
    # returns an expression an the index of the first element after the closing ) of the expression
    if expression[index+1] == "lambda":
        lam_var = "lambda " + expression[index+2].split(":")[0] + "_{ev}."
        body, next_index = parse(expression, index+3)
        return [lam_var, [body]], next_index+1
    else:
        pred = expression[index+1].split(":")[0]
        if '-' in pred:
            pred = pred.split("-")[2]
        args, next_index = parse_arguments(expression, [], index+2)
        return [pred, args], next_index


def parse_arguments(arg_string, args, next_index):
    next_piece = arg_string[next_index]
    if next_piece == ")":
        return args, next_index+1
    elif next_piece != "(":
        arg = next_piece.split(':')[0]
        if "-" in arg:
            arg = arg.split(':')[0].split("-")[2]
        args.append(arg)
        return parse_arguments(arg_string, args, next_index+1)
    else:
        arg, new_next_index = parse(arg_string, next_index)
        args.append(arg)
        return parse_arguments(arg_string, args, new_next_index)


def separate_parens(expression):
    new_expression = []
    for char in expression:
        if char == "(":
            new_expression.append("( ")
        elif char == ")":
            new_expression.append(" )")
        else:
            new_expression.append(char)
    return ''.join(new_expression)


exp_list = read_in_lfs(opts.in_file)
reformat(exp_list, opts.out_file, opts.verbose, opts.source_file)
