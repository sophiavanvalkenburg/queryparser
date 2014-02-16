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
from nltk.corpus import wordnet as wn

app = Flask(__name__)

@app.route('/parse', methods=['GET','POST'])
def receive_parse_request():
    query_text = request.form.get('text')
    auth = request.args.get('auth')
    if not query_text or not auth:
            response = {
                    "error": "must specify 'text' and 'auth' fields"
                    }
    else:
        if authenticate(auth):
            response = parse(query_text)
        else:
            response = {"error": "auth code is incorrect" }
    return json.dumps(response)

def authenticate(auth):
    return True

def parse(query_text):
    query_text = preprocess(query_text)
    tokens = word_tokenize(query_text)
    double_tokens = [ (w, w) for w in tokens ]
    tagged = pos_tag(tokens)
    domain_tagged = tag_domains(tagged)
    tg = tag_grammar()
    wg = word_grammar()
    t_cp = RegexpParser(compile_grammar(tg))
    w_cp = RegexpParser(compile_grammar(wg))
    tagged_result = t_cp.parse(domain_tagged)
    word_result = w_cp.parse(double_tokens)
    print 'tagged =',tagged
    print 'tagged result = ',tagged_result
    print 'word result =',word_result
    print 'domain tagged =',domain_tagged
    return { 'tagged':domain_tagged }

def preprocess(string):
    """ 
    -make lowercase
    -space out punctuation. necessary to treat punctuation as separate tokens.
    -also replace <, > with gt, lt because these symbols are reserved.
    so 2/13/2014 becomes 2 / 13 / 2014
    """
    string = string.lower()
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

def compile_grammar(glist):
    grammar = ""
    gdict = {}
    for tag, rule in glist:
        if tag in gdict:
            if gdict[tag] != rule:
                raise ValueError("%s has two rules: '%s' and '%s'"
                        %(tag, gdict[tag], rule) )
            else:
                continue
        else:
            gdict[tag] = rule
            grammar += "%s: %s \n"%(tag, rule)
    return grammar

def tag_grammar():
    glist = [
        ("MP",   "{<DT>?<JJ>*<MEDIA>+<N.*>*<POS>?}"),
        ("QUOTE", "{<``><.*>*<''>}"),
        ("PP",    "{<RB>?<IN|TO><[^IT].*>+}"),
    ]
    return glist

def word_grammar():
    imported_grammars = (
            num_grammar("NUM") + 
            date_grammar("DATE")
            )
    terminals = [
        ("CMP", "{<over|under|at least|at most|atleast|atmost|"
                "more than|greater than|less than|fewer than|gt|lt>}"),
        ("UNIT", "{<second|minute|hour|day|seconds|minutes|hours|days>}"),
        ("FROM", "{<after|starting|since|beginning|from>}"),
        ("TO", "{<before|ending|to>}"),
        ("ON", "{<on>}"),
        ("IN","{<in>}"),
        ("OF","{<of>}"),
        ("ABOUT","{<about>}"),
        ("BY","{<by>}"),
        ("WITH","{<with>}"),
    ]
    rules = [
        ("LENGTH", "{<CMP>?<NUM|a><->?<UNIT><long>?}"),
        ("DATE_FROM","{<FROM><DATE>}"),
        ("DATE_TO", "{<TO><DATE>}"),
        ]
    return imported_grammars + terminals + rules

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
    MOD = "<last|this|this past|the past>"
    AGO = "<ago|before|previous|prior|previously|since>"
    UNIT = "<day|week|month|year|decade|days|weeks|months|years|decades>"
    DAY_OF_WEEK = "<monday|tuesday|wednesday|thursday|friday|saturday|sunday>"
    YEAR = "<NUM>"
    DECADE = "<\d\d(\d\d)?s>"
    MONTH =("(<january|jan|february|feb|march|mar|april|apr|june|jun|july|jul|"
            "august|aug|september|sep|sept|october|oct|november|nov|december|"
            "dec|NUM>)")
    ORD = "<first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth>"
    ORDCHARS = "<\d\d?(st|nd|rd|th)>"
    DAY = "(<NUM>" + "|" + ORD + "|" + ORDCHARS +")"
    SEP = "<\.|/|->?"
    DATE_SEQ = (MONTH + SEP + DAY + "("+ SEP + YEAR + ")?|" +
                YEAR + SEP + MONTH + SEP + DAY + "|" + 
                DAY + SEP + MONTH + "(" + SEP + YEAR + ")?|")
    SINGLE = "(<yesterday|today>|"+YEAR+"|"+MONTH+"|"+DECADE+")"
    DATE = ("{(" + MOD +"(<NUM>?"+UNIT + AGO + "?" + "|" +
             DAY_OF_WEEK + "|" + MONTH + "))|" +
            "(" + DAY_OF_WEEK + "?" + DATE_SEQ + DAY_OF_WEEK + "?)|"
            "(" + SINGLE + ")}" )
    return NUM + [(tag, DATE)]

def matches_domain(word, domain_synset, thresh=0.5):
    """
    check whether word is a part of the domain using max synset similarity
    in the future, can use machine learning approach
    word            --  input word
    domain_synset   __  list of synsets representing the domain
    """
    word_synsets = wn.synsets(word,pos='n')
    max_similarity_score = 0
    for synset1 in domain_synset:
        for synset2 in word_synsets:
            this_score = synset1.path_similarity(synset2)
            max_similarity_score = max( max_similarity_score, this_score)
    print word, max_similarity_score
    return max_similarity_score >= thresh

def tag_domains(tagged):
    media_synset_list = media_synsets()
    domain_tagged = []
    for word, tag in tagged:
        if matches_domain(word, media_synset_list):
            tag = 'MEDIA'
        domain_tagged.append((word, tag))
    return domain_tagged

def media_synsets():
    """
    returns wordnet synsets for all words in the hardcoded list
    in the future, perhaps this list can be generated in a better way.
    """
    words = ("media|video|photo|audio|clip|movie|news|content|advertisement|"
            "footage|story|coverage|tv|program|upload|file|radio|segment")
    wordlist = words.split("|")
    synsets = []
    for word in wordlist:
        synsets += wn.synsets(word,pos='n')
    return synsets

if __name__ == "__main__":
    app.debug = True
    app.run()

