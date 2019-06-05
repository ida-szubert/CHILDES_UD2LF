import optparse
from childes_reader import CHILDESCorpusReader
from os import listdir
from os.path import isfile, join
import xml
from collections import defaultdict
import json
# import numpy as np
# from matplotlib import pyplot as plt

# Things done in this file:
# 1. repairing Adam batches 9 and 10 (fixing words and lemmas in the annotated files)
# 2. fixing Hebrew annotation to follow word-lemma order
# 3. adding CHILDES POS annotation to words and creating parse files for each CHILDES session
# 4. finding and printing out CHILDES sentences for which we miss parses


flatten = lambda l: [item for sublist in l for item in sublist]


def order_dict_by_value(dict):
    return sorted(dict.items(), key=lambda x: x[1], reverse=True)

def order_dict_by_key(dict):
    return sorted(dict.items(), key=lambda x: x[0], reverse=False)

#####################################################################
# READ IN CONLL FILES
# including producing stats and selecting examples
# and dealing with 
# probably straight from CHILDES and never preprocessed (although it's not clear how that happened)
# I have preprocessed version from when I send those sentences to be parsed
def read_in_parses(in_file_template, batch_numbers, invalid_parse_file, english, with_counts=False):
    """
    Reads in a list of UD parse CoNLL files into a single dictionary
    Writes out invalid parses to a separate file
    Distinguishes between Hebrew and English data bc they have the opposite order of word and lemma
    Can find sentences with particular depenencies and print them out
    :param in_file_template:
    :param batch_numbers:
    :param invalid_parse_file:
    :param english: Bool, English processed if T, Hebrew if F
    :param with_counts: Bool, if T returns additional dictionary with occurence counts for each utterance
    :return:
    """
    sent_set = set()
    invalid_parse_count = 0
    valid_parse = True
    annotation_dict = {}
    if with_counts:
        count_dict = defaultdict(int)
    sentence_buffer = []
    with open(invalid_parse_file, "w") as ip:
        for i in batch_numbers:
            in_file = in_file_template.format(i)
            for line in open(in_file, "r"):
                split_line = line.strip().split('\t')
                if len(split_line) > 1:
                    word_index = split_line[0]
                    word = split_line[1] if english else split_line[2]
                    lemma = split_line[2] if english else split_line[1]
                    upos = split_line[3]
                    xpos = split_line[4]
                    features = split_line[5]
                    parent_index = split_line[6]
                    edge_label = split_line[7].lower()
                    enhanced_dep = split_line[8]
                    misc = split_line[9]
                    if edge_label == 'incroot':
                        edge_label = 'root'
                    if edge_label == 'subj':
                        edge_label = 'nsubj'
                    # new Adam annotations (batches 9 and 10) differ from old ones
                    # in not using recontructed lemmas in place of various contractions
                    # and separating "have to", "thank you" etc into individual words
                    # Here we correct that
                    add_word = True
                    if english:
                        word, add_word = modify_new_adam_words(word, lemma, sentence_buffer)
                    if add_word:
                        sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                                parent_index, edge_label, enhanced_dep, misc])

                    if edge_label in ['obj','mod','app','link','com','jct','cmod','coord','njct','pred','pobj','inf',
                                      'pq','??','cjct','srl','xjct','?','_','xmod']:
                        valid_parse = False
                else:
                    # one full parse read
                    if valid_parse:
                        whole_sent = ' '.join(token[1] for token in sentence_buffer)
                        if with_counts:
                            words_only = [l[1] for l in sentence_buffer if l[3] != 'PUNCT']
                            sentence = ' '.join(words_only)
                            count_dict[sentence] += 1
                            if whole_sent not in sent_set:
                                sent_set.add(whole_sent)
                                annotation_dict[sentence] = sentence_buffer
                        elif whole_sent not in sent_set:
                            sent_set.add(whole_sent)
                            words_only = [l[1] for l in sentence_buffer if l[3] != 'PUNCT']
                            sentence = ' '.join(words_only)
                            other_sentence = ' '.join([change_s_be(x) for x in words_only])
                            another_sentence = ' '.join([x.split('(')[0] if '(' in x and ')' in x else x for x in words_only])
                            sents = {sentence, another_sentence, other_sentence}
                            for s in sents:
                                annotation_dict[s] = sentence_buffer
                    else:
                        invalid_parse_count += 1
                        for token in sentence_buffer:
                            ip.write('\t'.join(token)+'\n')
                        ip.write('\n')
                    valid_parse = True
                    sentence_buffer = []
    print("Number of sentences: {0:d}".format(len(sent_set)))
    print("Invalid parses: {0:d}".format(invalid_parse_count))
    if with_counts:
        return annotation_dict, count_dict
    else:
        return annotation_dict


def read_conll_file(in_file, english):
    sent_set = set()
    parse_dict = {}
    sentence_buffer = []
    for line in open(in_file, "r"):
        split_line = line.strip().split('\t')
        if len(split_line) > 1:
            word_index = split_line[0]
            word = split_line[1] if english else split_line[2]
            lemma = split_line[2] if english else split_line[1]
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
            whole_sent = ' '.join(token[1] for token in sentence_buffer)
            if whole_sent not in sent_set:
                sent_set.add(whole_sent)
                words_only = [l[1] for l in sentence_buffer if l[3] != 'PUNCT']
                sentence = ' '.join(words_only)
                other_sentence = ' '.join([change_s_be(x) for x in words_only])
                another_sentence = ' '.join([x.split('(')[0] if '(' in x and ')' in x else x for x in words_only])
                sents = {sentence, another_sentence, other_sentence}
                for s in sents:
                    parse_dict[s] = sentence_buffer
                sentence_buffer = []
    return parse_dict


def modify_new_adam_words(word, lemma, sentence_buffer):
    add_word = True
    prev_word = ""
    if sentence_buffer:
        prev_word = sentence_buffer[-1][1]
    if word == "'s":
        word = lemma
    if word == "'ll":
        word = "~will"
    if word in ["'re", "'m"]:
        word = "~be"
    if word == "aren":
        word = "be"
    if word == "'t":
        if prev_word == "won":
            sentence_buffer[-1][1] = "will"
            sentence_buffer[-1][2] = "will"
        word = "~not"
    if word in ["didn", "don", "doesn"]:
        word = "do"
    if word == "'ve":
        word = "~have"
    if word == "'d":
        word = "~genmod"
    if word == "to" and prev_word == "have":
        add_word = False
        sentence_buffer[-1][1] = "have_to"
        sentence_buffer[-1][2] = "have_to"
    elif word == "you" and prev_word == "thank":
        add_word = False
        sentence_buffer[-1][1] = "thank_you"
        sentence_buffer[-1][2] = "thank_you"
    return word, add_word


def filter_parse_dict(parse_dict, dep_filter, out_file):
    """
    Select sentences with particular dependencies
    and print out parses to the out_file
    :param parse_dict:
    :param dep_filter:
    :return:
    """
    seen_sents = set()
    for sent, buffer in parse_dict.items():
        for token in buffer:
            if token[7] in dep_filter:
                seen_sents.add(tuple([tuple(token) for token in buffer]))
                break
    with open(out_file, "w") as out_f:
        for buffer in seen_sents:
            for token in buffer:
                out_f.write('\t'.join(token)+'\n')
            out_file.write("\n")


# def filter_with_sent_list(parse_dict, sent_list):
#     new_dict = {}
#     for s in sent_list:
#         new_dict[s] = parse_dict[s]
#     return new_dict


def read_parse_dict_from_json(in_file):
    parse_dict = {}
    for line in open(in_file, "r"):
        sent = json.loads(line)["sentence"]
        word_info = json.loads(line)["words"]
        parse = []
        for w in word_info:
            word_index = w["index"]
            word = w["word"]
            lemma = w["lemma"]
            upos = w["pos"]
            xpos = w["fpos"]
            features = "_"
            parent_index = w["head"]
            edge_label = w["dep"]
            enhanced_dep = "_"
            misc = "_"
            parse.append([word_index, word, lemma, upos, xpos, features,
                          parent_index, edge_label, enhanced_dep, misc])
        parse_dict[sent] = parse

    return parse_dict


def get_dep_stats(parse_dict, write_out=True):
    dep_freq = defaultdict(int)
    all_sents = set([tuple([tuple(token) for token in buffer]) for buffer in parse_dict.values()])
    for buffer in all_sents:
        for token in buffer:
            dep_freq[token[7]] += 1
    if write_out:
        # for d, n in order_dict_by_value(dep_freq):
        for d, n in order_dict_by_key(dep_freq):
            print("{} : {}".format(d, str(n)))
    return dep_freq


def get_dep_stats_with_repetition(parse_dict, sent_count_dict, write_out=True):
    dep_freq = defaultdict(int)
    total_count = sum(sent_count_dict.values())
    for sent, buffer in parse_dict.items():
        count = sent_count_dict[sent]
        for token in buffer:
            dep_freq[token[7]] += float(count)/total_count
    if write_out:
        for d, n in order_dict_by_value(dep_freq):
            print("{} : {}".format(d, str(round(n,4))))
    return dep_freq


def dep_stats_difference(parse_dict1, parse_dict2):
    dep_stats1 = get_dep_stats(parse_dict1, write_out=False)
    dep_stats2 = get_dep_stats(parse_dict2, write_out=False)
    diff_dict = {}
    for k1, v1 in dep_stats1.items():
        diff_dict[k1] = float(dep_stats2[k1]) / v1
    for d, n in order_dict_by_value(diff_dict):
        print("{} & {} & {}\\\\".format(d, dep_stats1[d], str(round(n,2))))


#####################################################################
# FIX ADAM BATCHES 9 & 10
# connl files dumped from Arborator have strange words and lemmas
# probably straight from CHILDES and never preprocessed (athough it's not clear how that happened)
# I have preprocessed version from when I send those sentences to be parsed
def repair_adam_data(original_file, annotated_file, fixed_file):
    """
    Read in preprocessed file with correct words and lemmas but wrong parses
    and the file with correct parses but wrong words and lemmas
    match parses and merge to a wholy correct version
    Sometimes matching is too hard in which case the parse is excluded from the fixed_file
    :param original_file:
    :param annotated_file:
    :param fixed_file:
    :return:
    """
    original_dict = {}
    sentence_buffer = []
    for line in open(original_file, "r"):
        split_line = line.strip().split('\t')
        if len(split_line) > 1:
            word = split_line[1]
            lemma = split_line[2]
            if '~' in lemma:
                xpos = split_line[4]
                word1, word2, lemma1, lemma2, pos1, pos2 = process_complex_word(lemma, xpos, word, fix_mode=True)
                sentence_buffer.extend([[word1, lemma1], [word2, lemma2]])
            elif "_" in lemma:
                words = lemma.split("_")
                sentence_buffer.extend([[w, w] for w in words])
            else:
                sentence_buffer.append([word, lemma])
        else:
            lemma_sentence = ' '.join([x[1] for x in sentence_buffer])
            original_dict[lemma_sentence] = [x[0] for x in sentence_buffer]
            sentence_buffer = []
    with open(fixed_file, "w") as fix_f:
        total = 0
        found = 0
        for line in open(annotated_file, "r"):
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
                if lemma in ["~be&3S", "~be&1S"]:
                    lemma = "~be"
                if "&dn" in lemma:
                    lemma = lemma.split("&dn")[0]+"&dn"
                if "&dadj" in lemma:
                    lemma = lemma.split("&dadj")[0]+"&dadj"
                if "&dv" in lemma:
                    lemma = lemma.split("&dv")[0]+"&dv"
                if "&13S" in lemma:
                    lemma = lemma.split("&13S")[0]
                sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                        parent_index, edge_label, enhanced_dep, misc])
            else:
                total += 1
                lemmas = [x[2] for x in sentence_buffer]
                lemma_sentence = ' '.join(lemmas)
                lemma_sentence_2 = ' '.join([l.replace("&", "-") for l in lemmas])
                lemma_sentence_3 = ' '.join([l.split("&")[0] for l in lemmas])
                sentences = [lemma_sentence, lemma_sentence_2, lemma_sentence_3]
                if not any([s in original_dict for s in sentences]):
                    print("Things went wrong :(")
                    print(lemma_sentence)
                else:
                    found += 1
                    try:
                        words = original_dict[lemma_sentence]
                    except KeyError:
                        try:
                            words = original_dict[lemma_sentence_2]
                        except KeyError:
                            words = original_dict[lemma_sentence_3]
                    for item, word in zip(sentence_buffer, words):
                        item[1] = word
                        fix_f.write("\t".join(item)+"\n")
                    fix_f.write("\n")
                sentence_buffer = []
        print(total)
        print(found)


def add_childes_pos(childes_dir, out_file, parse_dict, split=False):
    all_childes_pos = set()
    seen = set()
    seen_sentences = set()
    print("Reading in CHILDES corpus")
    childes_files = [f for f in listdir(childes_dir) if isfile(join(childes_dir, f))]
    print("\n\tFinished.")
    out_suffix = ".all" if not split else ".dummy"
    print("\n\n")
    out = open(out_file.format(out_suffix), "w") #if split else None
    coverage_per_session = {}
    for file_num, ch_file in enumerate(childes_files, 1):
        if split:
            out = open(out_file.format(file_num), "w")
        print("Processing session {}".format(file_num))
        data = CHILDESCorpusReader(childes_dir, ch_file)
        adults = set(flatten([file_inf.keys() for file_inf in data.participants()]))
        adults.remove('CHI')
        xml_sents = data.extract_xmls_speakers(data.fileids()[0], speaker=adults)
        tagged_sents = data.tagged_sents(data.fileids()[0], speaker=adults, stem=True, relation=True)
        sents = data.sents(data.fileids()[0], speaker=adults)
        total_sentences = len(sents)
        rejected = 0
        annotated = 0
        not_annotated = []
        for i,(POSwords, stems_and_words, xml_sent) in enumerate(zip(tagged_sents,sents, xml_sents)):
            POSwords = [(x[0], x[1], '') if len(x)== 2 else x for x in POSwords]
            POSwords = [(w, pos.replace(':', ';'), rel) for w, pos, rel in POSwords]
            stems = [x[1] for x in stems_and_words]
            words = [x[0] for x in stems_and_words]
            morpheme_list = []
            split_word_list = []
            word_POS_list = []
            conll = []
            for n, ((lem, pos, rel), s, w) in enumerate(zip(POSwords, stems, words)):
                if '~' in lem:
                    orgn_word, orgn_suffix, word1, word2, pos1, pos2 = process_complex_word(lem, pos, w)
                    morpheme_list.extend([word1, word2])
                    word_POS_list.extend([(word1, pos1), (word2, pos2)])
                    split_word_list.extend([orgn_word, orgn_suffix])
                else:
                    morpheme_list.append(s)
                    word_POS_list.append((lem, pos))
                    split_word_list.append(w)
                head = rel.split('|')[1] if len(rel.split('|'))>1 else ''
                rel_string = rel.split('|')[2] if len(rel.split('|'))>1 else ''
                conll.append('\t'.join([str(n+1), w, lem, '_', pos.replace(';', ':'), '_', head, rel_string, '_', '_']))

            sent_v1 = ' '.join(morpheme_list[:-1])
            sent_v2 = ' '.join([''.join(x.split('+')) if '+' in x else x for x in morpheme_list[:-1]])
            sentPOS = [pos+"|"+w for w, pos in word_POS_list[:-1]]

            use_example = check_example_validity(morpheme_list[:-1], sent_v1, seen)
            if use_example:
                seen.add(sent_v1)
                sentence_buffer = get_parse(parse_dict, sent_v1, sent_v2)
                for _, pos in word_POS_list:
                    all_childes_pos.add(pos)
                if sentence_buffer:
                    annotated += 1
                    for i, (wPOS, w_o) in enumerate(zip(sentPOS, split_word_list)):
                        word_index = sentence_buffer[i][0]
                        sentence_buffer[i][1] = wPOS + "_" + str(word_index)
                        sentence_buffer[i][2] = w_o
                    for s_line in sentence_buffer:
                        out.write('\t'.join(s_line)+'\n')
                    out.write('\n')
                    seen_sentences.add(" ".join([x[1] for x in sentence_buffer]))
                else:
                    not_annotated.append(stems_and_words)
                    # not_annotated.append('\n'.join(conll))
                    # not_annotated.append(xml_sent)
            else:
                rejected += 1
        total_desirable_sentences = total_sentences - rejected
        coverage_per_session[file_num] = (float(annotated)/total_desirable_sentences, not_annotated)
    print("Total number of sentences after CHILDES POS mapping: {}".format(str(len(seen_sentences))))
    print("Total number of UD annotated sentences: {}".format(str(len(parse_dict))))
    return coverage_per_session


def process_complex_word(lem, pos, w, fix_mode=False):
    orgn = w.split("'")
    if len(orgn) > 1:
        orgn_word = orgn[0]
        orgn_suffix = "'" + orgn[1]
    else:
        orgn_word = w
        orgn_suffix = ""
    if any([x in lem for x in ['+not~not', '+not-3S~not', '+not-COND~not', '+not-PAST~not',
                               '+not-PRES~not', '+be~be', '+s~s', '+will~will', '+us~us',
                               '+s-DIM~s', '+s-dv~s', '+genmod~genmod', '+be-DIM~be',
                               '+have~have']]):
        word1 = lem.split('~')[0].split('+')
        if len(word1) > 2:
            word1 = '+'.join(word1[:-1])
        else:
            # fix mode is for fixing Adam annotation batches 9 and 10
            # which didn't have correct words and lemmas
            # Here we're dealing with e.g. wouldn't will+not-COND~not in original file
            # which has to match will&COND ~not in annotated file
            if fix_mode:
                if word1[1] in ["not-PRES", "not-PAST", "not-COND"]:
                    word1 = "".join([word1[0], word1[1][3:]])
                else:
                    word1 = word1[0]
            else:
                word1 = word1[0]
    else:
        word1 = lem.split('~')[0]
    word2 = '~'+lem.split('~')[1]
    pos1 = pos.split('~')[0]
    pos2 = pos.split('~')[1]
    return orgn_word, orgn_suffix, word1, word2, pos1, pos2


def check_example_validity(sent_list, sent, seen):
    valid = True
    if any([x in sent_list for x in ['+...', 'xxx', 'yyy', 'www']]):
        valid = False
    num_words = len(sent_list)
    if num_words <= 1 \
            or (num_words == 2 and 'what' in sent_list) \
            or (num_words == 3 and any([x in sent_list for x in [' .', ' ?', ' !']]) and 'what' in sent_list):
    # allow 1 word utterances
    # if (num_words == 2 and 'what' in sent_list) \
    #         or (num_words == 3 and any([x in sent_list for x in [' .', ' ?', ' !']]) and 'what' in sent_list):
        valid = False
    return valid


def get_parse(parse_dict, v1, v2):
    sentence_buffer = None
    try:
        sentence_buffer = parse_dict[v1]
    except KeyError:
        try:
            sentence_buffer = parse_dict[v2]
        except KeyError:
            pass
    return sentence_buffer


def change_s_be(word):
    if word == '~s':
        return '~be'
    elif word == '~be':
        return '~s'
    else:
        return word


# def repair_lemmas(lemmas):
#     return [l.replace("&", "_") for l in lemmas]



parser = optparse.OptionParser()
parser.add_option('-c', '--childes', dest="childes",
                  default='/usr/local/share/nltk_data/corpora/childes/data-xml/Eng-NA-MOR/Brown/Adam',
                  help="directory with CHILDES xml files")
parser.add_option('-i', '--input', dest="in_file",
                  default="../conll/original_adam/Adam.{}x.Gibbon.conll10",
                  # default="../conll/original_sivan/sivan_all{}.most.recent.trees_out.conll10",
                  help="raw annotation filee in CoNLL format")
parser.add_option('-n', '--batchnum', dest="batch_numbers",
                  default="0 1 2 3 4 5 6 7 8 9 10",
                  # default="0 1 2 17 18 19 20 21 22 23 24",
                  help="numbers of batches from which to draw parsed data")
parser.add_option("-o", "--output", dest="out_file", default="../conll/split_adam/adam{}.conll.txt",
                  help="destination file for preprocessed UD annotation")
parser.add_option("-s", "--split", dest="split", default=False,
                  help="if True, annotations are saved to files matching CHILDES files;"
                       "if False, one annotation file is used")
parser.add_option("-v", "--invalid", dest="invalid_file",
                  default="../conll/invalid_parses/Adam.conll.invalid.txt",
                  # default="../conll/invalid_parses/Sivan.conll.invalid.txt",
                  help="storage file for invalid parses")
parser.add_option("-e", "--english", dest="english", default=True,
                  help="if True, processing English parses; if False, processing Hebrew parses")
(opts, _) = parser.parse_args()



############################################
# OPTIONS

# # 1. preprocess conll files for UDepLambda
# parse_dict = read_in_parses(opts.in_file, opts.batch_numbers.split(), opts.invalid_file, opts.english)
# _ = add_childes_pos(opts.childes, opts.out_file, parse_dict, split=False)


# # 2a. get dependency statistics for the corpus
# #    - for the whole dependency corpus
# parse_dict = read_in_parses(opts.in_file, opts.batch_numbers.split(), opts.invalid_file, opts.english)
# print("\n\n")
# print("Stats for full UD corpus:")
# get_dep_stats(parse_dict)
# #    - for the sentences for which LF conversion succeeds
# print("\n\n")
# print("Stats after LF conversion:")
# # working_sentences = []
# # for line in open("./logs/working_sentences.txt"):
# #     working_sentences.append(line.strip())
# lf_parse_dict = read_parse_dict_from_json("../logs/working.txt")
# print("\n\n")
# get_dep_stats(lf_parse_dict)
# #    comparison
# print("\n\n")
# print("Proportion converted:")
# dep_stats_difference(parse_dict, lf_parse_dict)

# # 2b. get dependency statistics per session
# #    - for whole session
# session = "1"
# parse_dict = read_in_parses("../conll/split_adam/adam{}.conll.txt", [session], opts.invalid_file, opts.english)
# print("\n\n")
# print("Stats for session {}:".format(session))
# get_dep_stats(parse_dict)
# #    - per session for the sentences for which LF conversion succeeds
# lf_parse_dict = read_parse_dict_from_json("../logs/{}_working.txt".format(session))
# print("\n\n")
# print("Stats for session {} after LF conversion:".format(session))
# print("\n\n")
# get_dep_stats(lf_parse_dict)
# #    comparison
# print("\n\n")
# print("Proportion converted:")
# dep_stats_difference(parse_dict, lf_parse_dict)


# # 2c. generate dependency stats over sessions for histogram drawing
# # TODO, there's a problem with get_dep_stats_with_repetition bc read_in_parses creates
# # parse dict with 3 versions of each sentence as keys
# dep_histograms = defaultdict(lambda: [0]*41)
# # dep_histograms = defaultdict(list)
# for s in range(1, 42):
#     session = str(s)
#     parse_dict, sent_counts = read_in_parses("../conll/split_adam/adam{}.conll.txt", [session], opts.invalid_file,
#                                              opts.english, with_counts=True)
#     print("\n\n")
#     print("Stats for session {}:".format(session))
#     dep_freq = get_dep_stats_with_repetition(parse_dict, sent_counts, write_out=False)
#     total_sent_no = sum(sent_counts.values())
#     for dep in dep_freq:
#         dep_histograms[dep][s-1] = dep_freq[dep]
#         # dep_histograms[dep].extend([s]*dep_freq[dep])
#
# for dep, counts in dep_histograms.items():
#     # if dep =="nsubjpass":
#     #     print(counts)
#     print("\n"+dep)
#     print(counts)
#     # for s in range(1,42):
#     #     print(str(s)+": "+''.join(["+"]*(int(round(counts[s-1]*100)))))

# # 3. determine coverage of CHILDES sessions with the annotated UD corpus
# parse_dict = read_in_parses(opts.in_file, opts.batch_numbers.split(), opts.invalid_file, opts.english)
# coverage = add_childes_pos(opts.childes, opts.out_file, parse_dict, split=opts.split)
# missing = set([])
# for session, (cov, unannotated) in coverage.items():
#      if session < 42:
#          print(session, "{0:.2f}".format(cov))
#          missing = missing.union(set([' '.join([x[0] for x in u]) for u in unannotated]))
#      # if session == 2:
#      #     missing = set([' '.join([x[0] for x in u]) for u in unannotated])
#      # missing = missing.union(set(unannotated))
#
# print(len(missing))
# with open("Adam_unannotated_sentences_final.txt", "w") as missing_file:
#     for m in missing:
#         # xml.etree.ElementTree.dump(m)
#         missing_file.write(m)
#         missing_file.write('\n')


# # 4. repair Adam batches 9 and 10
# #    in which there are various contractions instead of recontructed lemmas
# #    and no merging of expressions such as "have to" or "thank you"
# repair_adam_data("./working_files/Adam_unannotated_sentences.txt", "./conll/original_adam/Adam.9x.Gibbon.wrong_words.conll10",
#                  "./conll/original_adam/Adam.9x.Gibbon.conll10")
# repair_adam_data("./working_files/Adam_unannotated_sentences.txt", "./conll/original_adam/Adam.10x.Gibbon.wrong_words.conll10",
#                  "./conll/original_adam/Adam.10x.Gibbon.conll10")

# # 5 .writing out Hebrew parses with word and lemma switching places
# #    to bring Hebrew data to the same form as English data
# def write_out_parses(parse_dict, out_file):
#     with open(out_file, "w") as out_f:
#         for sentence, parse in parse_dict.items():
#             for line in parse:
#                 out_f.write("\t".join(line)+"\n")
#             out_f.write("\n")
#
#
# parse_dict = read_in_parses("../conll/original_sivan/sivan_all{}.most.recent.trees_out.conll10",
#                             ["0","1","2","17","18","19","20","21","22","23","24"],
#                             "../conll/invalid_parses/Sivan.conll.invalid.txt", False)
# write_out_parses(parse_dict, "../../UDepLambda/sivan.all.conll.txt")
# write_out_parses(parse_dict, "../conll/original_sivan/sivan.all.conll.txt")


# ????
# _ = add_childes_pos(opts.childes, opts.out_file, parse_dict, split=opts.split)
# parse_dict_with_pos = read_conll_file(opts.out_file, opts.english)


