import optparse
from nltk.corpus.reader.childes import CHILDESCorpusReader

parser = optparse.OptionParser()
parser.add_option('-c', '--childes', dest="childes",
                  default='/usr/local/share/nltk_data/corpora/childes/data-xml/Eng-NA-MOR/Brown/Adam',
                  help="directory with CHILDES xml files")
parser.add_option('-i', '--input', dest="in_file",
                  default="./Adam.0x.adults.uniq.sgibbon.valid..complete.conll10",
                  help="raw annotation filee in CoNLL format")
parser.add_option("-o", "--output", dest="out_file", default="./Adam.conll.txt",
                  help="destination file for preprocessed UD annotation")
parser.add_option("-v", "--invalid", dest="invalid_file", default="./Adam.conll.invalid.txt",
                  help="storage file for invalid parses")
(opts, _) = parser.parse_args()


en = CHILDESCorpusReader(opts.childes, '.*.xml')
seen = set()
flatten = lambda l: [item for sublist in l for item in sublist]


def get_childes_sent_dict():
    childes_sent_dict = {}
    adults = set(flatten([file_inf.keys() for file_inf in en.participants()]))
    adults.remove('CHI')
    for fileid in en.fileids():
        tagged_sents = en.tagged_sents(fileid, speaker=adults, stem=True)
        sents = en.sents(fileid, speaker=adults)
        # for i,(POSwords, lemmas) in enumerate(zip(en.tagged_sents(fileid, speaker=adults, stem=True),
        #                                                  en.sents(fileid, speaker=adults))):
        for i,(POSwords, stems_and_words) in enumerate(zip(tagged_sents,sents)):
            stems = [x[1] for x in stems_and_words]
            words = [x[0] for x in stems_and_words]
            analysed_sent_list = []
            split_sent_list = []
            POSwords = [(w, pos.replace(':', ';')) for w, pos in POSwords]
            true_sentPOS_list = []
            if "get" in stems and 'what' in stems:
                pass
            for ((lem, pos), s, w) in zip(POSwords, stems, words):
                if '~' in lem:
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
                        word = lem.split('~')[0].split('+')
                        if len(word) > 2:
                            word = '+'.join(word[:-1])
                        else:
                            word = word[0]
                        analysed_sent_list.extend([word, '~'+lem.split('~')[1]])
                        true_sentPOS_list.extend([(word, pos.split('~')[0]),
                                                  ('~'+lem.split('~')[1], pos.split('~')[1])])
                    else:
                        analysed_sent_list.extend([lem.split('~')[0], '~'+lem.split('~')[1]])
                        true_sentPOS_list.extend([(lem.split('~')[0], pos.split('~')[0]),
                                                  ('~'+lem.split('~')[1], pos.split('~')[1])])
                    split_sent_list.extend([orgn_word, orgn_suffix])
                else:
                    analysed_sent_list.append(s)
                    true_sentPOS_list.append((lem, pos))
                    split_sent_list.append(w)
            # original_sent = ' '.join(split_sent_list)
            analysed_sent = ' '.join(analysed_sent_list)
            other_sent = ' '.join([''.join(x.split('+')) if '+' in x else x for x in analysed_sent_list])
            sentPOS = [pos+"|"+w for w, pos in true_sentPOS_list]

            if any([x in analysed_sent_list for x in ['+...', 'xxx', 'yyy', 'www']]):
                continue
            num_words = len(analysed_sent_list)
            if num_words == 1\
                    or (num_words == 2 and any([x in analysed_sent_list for x in [' .', ' ?', ' !', 'what']]))\
                    or (num_words == 3 and any([x in analysed_sent_list for x in [' .', ' ?', ' !']]) and 'what' in analysed_sent_list):
                continue
            if analysed_sent in seen:
                continue
            seen.add(analysed_sent)
            childes_sent_dict[analysed_sent] = (sentPOS, split_sent_list)
            if other_sent != analysed_sent:
                childes_sent_dict[other_sent] = (sentPOS, split_sent_list)
    return childes_sent_dict


def preprocess_annotation(out_file, in_file, invalid_parse_file, addPOS=True):
    sent_count = 0
    invalid_parse_count = 0
    valid_parse = True
    not_in_xml = 0
    with open(out_file, "w") as out_file, open(invalid_parse_file, "w") as iv_file, open("./not_in_xml.txt", "w") as wtf:
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
                # line = "\t".join([word_index, word, lemma, upos, xpos, features,
                #                   parent_index, edge_label, enhanced_dep, misc])
                # sentence_buffer.append(line+'\n')
                sentence_buffer.append([word_index, word, lemma, upos, xpos, features,
                                        parent_index, edge_label, enhanced_dep, misc])

                if edge_label in ['obj','mod','app','link','com','jct','cmod','coord','njct','pred','pobj','inf']:
                    valid_parse = False
            # elif len(split_line) > 1:
            #     pass
            else:
                out = out_file if valid_parse else iv_file
                if valid_parse:
                    sent_count += 1
                else:
                    invalid_parse_count += 1
                if addPOS:
                    words_only = [l[1] for l in sentence_buffer if l[3] != 'PUNCT']
                    sentence = ' '.join(words_only)
                    other_sentence = ' '.join([change_s_be(x) for x in words_only])
                    another_sentence = ' '.join([x.split('(')[0] if '(' in x and ')' in x else x for x in words_only])
                    try:
                        try:
                            wordsPOS, words_original = childes_sent_dict[sentence]
                        except KeyError:
                            try:
                                wordsPOS, words_original = childes_sent_dict[other_sentence]
                            except KeyError:
                                wordsPOS, words_original = childes_sent_dict[another_sentence]
                        for i,(wPOS, w_o) in enumerate(zip(wordsPOS, words_original)):
                            sentence_buffer[i][1] = wPOS
                            sentence_buffer[i][2] = w_o
                    except KeyError:
                        not_in_xml += 1
                        wtf.write(sentence+'\n')
                for s_line in sentence_buffer:
                    out.write('\t'.join(s_line)+'\n')
                out.write(line)
                valid_parse = True
                sentence_buffer = []
    print(sent_count)
    print(invalid_parse_count)
    print(not_in_xml)


def change_s_be(word):
    if word == '~s':
        return '~be'
    elif word == '~be':
        return '~s'
    else:
        return word

childes_sent_dict = get_childes_sent_dict()
with open("./childes_sent_dict.txt", "w") as dict_file:
    for sent, (pos_list, original_list) in childes_sent_dict.items():
        dict_file.write(sent + '\t' + '|||\t' + ' '.join(pos_list)+'\t' + '|||\t' + ' '.join(original_list)+'\n')

preprocess_annotation(opts.out_file, opts.in_file, opts.invalid_file)

