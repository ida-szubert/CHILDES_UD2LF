import optparse
import json
import re
import numpy as np


#############################
# PARSING UDLamdba output
#############################
def reformat_json(expressions, out_file, sample_size=0, sample_out=None, eval_out=None):
    # writing out final LFs
    # optionally extracting sample for gold standard annotation
    counter = 0
    sample = []
    if sample_size > 0:
        sample_indices = np.random.choice(len(expressions), 100, replace=False)
    else:
        sample_indices = []

    with open(out_file, "w") as out_f:
        for i in range(len(expressions)):
            sent, exp = expressions[i]
            split = separate_parens(exp).split()
            # problems with nonsensical LF caused by wrong UD annotation in Hebrew
            # they cannot even be parsed
            try:
                exp_list = full_parse(split)
                expression = list_to_string(exp_list)
            except TypeError:
                expression = None
            if expression:
                out_f.write("Sent: " + sent + "\n")
                out_f.write("Sem: " + expression + "\n")
                out_f.write("example_end\n\n")
                if counter in sample_indices:
                    sample.append((sent, expression))
            counter += 1
    if sample_size > 0:
        with open(sample_out, "w") as s_out, open(eval_out, "w") as e_out:
            for sent, expression in sample:
                s_out.write("Sent: " + sent + "\n")
                s_out.write("Sem: " + "\n")
                s_out.write("example_end\n\n")
                e_out.write("Sent: " + sent + "\n")
                e_out.write("Sem: " + expression + "\n")
                e_out.write("example_end\n\n")


def list_to_string(exp_list):
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
    if expression[index+1] == "lambda":
        variable, type = expression[index+2].split(":")
        if type == "ev":
            lam_var = "lambda " + variable + "_{r}."
            body, next_index, next_lambdas = parse(expression, index+3, lambdas_to_add)
            return [lam_var, [body]], next_index+1, next_lambdas
        elif type == "v":
            return parse_bare_nominal(expression, index, lambdas_to_add)
        # signature = "_{r}." if type == "ev" else "_{e}."
        # lam_var = "lambda " + variable + signature
        # body, next_index, next_lambdas = parse(expression, index+3, lambdas_to_add)
        # return [lam_var, [body]], next_index+1, next_lambdas
    else:
        pred = expression[index+1].split(":")[0]
        if '-' in pred:
            pred = extract_word(pred)
            pred = pred.replace(';', ':')
        args, next_index = parse_arguments(expression, [], index+2, lambdas_to_add)
        if pred == "cast":
            return args[0], next_index, lambdas_to_add
        elif pred == "wh":
            wh_type = expression[index+1].split(":")[1]
            if wh_type == "<<ev,v>,<ev,v>>":
                type_sig = "_{<r,t>}."
            elif wh_type == "<d,d>":
                type_sig = "_{<<e,e>,e>}."
            else:
                type_sig = "_{e}."
            lambdas_to_add.append("lambda " + args[0] + type_sig)
            if len(args) > 1:
                return [args[0], args[1:]], next_index, lambdas_to_add
            else:
                return args[0], next_index, lambdas_to_add
        else:
            return [pred, args], next_index, lambdas_to_add


def parse_bare_nominal(expression, index, lambdas_to_add):
    var = expression[index+2].split(":")[0]
    nominal, next_index = parse_arguments(expression, [], index+3, lambdas_to_add)
    body = [var]
    body.extend(nominal)
    # body = [var, nominal]
    return ["BARE", body], next_index, lambdas_to_add


def parse_arguments(arg_string, args, next_index, lambdas_to_add):
    next_piece = arg_string[next_index]
    if next_piece == ")":
        return args, next_index+1
    elif next_piece != "(":
        arg = next_piece.split(':')[0]
        if "-" in arg:
            arg = extract_word(arg)
            arg = arg.replace(';', ':')
        args.append(arg)
        return parse_arguments(arg_string, args, next_index+1, lambdas_to_add)
    else:
        arg, new_next_index, new_lambdas = parse(arg_string, next_index, lambdas_to_add)
        args.append(arg)
        return parse_arguments(arg_string, args, new_next_index, new_lambdas)


def extract_word(arg):
    token = arg.split(':')[0]
    word_signature = "w-\d+-"
    parts = re.split(word_signature, token)[1:]
    for i in range(1, len(parts)):
        parts[i] = parts[i].split("|")[1] if "|" in parts[i] else parts[i]
    return ''.join(parts)


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


def read_in_lfs_json(converted, original, log_dir):
    # get dict of all input sentences
    line_count = 0
    input_dict = {}
    for line in open(original, "r"):
        line_count += 1
        sent = json.loads(line)["sentence"]
        input_dict[sent] = line

    # categorize output into successes and failures
    # success_count = 0
    success = []
    # failure_count = 0
    failure = []
    for line in open(converted, "r"):
        try:
            data = json.loads(line)
            if "deplambda_expression" not in data:
                failure.append(data["sentence"])
                # failure_count += 1
            else:
                success.append((data["sentence"], data["deplambda_expression"]))
                # success_count += 1
        except ValueError:
            pass

    # identify examples for which no readable output was produced
    readable = [x[0] for x in success]
    readable.extend(failure)
    # unreadable_count = 0
    unreadable = []
    for sent in input_dict:
        if sent not in readable:
            unreadable.append(sent)
            # unreadable_count += 1

    # unique_succes = len(success)
    # unique_failure = len(failure)
    # unique_unreadable = len(unreadable)
    print("total: {} (unique: {})".format(str(line_count), str(len(input_dict))))
    print("converted: {} (unique: {})".format(str(len(success)), str(len(set(success)))))
    print("failed with no message: {} (unique: {})".format(str(len(failure)), str(len(set(failure)))))
    print("failed with error message: {} (unique: {})".format(str(len(unreadable)), str(len(set(unreadable)))))
    # writing out to files
    succes_suffix = log_dir + "working"
    failed_suffix = log_dir+"failed"
    unreadable_suffix = log_dir+"unreadable"
    with open(succes_suffix+"_sentences.txt", "w") as s_sent:
        with open(succes_suffix+".txt", "w") as s_data:
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


optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="in_file", default="../LF_files/full_adam/adam.all.lf.json", help="output of DepLambda")
optparser.add_option("-c", "--comparison", dest="comp_file", default="../conll/full_adam/adam.all.input.txt", help="input to DepLambda")
optparser.add_option("-o", "--output", dest="out_file", default="../LF_files/full_adam/adam.all_lf.txt", help="destination for re-formatted LFs")
optparser.add_option("-w", "--write", dest="write_out", default=True, help="whether to write postprocessed LFs to file")
optparser.add_option("-l", "--logdir", dest="log_dir", default="../logs/", help="directory for log files")
optparser.add_option("-s", "--sample", dest="sample", default=0, help="size of the required sample of the final LFs; if size=0, no sample is extracted")
optparser.add_option("-t", "--sample_file", dest="sam_file", default="../LF_files/sample_gold_english.txt", help="file to write out templates for the sample")
optparser.add_option("-u", "--sample_eval_file", dest="sam_eval_file", default="../LF_files/sample_output_english.txt", help="file to write out converter outputs for the sample")
(opts, _) = optparser.parse_args()


exp_list, failed, unreadable = read_in_lfs_json(opts.in_file,
                                                opts.comp_file,
                                                opts.log_dir)

if opts.write_out:
    reformat_json(exp_list, opts.out_file, sample_size=opts.sample, sample_out=opts.sam_file, eval_out=opts.sam_eval_file)

