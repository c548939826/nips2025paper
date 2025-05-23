from ipdb import set_trace
import os
import sys

flag = sys.argv[1]
# flag = "0508_gpt4o_0.80"
base_dir = f"../../experiments/{flag}/country"


with open(os.path.join(base_dir,"./Com_BERT.txt"), "r") as f:
    lines = f.readlines()

DATA = [[lines[i + 4].strip().replace(" ", "").replace("\t", "")] + [(lines[i + 2].strip() + lines[i + 4].strip()).replace(" ", "").replace("\t", "")] + [lines[i + t].strip() for t in range(7)] for i in range(0, len(lines), 7)]


with open(os.path.join(base_dir,"./Com_BERT_F.txt"), "r") as f:
    lines = f.readlines()

#DATAori = [[lines[i + 4].strip().replace(" ", "").replace("\t", "").replace("Gen:male", "").replace("Gen:female", "")] + [(lines[i + 2].strip() + lines[i + 4].strip()).replace(" ", "").replace("\t", "").replace("Gen:male", "").replace("Gen:female", "")] + [lines[i + t].strip() for t in range(7)] for i in range(0, len(lines), 7)]
DATAori = [[" ".join(lines[i + 4].strip().split("\t")[2:]).replace(" ", "")] + [(" ".join(lines[i + 2].strip().split("\t")[2:]) + " ".join(lines[i + 4].strip().split("\t")[2:])).replace(" ", "")] + [lines[i + t].strip() for t in range(7)] for i in range(0, len(lines), 7)]

def getscore(data):
    return float(data[2].split()[0].replace("[", "").replace(",", ""))

dictori = {}
print (len(DATAori))
print (len(DATA))



for data in DATAori:
#    print (data)
    dictori[data[0].replace(" ", "")] = [data, [getscore(data)]]
#    print (data[0].replace("Gen:male", "").replace("Gen:female", ""))
#    print (data[0])
    #print ([data, [getscore(data)]])
#print (dictori)
for data in DATA:
    if data[0] in dictori:
        if data[1] != dictori[data[0]][0][1]:
            #print (1)
            dictori[data[0]][1].append(getscore(data))

with open(os.path.join(base_dir,"./finalscore.txt"), "w") as f:
    for item in dictori:
        for k in dictori[item][0][2:]:
            f.write(k + "\n")
        
        f.write(str(dictori[item][1]) + "\n")
#print ()