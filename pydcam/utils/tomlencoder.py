
from toml import TomlEncoder

class MyTomlEncoder(TomlEncoder):
    def dump_sections(self, o, sup, indent=0):
        retstr, retdict = super().dump_sections(o, sup)
        if retdict:
            for key,value in retdict.items():
                name = sup + "." + key if sup!="" else key
                rst, rdict = self.dump_sections(value, name, indent=indent+1)
                if rst:
                    if retstr and retstr[-2:] != "\n\n":
                        retstr += "\n"
                    retstr += "\t"*indent + "[" + name + "]\n"
                    if rst:
                        for line in rst.split("\n")[:-1]:
                            retstr += "\t"*indent + line + "\n"
            retdict = self._dict()
        return (retstr, retdict)