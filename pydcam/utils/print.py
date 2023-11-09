


def print_dict(indict, indent=0):
    for key,value in indict.items():
        if isinstance(value,dict):
            print("\t"*indent+f"{key}: ")
            print_dict(value, indent=indent+1)
        else:
            print("\t"*indent+f"{key} : {value}")