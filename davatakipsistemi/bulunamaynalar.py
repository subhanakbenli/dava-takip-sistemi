

with open("davatakipsistemi/bulunamayan.txt", "r", encoding='utf-8') as f: 
    data = f.readlines()
    data = set(data)
    with open("set.txt", "w",encoding="utf-8") as f:
        
        for line in data:
            f.write(line)    