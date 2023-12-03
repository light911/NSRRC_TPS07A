
a = []
a.append(('oppoe',1,'23321'))
a.append(('o1231',2,'2312321'))
a.append(('oppo4124e',3,'3221'))
remove = None
print(a)
for item in a:
    if item[1] == 5:
        remove = item
if remove:
    a.remove(remove)
print(a)

# test add command
for item in a:
    new = ['op']
    for command in item:
        new.append(command)
    print(tuple(new))