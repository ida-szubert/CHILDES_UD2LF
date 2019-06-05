import optparse
from collections import defaultdict

parser = optparse.OptionParser()
parser.add_option('-i', '--input', dest="in_file_template",
                  default="../conll/original_adam/Adam.{}x.Gibbon.conll10",
                  help="raw annotation filee in CoNLL format")
parser.add_option("-o", "--output", dest="out_file_template", default="../conll/original_adam/{}.txt",
                  help="")
parser.add_option("-p", "--output_problem", dest="out_file_prob", default="./conll/Adam.conll.conj_problematic.txt",
                  help="")
(opts, _) = parser.parse_args()


def select_parses(in_template, out_template, parse_filter, reverse=False, separate_files=False):
    selected = False
    sentence_buffer = []
    if not separate_files:
        open(out_template, 'w').close()
    # with open(out_file, "w") as out:
    for i in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
        in_file = in_template.format(i)
        if separate_files:
            out = open(out_template.format(i), "w")
        else:
            out = open(out_template, "a")
        for line in open(in_file, "r"):
            split_line = line.strip().split('\t')
            if len(split_line) > 1:
                word_index = split_line[0]
                word = split_line[1]
                lemma = split_line[2]
                upos = split_line[3]
                xpos = split_line[4]
                features = split_line[5]
                parent_index = split_line[6]
                edge_label = split_line[7].lower()
                enhanced_dep = split_line[8]
                misc = split_line[9]
                sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                        parent_index, edge_label, enhanced_dep, misc])

            else:
                #make parse_filter a list of filters
                #pass all filters to get only good examples
                if type(parse_filter) == list:
                    fits_filter = any([fit for (sb, fit) in [f(sentence_buffer) for f in parse_filter]])
                else:
                    sentence_buffer, fits_filter = parse_filter(sentence_buffer)
                selected = not(fits_filter) if reverse else fits_filter
                if selected:
                    for l in sentence_buffer:
                        out.write('\t'.join(l)+'\n')
                    out.write('\n')
                selected = False
                sentence_buffer = []


def underscore_filter(sentence_buffer, has_underscore=False):
    for i, word in enumerate(sentence_buffer):
        if '_' in word[1] and word[3] != 'PROPN':
            # has_underscore = True
            words = word[1].split('_')
            if words == ['', '']:
                return sentence_buffer, False
            num_inserted = len(words)-1
            start = i
            new_buffer = sentence_buffer[:start]
            for j, w in enumerate(words):
                entry = [x for x in word]
                entry[0] = str(start+1+j)
                entry[1] = w
                entry[2] = w
                new_buffer.append(entry)
            for k in sentence_buffer[start+1:]:
                entry = [x for x in k]
                entry[0] = str(int(k[0]) + num_inserted)
                new_buffer.append(entry)

            for entry in new_buffer:
                parent_index = int(entry[6])
                if parent_index > start:
                    entry[6] = str(parent_index+num_inserted)
            return underscore_filter(new_buffer, has_underscore=True)

    return sentence_buffer, has_underscore


def obj_promoted_filter(sentence_buffer):
    for word in sentence_buffer:
        if word[1] in ['much', 'any', 'more', 'two', 'some', 'one', 'own']:
            if word[7] in ['dobj', 'iobj']:
                return sentence_buffer, True
    return sentence_buffer, False


def copula_PP_filter(sentence_buffer):
    # find potential copular verbs
    cop_indices = []
    for word in sentence_buffer:
        if word[2] in ['be', '~be']:
            cop_indices.append(word[0])
    # find potential nominal heads
    nominal_indices = []
    for word in sentence_buffer:
        if word[6] in cop_indices:
            if word[7] == 'nmod':
                if word[3] in ['NOUN', 'PROPN', 'PRON']:
                    nominal_indices.append(word[0])
    # find prepositions heading copular constructions
    for word in sentence_buffer:
        if word[7] == 'case':
            if word[6] in nominal_indices:
                return sentence_buffer, True
    return sentence_buffer, False


def fused_relative_filter(sentence_buffer):
    # was supposed to be something else, but turns out to pick up fused relative clauses
    # it shouldn't, accoridng to UD guidelines
    # but it seems our annotators decided on a different analysis
    parent_indices = []
    for word in sentence_buffer:
        if word[2] in ['why', 'what', 'which', 'who', 'how', 'where', 'when']:
            parent_indices.append(int(word[6]))
    for parent in parent_indices:
        if sentence_buffer[parent][7] == 'ccomp':
            return sentence_buffer, True
    return sentence_buffer, False


def complementizer_filter(sentence_buffer):
    # find sentences with wh words within a clause dominated by xcomp,ccomp, or acl
    parent_indices = []
    for word in sentence_buffer:
        if word[2] in ['why', 'what', 'which', 'who', 'how', 'where', 'when']:
            parent_indices.append(int(word[6]))
    for parent in parent_indices:
        if sentence_buffer[parent-1][7] in ['xcomp', 'ccomp', 'acl']:
            return sentence_buffer, True
    return sentence_buffer, False


def select_underscore():
    select_parses(opts.in_file_template, opts.out_file_template.format("underscore"), underscore_filter)


def select_obj_promoted():
    select_parses(opts.in_file_template, opts.out_file_template.format("obj_promoted"), obj_promoted_filter)


def select_pp_copula():
    select_parses(opts.in_file_template, opts.out_file_template.format("PP_copula"), copula_PP_filter)


def select_fused_relative():
    select_parses(opts.in_file_template, opts.out_file_template.format("fused_relative"), fused_relative_filter)


def select_complementizer():
    select_parses(opts.in_file_template, opts.out_file_template.format("complementizer"), complementizer_filter)


def select_unproblematic():
    select_parses("./conll/original/Adam.conll.{}.txt", "./conll/original/Adam.conll.{}.filtered.txt",
                  [underscore_filter, obj_promoted_filter, copula_PP_filter], reverse=True, separate_files=True)


def reverse_conjunction(in_file_template, out_file_template, out_file_problematic):
    # empty out_file_problematic
    open(out_file_problematic, 'w').close()

    sentence_buffer = []
    for i in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
        out_file = out_file_template.format(i, "conj_fixed")
        in_file = in_file_template.format(i)
        with open(out_file, "w") as out, open(out_file_problematic, "a") as out_prob:
            for line in open(in_file, "r"):
                split_line = line.strip().split('\t')
                if len(split_line) > 1:
                    word_index = split_line[0]
                    word = split_line[1]
                    lemma = split_line[2]
                    upos = split_line[3]
                    xpos = split_line[4]
                    features = split_line[5]
                    parent_index = split_line[6]
                    edge_label = split_line[7].lower()
                    enhanced_dep = split_line[8]
                    misc = split_line[9]
                    sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                            parent_index, edge_label, enhanced_dep, misc])
                else:
                    # look for conj-cc groups
                    correct = True
                    group_indices = []
                    for entry in sentence_buffer:
                        if entry[7] == 'conj':
                            head = entry[6]
                            for entry2 in sentence_buffer:
                                if entry2[7] == 'cc' and entry2[6] == head:
                                    correct = False
                                    group_indices.append((head, entry[0], entry2[0]))

                    num_heads = len(group_indices)
                    num_unique_heads = len(set([x[0] for x in group_indices]))
                    if not correct:
                        # should it be fixed or is the case problematic? It's problematic if
                        # there's more than 1 conjunction with the same head
                        if num_heads > num_unique_heads:
                            for l in sentence_buffer:
                                out_prob.write('\t'.join(l)+'\n')
                            out_prob.write('\n')
                        else:
                            for head, conj, cc in group_indices:
                                sentence_buffer[int(cc)-1][6] = conj
                            for l in sentence_buffer:
                                out.write('\t'.join(l)+'\n')
                            out.write('\n')
                    else:
                        # pass
                        for l in sentence_buffer:
                            out.write('\t'.join(l)+'\n')
                        out.write('\n')

                    sentence_buffer = []

# select_unproblematic()
# reverse_conjunction(opts.in_file_template, "./conll/original/Adam.conll.{}.txt", opts.out_file_prob)

# to process files downloaded from Arborator:
# automatically retrofit the parses to UDv2 with respect to conjunction:
# reverse_conjunction("Adam.{}x.Gibbon.conll10", "./conll/original/Adam.{}x.conj_fixed.Gibbon.conll10",
# "./conll/Adam.conll.conj_problematic.txt")
# select only the sentences which didn't have any problems; the rest has been fixed and is now in one of the small batches
# select_unproblematic()s
select_complementizer()
