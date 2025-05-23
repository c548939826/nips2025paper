import sys
import os

flag=sys.argv[2]
base_dir = f"../../experiments/{flag}/country"

with open(os.path.join(base_dir,"Com_BERT.txt")) as f:
    lines = f.readlines()

Data = [[lines[t + i].strip() for t in range(7)]for i in range(0, len(lines), 7)]

def writedata(data, fi):
    for da in data:
        fi.write(da + "\n")

with open(os.path.join(base_dir,"Com_BERT_F.txt"), "w") as f:
    for data in Data:
        score = data[0].strip().split()[0].replace("[", "").replace(",", "")
        score = float(score)
        if score < float(sys.argv[1]):
#            if "Gen:\t" in data[2]:
            writedata(data, f)
                #                f.write(" ".join(data[2].split("\t")[2:]) + "\n")
#                f.write(" ".join(data[4].split("\t")[2:]) + "\n")
#            else: 
#                f.write(data[2] + "\n")
#                f.write(data[4] + "\n")

    #lines = f.readlines()

with open(os.path.join(f"../../experiments/{flag}","en_tk.txt"), "w") as f:
    for data in Data:
        score = data[0].strip().split()[0].replace("[", "").replace(",", "")
        score = float(score)
        if score < float(sys.argv[1]):
            if "Gen:\t" in data[2]:
                f.write(" ".join(data[2].split("\t")[2:]) + "\n")
                f.write(" ".join(data[4].split("\t")[2:]) + "\n")
            else: 
                f.write(data[2] + "\n")
                f.write(data[4] + "\n")



