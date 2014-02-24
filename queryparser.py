"""
queryparser.py
author: Sophia van Valkenburg

This script retrieves a query string, user, and password.
If the user and password are correct, parse the query and
return a JSON string of the parsed values.

"""
import json
from flask import Flask, request
from nltk import RegexpParser, word_tokenize, pos_tag
from nltk.tree import Tree,ParentedTree
from nltk.corpus import wordnet as wn


UNK = "UNK"
SKIP = "SKIP"

app = Flask(__name__)

@app.route('/parse', methods=['GET','POST'])
def receive_parse_request():
    query_text = request.form.get('text')
    network_json = request.form.get('networks')
    auth = request.args.get('auth')
    if not query_text or not auth:
            response = {
                    "error": "must specify 'text' and 'auth' fields"
                    }
    else:
        if authenticate(auth):
            response = parse(query_text, network_json)
        else:
            response = {"error": "auth code is incorrect" }
    return json.dumps(response)

def authenticate(auth):
    return True

def parse(query_text, networks_json):
    query_text = preprocess(query_text)
    tokens = word_tokenize(query_text)
    double_tokens = [ (w, w) for w in tokens ]
    tagged = pos_tag(tokens)
    domain_tagged = tag_domains(tagged, networks_json)
    tg = tag_grammar()
    wg = word_grammar()
    t_cp = RegexpParser(compile_grammar(tg))
    w_cp = RegexpParser(compile_grammar(wg))
    tagged_result = t_cp.parse(domain_tagged)
    word_result = w_cp.parse(double_tokens)
    slots = assign_slots(tokens, tagged_result, word_result)
    print 'tagged-result = ',tagged_result
    print 'word-result = ',word_result
    return slots

def preprocess(string):
    """ 
    -strip, make lowercase
    -space out punctuation. necessary to treat punctuation as separate tokens.
    so 2/13/2014 becomes 2 / 13 / 2014
    -also replace <, > with gt, lt because these symbols are reserved.
    """
    string = string.strip().lower()
    punctuation = "~`!@#$%^&*()_+-={}|[]\\:\";'<>?,./"
    new_string = ""
    for ch in string:
        if ch in punctuation:
            if ch == '>':
                ch = 'gt'
            elif ch == '<':
                ch = 'lt'
            ch = " " + ch + " "
        new_string += ch
    return new_string

def assign_slots(tokens, tag_tree, word_tree):
    tokens_with_slot_tags = []
    word_tree = ParentedTree.convert(word_tree)
    tag_tree = ParentedTree.convert(tag_tree)
    word_tree_with_cats = tag_words_with_categories(word_tree)
    tag_tree_with_cats = tag_words_with_categories(tag_tree)
    for i, word in enumerate(tokens):
        tag = merge_tags(i, word, tag_tree_with_cats, word_tree_with_cats) 
        tokens_with_slot_tags.append((word, tag))
    found_query_focus = False
    for i, item in enumerate(tokens_with_slot_tags):
        word, tag = item
        if tag in ['USER','MEDIA','NETWORK'] and not found_query_focus:
            tokens_with_slot_tags[i] = (word, 'SEARCH')
            found_query_focus = True
        elif tag == UNK:
            tokens_with_slot_tags[i] = (word, 'KEYWORD')
    slots = {}
    for word, tag in tokens_with_slot_tags:
        if tag == 'SKIP':
            continue
        elif tag == 'KEYWORD':
            if 'KEYWORDS' not in slots:
                slots['KEYWORDS'] = []
            slots['KEYWORDS'].append(word)
        else:
            if tag not in slots:
                slots[tag] = word
            else:
                previous_words = slots[tag]
                slots[tag] = ' '.join([previous_words, word])
    return slots

def merge_tags(i, word, tt, wt):
    tt_ind = tt.leaf_treeposition(i)
    wt_ind = wt.leaf_treeposition(i)
    tt_pos = tt[tt_ind][1]
    tt_category = tt[tt_ind][2]
    wt_category = wt[wt_ind][2]
    if wt_category == 'DATE':
        return 'DATE_1'
    elif wt_category == 'DATE_FROM':
        if tt_pos != 'IN':
            return 'DATE_1'
        else:
            return SKIP
    elif wt_category == 'DATE_TO':
        if tt_pos != 'IN' and tt_pos != 'TO':
            return 'DATE_2'
        else:
            return SKIP
    elif wt_category == 'LENGTH':
        if tt_pos == 'CD' or tt_pos == 'LS':
            return 'LENGTH_NUM'
        elif tt_pos == 'NN' or tt_pos == 'NNS' or tt_pos == 'JJ':
            return 'LENGTH_UNIT'
        else:
            return SKIP
    elif tt_pos == 'MEDIA':
        return 'MEDIA'
    elif tt_pos == 'NETWORK':
        return 'NETWORK'
    elif tt_pos == 'NETWORK_NAME':
        return 'NETWORK_NAME'
    elif tt_pos == 'USER':
        return 'USER'
    elif tt_category == "PosP":
        if tt_pos != 'POS' and len(word) > 1:
            return 'CREATOR'
        else:
            return SKIP
    elif tt_category == 'PP':
        if tt_pos != 'IN' and tt_pos != 'TO':
            # get the value of preposition
            j = i
            tt_pos_j = tt_pos
            while j > 0 and tt_pos_j != 'IN' and tt_pos_j != 'T0':
                j = j-1
                tt_ind_j = tt.leaf_treeposition(j)
                tt_pos_j = tt[tt_ind_j][1]
            wt_ind_j = wt.leaf_treeposition(j)
            wt_category_j = wt[wt_ind_j][2]
            if wt_category_j == 'BY' or wt_category_j == 'FROM':
                return 'CREATOR'
            else:
                return UNK
        else:
            return SKIP
    else:
        return UNK

def tag_words_with_categories(tree):
    """
    tag each word in the tree with the category it is listed under
    for example, (LENGTH (NUM 1/1) minute/minute ) should have leaves
    1/1/LENGTH minute/minute/LENGTH
    """
    for subtree in tree:
        if isinstance(subtree, Tree):
            for pos in subtree.treepositions('leaves'):
                subtree[pos] += (subtree.node,)
    return tree

def compile_grammar(glist):
    grammar = ""
    gdict = {}
    for entry in glist:
        tag, rules = entry[0], entry[1:]
        rule_str = '\n'.join(rules)
        if tag in gdict:
            if gdict[tag] != rule_str:
                raise ValueError("%s has two rules: '%s' and '%s'"
                        %(tag, gdict[tag], rule_str) )
            else:
                continue
        else:
            gdict[tag] = rule_str
            grammar += "%s: %s \n"%(tag, rule_str)
    return grammar

def tag_grammar():
    glist = [
        ("MedP",    "{<DT>?<JJ>*<MEDIA>+<NN.*|NetP|NETWORK.*>*}"),
        ("NetP",    "{<DT>?<JJ>*<NETWORK.*>+<NN.*|MedP|MEDIA>*}"),
        ("PP",      "{<.*>+}", "<.*>}{<RB>?<IN|TO>", "}<WDT><.*>+{"),
        ("PosP",    "{<.*><POS><NNS>?}"),
        ("QUOTE",   "{<``><.*>*<''>}"),
        (UNK, "{<.*>}","}<MedP|NetP|PP|PosP|QUOTE>{")
    ]
    return glist

def word_grammar():
    NUM = num_grammar("NUM")
    DATE = date_grammar("DATE")
    terminals = [
        ("CMP", "{<over|under|at least|at most|atleast|atmost|"
                "more than|greater than|less than|fewer than|gt|lt>}"),
        ("UNIT", "{<sec|min|hr|second|minute|hour|day|seconds|minutes|hours|"
                "days>}"),
        ("FROM", "{<after|starting|since|beginning|from>}"),
        ("TO", "{<before|ending|to>}"),
        ("ON", "{<on>}"),
        ("IN","{<in>}"),
        ("OF","{<of>}"),
        ("ABOUT","{<about>}"),
        ("BY","{<by>}"),
        ("WITH","{<with>}"),
    ]
    rules = (
        NUM + [ ("LENGTH", "{<CMP>?<NUM|a><->?<UNIT><long>?}") ] +
        DATE + [ ("DATE_FROM","{<FROM><DATE>}"), ("DATE_TO", "{<TO><DATE>}")] +
        [ (UNK,   "{<.*>}",
            "}<LENGTH|DATE.*|CMP|UNIT|FROM|TO|ON|IN|OF|ABOUT|BY|WITH>{") ]
        )
    return terminals + rules

def num_grammar(tag="NUM"):
    DIGIT =     "<one|two|three|four|five|six|seven|eight|nine>"
    TEEN =      ("<ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|sevente"
                "en|eighteen|nineteen>")
    TEN =       "<twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety>"
    LARGE =     "(<a>?<hundred|thousand|million|billion|trillion>)"
    NUMWORDS =  "(("+DIGIT+"|"+TEEN+"|"+TEN+")?"+LARGE+"?)"
    NUMCHARS =   "<\.>?<\d+>(<\.|/><\d+>)?"
    FRACTION =  "(<and><a><half|quarter>|<half>)"
    NUM =       "{"+ NUMCHARS+ "|" + NUMWORDS + FRACTION + "?}"
    return [(tag, NUM)]

def date_grammar(tag="DATE"):
    NUM = num_grammar("NUM")
    DAY_OF_WEEK = ("<monday|mon|tuesday|tues|wednesday|wed|thursday|thur|"
            "friday|fri|saturday|sat|sunday|sun>")
    MONTH =("<january|jan|february|feb|march|mar|april|apr|june|jun|july|jul|"
            "august|aug|september|sep|sept|october|oct|november|nov|december|"
            "dec>")
    YEAR = "<NUM>"
    ORD = "<first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth>"
    ORDCHARS = "<\d\d?(st|nd|rd|th)>"
    DAY = "(<NUM>" + "|" + ORD + "|" + ORDCHARS +")"
    DECADE = "<\d\d(\d\d)?s>"
    SEP = "<\.|/|-,>?"
    DATE_SEQUENCE = ( DAY_OF_WEEK + "?" + SEP + 
            "( <NUM>" + SEP + DAY + "(" + SEP + YEAR + ")? |"
            + MONTH + SEP + DAY + "(" + SEP + YEAR + ")? |"
            + DAY + SEP + MONTH + "(" + SEP + YEAR + ")? |"
            + DAY + "<of>" + MONTH + ")" + SEP + DAY_OF_WEEK + "?" )
    # specific date
    SDATE = ( "{" + DATE_SEQUENCE + "|" + DAY_OF_WEEK + "|" + MONTH + "|" 
            + DECADE + "|" + YEAR + "}" )

    MOD = "<the last|last|this|this past|the past>"
    AGO = "<ago|before|previous|prior|previously|since>"
    UNIT = "<day|week|month|year|decade|days|weeks|months|years|decades>"
    # relative date
    RDATE = "{ <yesterday>|<today>|<NUM>"+UNIT+AGO+"|"+MOD+"<NUM>?"+UNIT + " }"
    
    return NUM + [("SDATE", SDATE),("RDATE", RDATE),(tag, "{<SDATE|RDATE>}")]


def matches_domain(word, domain_synset, thresh=0.5):
    """
    check whether word is a part of the domain using max synset similarity
    in the future, can use machine learning approach
    word            --  input word
    domain_synset   __  list of synsets representing the domain
    """
    word_synsets = get_synsets([word])
    max_similarity_score = 0
    for synset1 in domain_synset:
        for synset2 in word_synsets:
            this_score = synset1.path_similarity(synset2)
            max_similarity_score = max( max_similarity_score, this_score)
    return max_similarity_score >= thresh

def tag_domains(tagged, networks_json):
    """
    returns a list of (word, tag) tuples where some words are tagged as
    MEDIA or NETWORK. MEDIA words are tagged using just one feature - 
    wordnet path similarity between the synsets of the given word and
    synsets of the words in the MEDIA category. NETWORK words are tagged
    using the same method as MEDIA, but also if the word is part of a 
    given network list.

    In the future, we can add more features to the domain classifier.
    We should also look at the next and previous words to match network
    names instead of just checking one word (obviously, the current method
    will not work for networks that are more than one word long)
    """
    media_synset_list = media_synsets()
    network_synset_list = network_synsets()
    user_synset_list = user_synsets()
    network_list = get_network_names(networks_json)
    domain_tagged = []
    for word, tag in tagged:
        if tag.startswith('N'):
            if matches_domain(word, media_synset_list):
                tag = 'MEDIA'
            elif matches_domain(word, network_synset_list):
                tag = 'NETWORK'
            elif word in network_list:
                tag = 'NETWORK_NAME'
            elif matches_domain(word, user_synset_list):
                tag = 'USER'
        domain_tagged.append((word, tag))
    return domain_tagged

def media_synsets():
    """
    returns wordnet synsets for all words in media list
    """
    words = ("media|video|photo|audio|clip|movie|news|content|advertisement|"
        "podcast|footage|story|coverage|tv|program|upload|file|radio|segment")
    wordlist = words.split("|")
    return get_synsets(wordlist)

def network_synsets():
    """
    returns wordnet synsets for all words in networks list. 
    """
    words = ("network|channel|affliate|broadcaster|distributor|provider|"
            "telecast|communications")
    wordlist = words.split("|")
    return get_synsets(wordlist)

def user_synsets():
    """
    returns wordnet synsets for all words in users list. 
    """
    words = ("user|member|username")
    wordlist = words.split("|")
    return get_synsets(wordlist)

def get_synsets(wordlist):
    """
    returns wordnet synsets for all words in the hardcoded list
    in the future, perhaps this list can be generated in a better way.
    """
    synsets = []
    for word in wordlist:
        synsets += wn.synsets(word)
    return synsets

def get_network_names(networks_json=None):
    """
    gets a list of network names from the given json list
    """
    networks = []
    try:
        networks = [ preprocess(s) for s in json.loads(networks_json) ]

    except ValueError:
        print "Unable to parse JSON networks list"
    return networks


if __name__ == "__main__":
    app.debug = True
    app.run()

