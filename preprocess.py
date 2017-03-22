import optparse
from childes_reader import CHILDESCorpusReader
from os import listdir
from os.path import isfile, join


flatten = lambda l: [item for sublist in l for item in sublist]


def add_childes_pos(childes_dir, out_file, out_dir, split=False):
    seen = set()
    childes_files = [f for f in listdir(childes_dir) if isfile(join(childes_dir, f))]
    with open(out_file, "w") as one_out_file:
        for ch_file in childes_files:

            data = CHILDESCorpusReader(childes_dir, ch_file)
            adults = set(flatten([file_inf.keys() for file_inf in data.participants()]))
            adults.remove('CHI')
            tagged_sents = data.tagged_sents(data.fileids()[0], speaker=adults, stem=True)
            sents = data.sents(data.fileids()[0], speaker=adults)

            for i,(POSwords, stems_and_words) in enumerate(zip(tagged_sents,sents)):
                POSwords = [(w, pos.replace(':', ';')) for w, pos in POSwords]
                stems = [x[1] for x in stems_and_words]
                words = [x[0] for x in stems_and_words]
                morpheme_list = []
                split_word_list = []
                word_POS_list = []
                for ((lem, pos), s, w) in zip(POSwords, stems, words):
                    if '~' in lem:
                        orgn_word, orgn_suffix, word1, word2, pos1, pos2 = process_complex_word(lem, pos, s, w)
                        morpheme_list.extend([word1, word2])
                        word_POS_list.extend([(word1, pos1), (word2, pos2)])
                        split_word_list.extend([orgn_word, orgn_suffix])
                    else:
                        morpheme_list.append(s)
                        word_POS_list.append((lem, pos))
                        split_word_list.append(w)

                sent_v1 = ' '.join(morpheme_list)
                sent_v2 = ' '.join([''.join(x.split('+')) if '+' in x else x for x in morpheme_list])
                sentPOS = [pos+"|"+w for w, pos in word_POS_list]

                use_example = check_example_validity(morpheme_list, sent_v1, seen)
                if use_example:
                    seen.add(sent_v1)
                    sentence_buffer = get_parse(sent_v1, sent_v2)
                    if sentence_buffer:
                        if not split:
                            out = one_out_file
                        else:
                            out = open(join(out_dir, ''.join([ch_file.rstrip('xml'), 'txt'])), "a")
                        for i, (wPOS, w_o) in enumerate(zip(sentPOS, split_word_list)):
                            sentence_buffer[i][1] = wPOS
                            sentence_buffer[i][2] = w_o
                        for s_line in sentence_buffer:
                            out.write('\t'.join(s_line)+'\n')
                        out.write('\n')


def process_complex_word(lem, pos, s, w):
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
    if num_words == 1\
            or (num_words == 2 and any([x in sent_list for x in [' .', ' ?', ' !', 'what']]))\
            or (num_words == 3 and any([x in sent_list for x in [' .', ' ?', ' !']]) and 'what' in sent_list):
        valid = False
    if sent in seen:
        valid = False
    return valid


def get_parse(v1, v2):
    sentence_buffer = None
    try:
        sentence_buffer = parse_dict[v1]
    except KeyError:
        try:
            sentence_buffer = parse_dict[v2]
        except KeyError:
            pass
    return sentence_buffer


def read_in_parses(out_file, in_file, invalid_parse_file, addPOS=True):
    sent_count = 0
    invalid_parse_count = 0
    valid_parse = True
    annotation_dict = {}
    sentence_buffer = []
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
            if edge_label == 'incroot':
                edge_label = 'root'
            elif edge_label == 'subj':
                edge_label = 'nsubj'
            sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                    parent_index, edge_label, enhanced_dep, misc])

            if edge_label in ['obj','mod','app','link','com','jct','cmod','coord','njct','pred','pobj','inf','pq']:
                valid_parse = False
        else:
            if valid_parse:
                sent_count += 1
                words_only = [l[1] for l in sentence_buffer if l[3] != 'PUNCT']
                sentence = ' '.join(words_only)
                other_sentence = ' '.join([change_s_be(x) for x in words_only])
                another_sentence = ' '.join([x.split('(')[0] if '(' in x and ')' in x else x for x in words_only])
                sents = {sentence, another_sentence, other_sentence}
                for s in sents:
                    annotation_dict[s] = sentence_buffer
            else:
                invalid_parse_count += 1
            valid_parse = True
            sentence_buffer = []
    print("Number of sentences: {0:d}".format(sent_count))
    print("Invalid parses: {0:d}".format(invalid_parse_count))
    return annotation_dict


def change_s_be(word):
    if word == '~s':
        return '~be'
    elif word == '~be':
        return '~s'
    else:
        return word

parser = optparse.OptionParser()
parser.add_option('-c', '--childes', dest="childes",
                  default='/usr/local/share/nltk_data/corpora/childes/data-xml/Eng-NA-MOR/Brown/Adam',
                  help="directory with CHILDES xml files")
parser.add_option('-i', '--input', dest="in_file",
                  default="./Adam.0x.adults.uniq.sgibbon.valid..complete.conll10",
                  help="raw annotation filee in CoNLL format")
parser.add_option("-o", "--output", dest="out_file", default="./Adam.conll.test.txt",
                  help="destination file for preprocessed UD annotation")
parser.add_option("-d", "--output_dir", dest="out_dir", default="./conll",
                  help="destination directory for preprocessed UD annotations split to match CHILDES files")
parser.add_option("-s", "--split", dest="split", default=False,
                  help="if True, annotations are saved to files matching CHILDES files;"
                       "if False, one annotation file is used")
parser.add_option("-v", "--invalid", dest="invalid_file", default="./Adam.conll.invalid.txt",
                  help="storage file for invalid parses")
(opts, _) = parser.parse_args()

parse_dict = read_in_parses(opts.out_file, opts.in_file, opts.invalid_file)
add_childes_pos(opts.childes, opts.out_file, opts.out_dir, split=opts.split)
