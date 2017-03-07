import optparse
import json

optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="in_file", default="./Adam.lf.json", help="output of DepLambda")
optparser.add_option("-c", "--comparison", dest="comp_file", default="./Adam.input.txt", help="input to DepLambda")
optparser.add_option("-o", "--output", dest="out_file", default="./Adam_lf.txt", help="destination for re-formatted LFs")
optparser.add_option("-w", "--write", dest="write_out", default=True, help="whether to write postprocessed LFs to file")
# optparser.add_option("-v", "--verbose", dest="verbose", default=True, help="whether to include original sentences and phenomena description")
# optparser.add_option("-s", "--source", dest="source_file", default="./conversion_debug.txt", help="original source of the sentences")
(opts, _) = optparser.parse_args()


#############################
# PARSING UDLamdba output
#############################
def reformat_json(expressions, out_file):
    with open(out_file, "w") as out_f:
        for i in range(len(expressions)):
            sent, exp = expressions[i]
            split = separate_parens(exp).split()
            exp_list = full_parse(split)
            expression = list_to_string(exp_list)
            out_f.write("Sent: " + sent + "\n")
            out_f.write("Sem: " + expression + "\n")
            out_f.write("example_end\n\n")


def list_to_string(exp_list):
    t = type(exp_list)
    # if isinstance(exp_list, str):
    if not isinstance(exp_list, list):
        return exp_list
    elif exp_list:
        str_list = [exp_list[0].replace(';', ':')]
        if not exp_list[0].startswith("lambda"):
            str_list.append("(")
        if len(exp_list) < 2:
            pass
        for x in exp_list[1]:
            str_list.append(list_to_string(x))
            str_list.append(",")
        del str_list[-1]
        if not exp_list[0].startswith("lambda"):
            str_list.append(")")
        return ''.join(str_list)
    else:
        return ''


def full_parse(expression):
    exp_list, _, lambdas_to_add = parse(expression, 0, [])
    for l in lambdas_to_add:
        exp_list = [l, [exp_list]]
    return exp_list


def parse(expression, index, lambdas_to_add):
    # expression can be a lambda expression or a function application
    # returns an expression an the index of the first element after the closing ) of the expression
    if len(expression) < index+2:
        # one-word expression
        return [], index, []
    # if len(expression) < index+1:
    #     pass
    if expression[index+1] == "lambda":
        lam_var = "lambda " + expression[index+2].split(":")[0] + "_{ev}."
        body, next_index, next_lambdas = parse(expression, index+3, lambdas_to_add)
        return [lam_var, [body]], next_index+1, next_lambdas
    else:
        pred = expression[index+1].split(":")[0]
        if '-' in pred:
            pred = pred.split("-", 2)[2]
            pred = pred.replace(';', ':')
        args, next_index = parse_arguments(expression, [], index+2, lambdas_to_add)
        if pred == "cast":
            return args[0], next_index, lambdas_to_add
        elif pred == "wh":
            lambdas_to_add.append("lambda " + args[0] + "_{e}.")
            if len(args) > 1:
                return [args[0], args[1:]], next_index, lambdas_to_add
            else:
                return args[0], next_index, lambdas_to_add
        else:
            return [pred, args], next_index, lambdas_to_add


def parse_arguments(arg_string, args, next_index, lambdas_to_add):
    next_piece = arg_string[next_index]
    if next_piece == ")":
        return args, next_index+1
    elif next_piece != "(":
        arg = next_piece.split(':')[0]
        if "-" in arg:
            arg = arg.split(':')[0].split("-", 2)[2]
            arg = arg.replace(';', ':')
        args.append(arg)
        return parse_arguments(arg_string, args, next_index+1, lambdas_to_add)
    else:
        arg, new_next_index, new_lambdas = parse(arg_string, next_index, lambdas_to_add)
        args.append(arg)
        return parse_arguments(arg_string, args, new_next_index, new_lambdas)


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


#############################
# Reading in UDLambda output
#############################


def read_in_lfs_json(converted, original, succces_suffix, failed_suffix, unreadable_suffix):
    # get dict of all input sentences
    input_dict = {}
    for line in open(original, "r"):
        sent = json.loads(line)["sentence"]
        input_dict[sent] = line

    # categorize output into successes and failures
    success = []
    failure = []
    # with open("./conversion_errors.txt", "w") as f:
    for line in open(converted, "r"):
        try:
            data = json.loads(line)
            if "deplambda_expression" not in data:
                failure.append(data["sentence"])
            else:
                success.append((data["sentence"], data["deplambda_expression"]))
        except ValueError:
            pass

    # identify examples for which no readable output was produced
    readable = [x[0] for x in success]
    readable.extend(failure)
    unreadable = []
    for sent in input_dict:
        if sent not in readable:
            unreadable.append(sent)
    print("total: "+str(len(input_dict)))
    print("converted: "+str(len(success)))
    print("failed with no messeage: "+str(len(failure)))
    print("failed with error message: "+str(len(unreadable)))
    # writing out to files
    with open(succces_suffix+"_sentences.txt", "w") as s_sent:
        with open(succces_suffix+".txt", "w") as s_data:
            for s, lam in success:
                s_sent.write(s+"\n")
                s_data.write(input_dict[s])
    with open(failed_suffix+"_sentences.txt", "w") as f_sent:
        with open(failed_suffix+".txt", "w") as f_data:
            for s in failure:
                f_sent.write(s+"\n")
                f_data.write(input_dict[s])
    with open(unreadable_suffix+"_sentences.txt", "w") as u_sent:
        with open(unreadable_suffix+".txt", "w") as u_data:
            for s in unreadable:
                u_sent.write(s+"\n")
                u_data.write(input_dict[s])

    return success, failure, unreadable


exp_list, failed, unreadable = read_in_lfs_json(opts.in_file, opts.comp_file, "./working", "./failed", "./unreadable")
if opts.write_out:
    reformat_json(exp_list, opts.out_file)


# def parse(expression, index):
#     # expression can be a lambda expression or a function application
#     # returns an expression an the index of the first element after the closing ) of the expression
#     if expression[index+1] == "lambda":
#         lam_var = "lambda " + expression[index+2].split(":")[0] + "_{ev}."
#         body, next_index = parse(expression, index+3)
#         return [lam_var, [body]], next_index+1
#     else:
#         pred = expression[index+1].split(":")[0]
#         if '-' in pred:
#             pred = pred.split("-")[2]
#         if pred == "cast":
#             if expression[index+2] != "(":
#                 return expression[index+2], index+3
#             else:
#                 return parse(expression, index+2)
#         else:
#             args, next_index = parse_arguments(expression, [], index+2)
#             return [pred, args], next_index

# def read_in_lfs_txt(in_file):
#     expressions = []
#     last_expression = ''
#     for line in open(in_file, "r"):
#         if line:
#             split_line = line.split()
#             if len(split_line) > 3:
#                 last_expression = ' '.join(split_line[3:])
#             if line == "#####################\n":
#                 expressions.append(last_expression)
#                 last_expression = ''
#     return expressions


#def reformat_txt(expressions, out_file, verbose=False, source_file=None):
#     exp_dict = {}
#     for i in range(len(expressions)):
#         exp = expressions[i]
#         split = separate_parens(exp).split()
#         exp_list = full_parse(split)
#         expression = list_to_string(exp_list)
#         exp_dict[i] = expression
#     if verbose:
#         with open(out_file, "w") as out_f:
#             with open(source_file, "r") as source:
#                 sent_counter = 0
#                 for l in source:
#                     line = l.strip("\n")
#                     if "{" in line:
#                         sent = '"' + json.loads(line.lstrip("#"))['sentence'] + '"'
#                         lf = exp_dict[sent_counter]
#                         sent_counter += 1
#                         out_f.write(sent)
#                         out_f.write("\n\t")
#                         out_f.write(lf)
#                         out_f.write("\n")
#                     elif line:
#                         dscpt = "***" + line.lstrip("#") + " ***"
#                         out_f.write(dscpt)
#                         out_f.write("\n")
#                     else:
#                         out_f.write("\n")
#     else:
#         with open(out_file, "w") as out_f:
#             for exp in exp_dict.values():
#                 out_f.write(exp)
#                 out_f.write("\n\n")

# def extract_failed_inputs(successful, failed, input_file, output_file1, output_file2):
#     readable = [x[0] for x in successful]
#     readable.extend(failed)
#     input_dict = {}
#     for line in open(input_file, "r"):
#         sent = json.loads(line)["sentence"]
#         input_dict[sent] = line
#     with open(output_file1+".txt", "w") as f1_out:
#         with open(output_file1+"_sentences.txt", "w") as f2_out:
#             for f in failed:
#                 f1_out.write(input_dict[f])
#                 f2_out.write(f+"\n")
#     unreadable_count = 0
#     with open(output_file2+".txt", "w") as f3_out:
#         with open(output_file2+"_sentences.txt", "w") as f4_out:
#             for s in input_dict.keys():
#                 if s not in readable:
#                     unreadable_count += 1
#                     f3_out.write(input_dict[s])
#                     f4_out.write(s+"\n")
#     return len(input_dict), unreadable_count
