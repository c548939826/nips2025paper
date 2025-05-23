import nltk
from tqdm import tqdm
import numpy as np
import string
import math
import torch
from multiprocessing import Process
import sys
import torch.nn.functional as F
#from stanfordcorenlp import StanfordCoreNLP
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from flair.data import Sentence
from flair.models import SequenceTagger
import time
import random
from copy import deepcopy
#from pytorch_pretrained_bert imporat BertTokenizer, BertModel, BertForMaskedLM
from transformers import BertConfig, BertTokenizer, BertModel, RobertaTokenizer, RobertaModel, BertForMaskedLM, ElectraForPreTraining, ElectraTokenizerFast, ElectraModel
from nltk.tokenize.treebank import TreebankWordTokenizer, TreebankWordDetokenizer
from GenderMutantGeneration import GenderMutantGeneration
from CountryMutantGeneration import CountryMutantGeneration
from utils import preprocessText
from ipdb import set_trace

#os.environ["CUDA_VISIBLE_DEVICES"]="6"

K_Number = 100
Max_Mutants = 10

ft = time.time()
tker = TreebankWordTokenizer()
detokenizer = TreebankWordDetokenizer()

#nlp = StanfordCoreNLP("stanford-corenlp-full-2018-02-27", port=34141, lang="en")

def check_tree (ori_tag, line):
    tag = line.strip()
    tag = nlp.pos_tag(tag)
    #print (tag)
    #print (ori_tag)
    #print ("-----------------")
    if len(tag) != len(ori_tag):
        return False
    for i in range(len(tag)):
        if tag[i][1] != ori_tag[i][1]:
            return False
    return True


def bertInit():
    #config = Ber
    berttokenizer = BertTokenizer.from_pretrained('bert-large-cased')
    bertmodel = BertForMaskedLM.from_pretrained("bert-large-cased")#'/data/szy/bertlarge')
    bertori = BertModel.from_pretrained("bert-large-cased")#'/data/szy/bertlarge')
    #berttokenizer = RobertaTokenizer.from_pretrained('bert-large-uncased')
    #bertmodel = RoBertaForMaskedLM.from_pretrained('/data/szy/bertlarge')
    electratokenizer = ElectraTokenizerFast.from_pretrained("google/electra-large-discriminator")
    electra = ElectraModel.from_pretrained("google/electra-large-discriminator")
    
    bertmodel = bertmodel.eval().to('cuda:0')   
    bertori = bertori.eval().to('cuda:1')      
    electra = electra.eval().to('cuda:2')     
    
    return bertmodel, berttokenizer, bertori, electra, electratokenizer

tokenizer = TreebankWordTokenizer()

lcache = []

tagger = SequenceTagger.load('ner')
tagger = tagger.to('cpu')

def getNEPar(inpori):
    return [[] for k in inpori]
    sents = [Sentence(k) for k in inpori]
    tagger.predict(sents)
#    sentence = inpori
    ls = []
    for sent in sents:
        l = []
        for entity in sent.get_spans('ner'):
            if "PER (" in str(entity):
                continue
            l.append(entity.text)
        ls.append(l)
    return [[] for l in ls]

def getNE(inpori):
    return []
    sent = Sentence(inpori)
    tagger.predict(sent)
#    sentence = inpori
    l = []
    for entity in sent.get_spans('ner'):
        if "PER (" in str(entity):
            continue
        l.append(entity.text)
    return []

def read2Mask():
    l = []
    kk = []
    dic = {}
    with open("./jobs.txt") as f:
        lines = f.readlines()
        l = []
        l += [line.strip() for line in lines]
        l = [k.split() for k in l]
        kk += l
        for q in l:
            for qq in q:
                if qq not in dic:
                    dic[qq] = ["jobs"]
                else:
                    dic[qq].append("jobs")
    with open("./age.txt") as f:
        lines = f.readlines()
        l = []
        l += [line.strip() for line in lines]
        l = [k.split() for k in l]
        for k in l:
            if "<PLH>" in k :
                for i in range(0,5001):
                    q = deepcopy(k)
                    q[0] = str(i)
                    l.append(q)
        kk += l
        for q in l:
            for qq in q:
                #print (q)
                #print (qq)
                if qq not in dic:
                    dic[qq] = ["age"]
                else:
                    dic[qq].append("age")
        #dic["age"] = l
    with open("./race.txt") as f:
        lines = f.readlines()
        l = []
        l += [line.strip() for line in lines]
        l = [k.split() for k in l]
        kk += l
        for q in l:
            for qq in q:
                if qq not in dic:
                    dic[qq] = ["race"]
                else:
                    dic[qq].append("race")
        #dic["race"] = l
    with open("./gender.txt") as f:
        lines = f.readlines()
        l = []
        l += [line.strip() for line in lines]
        l = [k.split() for k in l]
        kk += l
        for q in l:
            for qq in q:
                if qq not in dic:
                    dic[qq] = ["gender"]
                else:
                    dic[qq].append("gender")
        #dic["gender"] = l
    #exit()
#    for i in range(len(l)):
#        l[i] = " ".join(l[i])
    return kk, dic
encodingl = []
def BertM (bert, berttoken, inpori, bertori):
    global lcache
    global encodingl
    for k in lcache:
        if inpori == k[0]:
            return k[1], k[2]
    sentence = inpori
    
    ne = getNE(inpori)
#    print (ne)
#    if ne is None:
#        return "", []

    inputtokens = inpori.split()
    oritokens = tokenizer.tokenize(sentence)
    tokens = berttoken.tokenize(sentence)
    if len(tokens) > 400:
        raise AssertionError
    count = 0
    start = 0
    index = [0] * len(tokens)
    startlist = [0] * len(tokens)
    for i in range(len(tokens)):
        token = tokens[i]
        if "##" in token:
            index[i] = count - 1
            startlist[i] = start
        else:
            startlist[i] = i
            start = i
            index[i] = count 
            count += 1
    
    k = deepcopy(ne)
    for i in ne:
        k += i.split()
    orine = ne
    ne = k
    batchsize = 1000 // len(tokens)
    gen = []
    ltokens = ["[CLS]"] + tokens + ["[SEP]"]
#    try:
#        encoding = [[berttoken.convert_tokens_to_ids(ltokens[0:i] + ["[MASK]"] + ltokens[i + 1:]), inputtokens[index[i - 1]] in ne, [i, i + 1]] for i in range(1, len(ltokens) - 1)]#.cuda()
#    except:
#        return " ".join(tokens), gen
    used = [False] * len(tokens)
    encoding = []
    needMask, maskClass = read2Mask()
    def MaskSite(k):
        l = []
#            print (k)
        for i in range(len(k)):
            if k[i] == "[MASK]":
                l.append(i)
        return l
  
    def getEncoding(inpori, encodingq, index=None):
        def MaskSite(k):
            l = []
#            print (k)
            for i in range(len(k)):
                if k[i] == "[MASK]":
                    l.append(i)
            return l
        #print (inpori)
        newne = needMask
      
        global encodingl
        print (ne)
#        for kkk in ne:
#            newne += [kkk.split()]
#        print (newne)
        for i in range(len(newne)):
#            nm = " ".join(needMask[i])
#            if nm.lower() in inpori.lower():
#                site = inpori.lower().index(nm.lower())
#                newori = inpori[:site] + " [MASK] " + inpori[site + len(nm):]
#                if len(newori.split()) > len(inpori.split()):
#                    continue
#                newtokens = berttoken.tokenize(newori)
#                newltokens = ["[CLS]"] + newtokens + ["[SEP]"]
#                k = berttoken.convert_tokens_to_ids(newltokens)
#                l = [k, True, [MaskSite(newltokens)]]
#                if l not in encoding:
#                    encoding.append(l)
            for t in range(len(newne[i])):
                nm = newne[i][t]#needMask[i][t]
                k = " ".join(newne[i])
                if k.lower() not in inpori.lower():
                    continue
                if nm.lower() in inpori.lower():
                    site = inpori.lower().index(nm.lower())
                    newori = inpori[:site] + " [MASK] " + inpori[site + len(nm):]
                    if len(newori.split()) > len(inpori.split()):
                        continue
                    
                    newtokens = berttoken.tokenize(newori)
                    #print (newtokens)
                    for m in range(len(newtokens)):
                        if newtokens[m] == "[MASK]":
                            n = m + 1
                            for n in range(m + 1, len(tokens)):
                                if "##" not in tokens[n]:
                                    break
                            break
                    for ind in range(m, n):
                        newtokens = deepcopy(tokens)
                        newtokens[ind] = "[MASK]"
                        newltokens = ["[CLS]"] + newtokens + ["[SEP]"]
                        k = berttoken.convert_tokens_to_ids(newltokens)
                        l = [k, True, MaskSite(newltokens)]
                        if l not in encodingq:
                            if index is not None:
                                encodingl[index].append(l)
                            else:
                                encodingq.append(l)
        if index is not None:
            with open(f"mu{index}.txt", "w") as f:
                for k in encoding:
                    f.write(str(k) + "\n")
        print ("Num:", len(encodingq))
#        for i in range(len(ne)):
#            if len(ne[i].split()) > 1:
#                continue
#            newori = inpori.replace(ne[i], "[MASK]")
#            newtokens = berttoken.tokenize(newori)
#            newltokens = ["[CLS]"] + newtokens + ["[SEP]"]
#            k = berttoken.convert_tokens_to_ids(newltokens)
#            l = [k, True, MaskSite(newltokens)]
#            if l not in encoding:
#                encoding.append(l)

    getEncoding(inpori, encoding)
    length = len(encoding)
#    encodingl = [[] for i in range(length)]
#    pro = [Process(target=getEncoding, args=(" ".join(berttoken.convert_ids_to_tokens(encoding[i][0])[1:-1]), encodingl,i,)) for i in range(length)]
#    for p in pro:
#        p.start()
    def mergeseq(s1, s2):
        l = []
        for i in range(len(s1)):
            if s1[i] == s2[i]:
                l.append(s1[i])
            elif "[MASK]" in [s1[i], s2[i]]:
                l.append('[MASK]')
        return l

    for i in range(length):
        for t in range(i + 1, length):
            s = mergeseq(berttoken.convert_ids_to_tokens(encoding[i][0]), berttoken.convert_ids_to_tokens(encoding[t][0]))
            l = [berttoken.convert_tokens_to_ids(s), True, MaskSite(s)]
            if l not in encoding:
                encoding.append(l)
    encoding = encoding[::-1]
#    for p in pro:
#        p.join()
#    for i in range(length):
#        with open(f"mu{i}.txt") as f:
#            lines = f.readlines()
#            for line in lines:
#                line = eval(line)
#                if line not in encoding:
#                    pass
#                    encoding.append(line)
#    for kkk in encodingl:
#        for kkkk in kkk:
#            if kkk not in encoding:
#                encoding += kkk
    #lll = []
    
#    encoding = list(set(encoding))
#    for i in range(length):
#        getEncoding(" ".join(berttoken.convert_ids_to_tokens(encoding[i][0])[1:-1]), encoding)

    p = []
    ma = 0
    for t in range(len(encoding)):
        ma = max(ma, len(encoding[t][0]))
    for t in range(len(encoding)):
        encoding[t][0] += [0] * (ma - len(encoding[t][0]))
    for i in range(0, len(encoding), batchsize):
        tensor = [k[0] for k in encoding[i: min(len(encoding), i + batchsize)]]
        tensor = torch.tensor(tensor).cuda()
        pre = F.softmax(bert(tensor)[0], dim=-1).data.cpu()
        p.append(pre)
    if len(p) == 0:
        return " ".join(tokens), []
        #continue
    pre = torch.cat(p, 0)
    tarl = [[tokens, -1]]
    allc = []
    for k in needMask:
        for q in k:
            if q != "a":
                allc.append(q)

    for i in range(len(encoding)):
        wordindex = encoding[i][2]
        topks = []
        values = []
        flag = True
        for index in wordindex:
#            print (tokens)
#            print (wordindex)
            isne = encoding[i][1]
            if not isne:
                flag = False
                continue
            if tokens[index - 1] in string.punctuation:
                flag = False
                continue
            topk = torch.topk(pre[i][index], K_Number)#.tolist()
            value = topk[0].numpy()
            topk = topk[1].numpy().tolist()
            topkTokens = berttoken.convert_ids_to_tokens(topk)
            topks.append(topkTokens)
            values.append(value)
        if not flag:
            continue
        assert len(wordindex) != 0
        sentences = []
        ttlist = []
        tarlcandi = []
        llist = []
        wordindexlist = []
        valuelist = []
        isnelist = []
        if len(wordindex) == 1:
            for index in range(len(topkTokens)):
                if value[index] < 0.01:
                    break
                tt = topkTokens[index]
                if tt in string.punctuation:
                    continue
  #              print (tt.strip(), tokens[wordindex[0] - 1])
                if tt.strip().lower() == tokens[wordindex[0] - 1].lower():
                    continue
                l = deepcopy(tokens)
                l = l[:wordindex[0] - 1] + [tt] + l[wordindex[0]:]
                finaltt = ""
                nowindex= wordindex[0]
                while nowindex >= 0 and "##" in tt:
                    finaltt = tt.replace("##", "") + finaltt
                    tt = l[nowindex]
                    nowindex -= 1
                finaltt = tt + finaltt
                tt = finaltt
                ttlist.append([tt])
                sentences.append(" ".join(l).replace(" ##", ""))
#                llist.append(l)
#                wordindexlist.append(wordindex)
#                valuelist.append(value[index])
#                isnelist.append(isne)
                tarlcandi.append([l, wordindex, value[index], isne])
                #print (tt)
#                if isne:
#                    newne = getNE(" ".join(l).replace(" ##", ""))
#                    k = deepcopy(newne)
#                    for ttt in newne:
#                        k += ttt.split()
#                    newne = k
#                    if newne is None or (tt not in newne and tt not in allc): 
#                        continue
    #                else:

#                tarl.append([l, wordindex, value[index], isne])
        else:
            #for m in range(len(wordindex)):
            tts = [[], []]
 #           print (topks)
            for kkk in range(2):
                for index in range(len(topks[kkk])):
                    if values[kkk][index] < 0.01:
                        break
#                    if values[kkk][index] > 0.10:
#                        break
                    tt = topks[kkk][index]
                    if tt in string.punctuation:
                        continue
#                    print (tt.strip(), tokens[wordindex[kkk] - 1])
                    if tt.strip().lower() == tokens[wordindex[kkk] - 1].lower():
                        continue
                    tts[kkk].append(tt)
            
#            for kkk in range(2)
            for tt1 in tts[0]:
                for tt2 in tts[1]:
#                    if tt1 == tt2:
#                        continue
                    l = deepcopy(tokens)
                    l = l[:wordindex[0] - 1] + [tt1] + l[wordindex[0]:]
                    l = l[:wordindex[1] - 1] + [tt2] + l[wordindex[1]:]
                    flag = False
                    for iii in range(len(l)):
                        if tokens[iii] != l[iii]:
                            if " ".join(tokens[iii]) not in " ".join(l[iii]) and " ".join(l[iii]) not in " ".join(tokens[iii]): #maskClass[tokens[iii]] not in maskClass[l[iii]]:
                                flag = True
                                break
                    if flag:
                        continue
                    finaltt1 = ""
                    nowindex= wordindex[0]
                    while nowindex >= 0 and "##" in tt1:
                        finaltt1 = tt1.replace("##", "") + finaltt1
                        tt1 = l[nowindex]
                        nowindex -= 1
                    finaltt1 = tt1 + finaltt1
                    tt1 = finaltt1
                    
                    finaltt2 = ""
                    nowindex= wordindex[1]
                    while nowindex >= 0 and "##" in tt2:
                        finaltt2 = tt2.replace("##", "") + finaltt2
                        tt2 = l[nowindex]
                        nowindex -= 1
                    finaltt2 = tt2 + finaltt2
                    tt2 = finaltt2
                    if tt1 == tt2 and abs(wordindex[0] - wordindex[1]) <= 1:
                        continue
                    ttlist.append([tt1, tt2])
                    sentences.append(" ".join(l).replace(" ##", ""))
                    tarlcandi.append([l, wordindex, value[index], isne])
            #tts[kkk].append(tt)
#            print (tt)
#                    if isne:
            #
            #for q in range(len(sentences)):
            newnes = getNEPar(sentences)
            for q in range(len(newnes)):
#            k = deepcopy(newne)
                length = len(newnes[q])
                for ttt in range(length):
                     newnes[q] += newnes[q][ttt].split()
                #newne = k
                if newnes[q] is None:
                    continue 
                flag = True
                for tt in ttlist[q]:
                    if (tt not in newnes[q] and tt not in allc):# or (tt2 not in newne and tt2 not in allc): 
                        flag = False
                        break
#                else:
                if flag:
                    tarl.append(tarlcandi[q])#[l, wordindex, value[index], isne])
            
    if len(tarl) == 0:
        return " ".join(tokens), gen
        
    
    
    lDB = []
    #batchsize = 100

    #oriencoding = bertori(torch.tensor([berttoken.convert_tokens_to_ids(ltokens)]).cuda())[0][0].data.cpu().numpy()
    #oriencoding = bertori(torch.tensor([berttoken.convert_tokens_to_ids(ltokens)]).cuda())[0][0].data.cpu().numpy()
    ma = 0
    tensor = [berttoken.convert_tokens_to_ids(["[CLS]"] + l[0] + ["[SEP]"]) for l in tarl]
    for t in range(len(tensor)):
        ma = max(ma, len(tensor[t]))
    #for t in range(len(encoding)):
    #    encoding[t][0] += [0] * (ma - len(encoding[t][0]))
    for i in range(0, len(tarl), batchsize):
        tensor = [berttoken.convert_tokens_to_ids(["[CLS]"] + l[0] + ["[SEP]"]) for l in tarl[i: min(i + batchsize, len(tarl))]]
    #    ma = 0
    #    for t in range(len(tensor)):
    #        ma = max(ma, len(tensor[t]))
        for t in range(len(tensor)):
            tensor[t] += [0] * (ma - len(tensor[t]))
        tensor = torch.tensor(tensor).to('cuda:1')
        #tarlist = tarl[i: min(len(tarl), i + 300]
        lDB.append(bertori(tensor)[0].data.cpu().numpy())
    lDB = np.concatenate(lDB, axis=0)
            
    #print ("-----------------")
    #print (len(lDB))
    #print (len(tarl))
    lDA = lDB[0]
    assert len(lDB) == len(tarl)
    tarl = tarl[1:]
    lDB = lDB[1:]
    for t in range(len(lDB)):
        cossim = 2
        #if not tarl[t][3]:
        flag = True
        print ("--")
        print (tarl[t][1])
        for k in range(len(tarl[t][1])):
            DB = lDB[t][tarl[t][1][k]]
            DA = lDA[tarl[t][1][k]]
            cossim = np.sum(DA * DB) / (np.sqrt(np.sum(DA * DA)) * np.sqrt(np.sum(DB * DB)))
            print (cossim)
            if cossim >= 0.85:
                flag = False
                break
            if cossim <= 0.5:
                flag = False
                break
        if flag:
            sen = " ".join(tarl[t][0])# + "\t!@#$%^& " + str(math.exp(value[index]))#.replace(" ##", "")
            gen.append([cossim, sen])
    if len(lcache) > 4:
        lcache = lcache[1:]    

    lcache.append([inpori, " ".join(tokens), gen])
    return " ".join(tokens), gen#.replace(" ##", ""), gen

f = open(sys.argv[1])
lines = f.readlines()
f.close()

l = []
for i in range(len(lines)):
    l.append(lines[i].strip())

bertmodel, berttoken, bertori, electra, electratokenizer = bertInit()

def detk(sent):
    return " ".join(tker.tokenize(detokenizer.detokenize(sent.split())))

def tk(sent):
    return " ".join(tker.tokenize(sent))

countct = 0
countgd = 0
countb = 0
f = open(sys.argv[2], "w")
fline = open(sys.argv[3], "w")
for i in tqdm(range(len(l))):
    line = l[i]
    print(line)
    text = preprocessText(line)
    # print("preprocessText")
    mg = GenderMutantGeneration(text)
    # print("GenderMutantGeneration")
    #continue
    mg2 = CountryMutantGeneration(text)
#    print (mg.getMutants())
#    print (mg2.getMutants())
    count = 0
    print ("=[===-=-=-=-=-=-=-")
    #continue
    #tag = nlp.pos_tag(line)
    try:
        tar, gen = BertM(bertmodel, berttoken, line, bertori)
    except:
        continue
    gen = sorted(gen)[::-1]
    count = 0
    for sen in gen:
        sen[1] = sen[1].replace(" ##", "")
        print ("Output: ")
        print (tar)
        print (sen)
        li = [detk(l[i].strip()), detk(sen[1].strip())]
        if li not in usedd:
            usedd.append(deepcopy(li))
            usedd.append(deepcopy([li[1], li[0]]))
        else:
            continue
        f.write(detk(tar.replace(" ##", "")).strip() + "\n")
        f.write(tk(sen[1]).strip() + "\n")
#        f.flush()
        fline.write(str(i) + "\n")
        count += 1
        countb += 1
        if count >= Max_Mutants:
            break
    count = 0
    usedd = []
    dic = {}
    
    for i in range(len(mg.getMutants())):
        sen = mg.mutants[i]
        gender = mg.genders[i]
        if gender not in dic:
            dic[gender] = [sen]
        else:
            dic[gender].append(sen)

    llll = list(dic.keys())
    macount = 1
    for k in dic:
        macount *= len(dic[k])
    if len(dic) <= 1:
        macount = 0
#    macount = min(macount, Max_Mutants) 
    while count < min(macount, Max_Mutants):
#        break
        index1 = random.randint(0, len(dic) - 1)
        index2 = random.randint(0, len(dic) - 1)
        while index1 == index2:
            index2 = random.randint(0, len(dic) - 1)
#        print (llll)
        index11 = random.randint(0, len(dic[llll[index1]]) - 1)
        index21 = random.randint(0, len(dic[llll[index2]]) - 1)
        n = [tk(dic[llll[index1]][index11]), tk(dic[llll[index2]][index21])]
        if n not in usedd:
            usedd.append(deepcopy(n))
            n1 = [n[1], n[0]]
            usedd.append(deepcopy(n1))
        else:
            continue
        print ("Output: ")
        print (n[0])
        print (n[1])
        countgd += 1
        f.write("Gen:\t" + llll[index1] + "\t" + detk(n[0]).strip() + "\n")
        f.write("Gen:\t" + llll[index2] + "\t" + tk(n[1]).strip() + "\n")
        fline.write(str(i) + "\n")
        count += 1
#    continue
    dic = {}
    count = 0
f.close()
fline.close()
print (countgd, countct, countb)
print (time.time() - ft)
