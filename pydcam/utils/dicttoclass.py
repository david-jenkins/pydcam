
from pydcam import CONF_DIR
import toml

def dict_to_class(indict:dict, classname:str) -> str:

    file_str = f"\n\nclass {classname}:\n"

    for key,value in indict.items():
        name = key.replace(" ","_").replace("[","").replace("]","")
        file_str += f"    class {name}:\n"
        for key,val in value.items():
            if isinstance(val,str):
                file_str += f"        {key} = '{val}'\n"
            else:
                file_str += f"        {key} = {val}\n"

    file_str += "    @classmethod\n    def get(cls, name):\n        return getattr(cls, name.replace(' ','_').replace('[','').replace(']',''))"

    file_str += f"\n\nif __name__ == '__main__':\n    i = {classname}.get('SYSTEM ALIVE')"+"\n    print(', '.join([f'{key} = {value}' for key,value in vars(i).items() if '__' not in key]))"

    return file_str

if __name__ == "__main__":

    classname = "ORCAPROPS"

    with open(CONF_DIR/"orca_raw_properties.toml", 'r') as toml_file:
        tprops = toml.load(toml_file)

    file_str = dict_to_class(tprops, classname)

    with open(f"{classname}_class.py","w") as fh:
        fh.write(file_str)
