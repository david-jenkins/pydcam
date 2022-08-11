

from functools import partial
from numpy import array
from pydcam.api.dcam import *
import toml
import yaml

SHOW_PROPERTY_ATTRIBUTE = 1
SHOW_PROPERTY_MODEVALUELIST = 1
SHOW_PROPERTY_ARRAYELEMENT = 2

printf = partial(print,end='')

def printf_attr(count, name):
    if count == 0:
        printf(name)
    else:
        printf(" | ", name)
    return count+1

def dcamcon_show_dcamdev_info( dcam:Dcam ):

    info = {}
    keys = [DCAM_IDSTR.MODEL, DCAM_IDSTR.CAMERAID, DCAM_IDSTR.BUS]

    for key in keys:
        info[key.name] = dcam.dev_getstring(key)
        if info[key.name] is False:
            print(f"Error in show info ({key.name}) -> ", dcam.lasterr().name)
    print(f"{info['MODEL']} ({info['CAMERAID']}) on {info['BUS']}")

    return info

def dcamcon_show_dcamdev_info_detail( dcam:Dcam ):
    info = {}
    for idstr in DCAM_IDSTR:
        value = dcam.dev_getstring(idstr)
        if value is False:
            print(f"{idstr.name} = {dcam.lasterr().name}")
        else:
            print(f"{idstr.name} = {value}")
            info[idstr.name] = value

    return info

def dcamcon_get_writable( dcam:Dcam ):

    iProp = dcam.prop_getnextid(0)

    if iProp is False:
        print("DCAMPROP_OPTION.SUPPORT error -> ", dcam.lasterr())
        return

    properties = {}

    while ( iProp != 0 ):

        text = dcam.prop_getname(iProp)
        if text is False:
            print(f"ERROR: dcamprop_getname({iProp})")
            return

        value = dcam.prop_getvalue(iProp)
        if value is False:
            print(f"ERROR: dcamprop_getvalue({iProp})")

        property_dict = {"name":text,"id":iProp,"value":value}

        propattr = dcam.prop_getattr(iProp)

        if propattr.is_writable():
            if propattr.attribute & DCAM_PROP.ATTR.HASRANGE:
                property_dict['min'] = propattr.valuemin
                property_dict['max'] = propattr.valuemax

            # step
            if propattr.attribute & DCAM_PROP.ATTR.HASSTEP:
                property_dict['step'] = propattr.valuestep

            # default
            if propattr.attribute & DCAM_PROP.ATTR.HASDEFAULT:
                property_dict['default'] = propattr.valuedefault

            properties[DCAM_IDPROP(iProp).name] = property_dict

        iProp = dcam.prop_getnextid(iProp)

        if iProp is False:
            print("No more properties available")
            break
            
    props = {key:value["value"] for key,value in properties.items()}
    props.update({key+".properties":value for key,value in properties.items()})
    return props

def dcamcon_show_propertyattr(propattr:DCAMPROP_ATTR, bElement = False):
    count = 0
    indent = ''
    if bElement:
        indent = "\t\t"

    printf("%sATTR:\t"%(indent))

    attr_dict = {"ATTR":[],"ATTR2":[]}

    for ATTR in DCAM_PROP.ATTR:
        if propattr.attribute & ATTR:
            count = printf_attr( count, f"{str(ATTR)}" )
            attr_dict['ATTR'].append(ATTR.name)

    for ATTR2 in DCAM_PROP.ATTR2:
        if propattr.attribute2 & ATTR2:
            count = printf_attr( count, f"{str(ATTR2)}" )
            attr_dict['ATTR2'].append(ATTR2.name)

    if count == 0:
        printf( "none" )
    printf( "\n" )


    attr_dict['TYPE'] = DCAM_PROP.TYPE(propattr.attribute & DCAM_PROP.TYPE.MASK).name
    printf("%sTYPE:\t%s\n"%(indent,attr_dict['TYPE']))

    # range
    if propattr.attribute & DCAM_PROP.ATTR.HASRANGE:
        printf( "%smin:\t%f\n"%(indent, propattr.valuemin))
        printf( "%smax:\t%f\n"%(indent, propattr.valuemax))
        attr_dict['min'] = propattr.valuemin
        attr_dict['max'] = propattr.valuemax

    # step
    if propattr.attribute & DCAM_PROP.ATTR.HASSTEP:
        printf( "%sstep:\t%f\n"%(indent, propattr.valuestep))
        attr_dict['step'] = propattr.valuestep

    # default
    if propattr.attribute & DCAM_PROP.ATTR.HASDEFAULT:
        printf( "%sdefault:\t%f\n"%(indent, propattr.valuedefault))
        attr_dict['default'] = propattr.valuedefault

    return attr_dict

def dcamcon_show_supportmodevalues(dcam:Dcam, iProp, value, bElement = False):
    indent = ''
    if bElement:
        indent = "\t\t"

    printf("%sSupport:\n"%(indent))

    pv_index = 0

    mode_dict = {"support":{}}

    while(True):
        # get value text
        pv_index = pv_index + 1
        text = dcam.prop_getvaluetext(iProp, value)
        if text is not False:
            printf( "%s\t%d:\t%s\n"%(indent, pv_index, text))
            mode_dict["support"][str(pv_index)] = text
        # get next value
        value = dcam.prop_queryvalue(iProp,value,DCAMPROP_OPTION.NEXT)
        if value is False:
            break
    return mode_dict

def dcamcon_show_arrayelement(dcam:Dcam, basepropattr:DCAMPROP_ATTR):

    if not (basepropattr.attribute2 & DCAM_PROP.ATTR2.ARRAYBASE):
        return

    printf( "Array Element:\n" )

    prop_list = []

    if SHOW_PROPERTY_ARRAYELEMENT == 2:
        # get number of array
        iProp = basepropattr.iProp_NumberOfElement
        value = dcam.prop_getvalue(iProp)
        if value is not False:

            nArray = value
            printf("\tNumber of valid element: %d\n"%(nArray))

            iProp = basepropattr.iProp
            iProp = dcam.prop_getnextid(iProp,DCAMPROP_OPTION.ARRAYELEMENT)
            
            if iProp is not False:

                while(True):

                    text = dcam.prop_getname(iProp)
                    if text is False:
                        print("ERROR in dcamprop_getname()", "IDPROP:%0x08x", iProp )
                        return

                    array_prop = {"name":text,"id":iProp}

                    printf("\t0x%08x: %s\n"%(iProp, text))

                    subpropattr = dcam.prop_getattr(iProp)
                    if subpropattr:
                        arrattr_prop = dcamcon_show_propertyattr( subpropattr, True )
                        array_prop.update(arrattr_prop)
                        if SHOW_PROPERTY_MODEVALUELIST:
                            # show mode value list of property
                            if (subpropattr.attribute & DCAM_PROP.TYPE.MASK) == DCAM_PROP.TYPE.MODE:
                                mode_dict = dcamcon_show_supportmodevalues( dcam, subpropattr.iProp, subpropattr.valuemin, True )
                                array_prop.update(mode_dict)
                    else:
                        print(f"ERROR in show_arrrayelement() -> {dcam.lasterr().name}")

                    prop_list.append(array_prop)
                    iProp = dcam.prop_getnextid(iProp, DCAMPROP_OPTION.ARRAYELEMENT)
                    if iProp is False:
                        break

    else: #if SHOW_PROPERTY_ARRAYELEMENT != 2:
        ###### SECOND ONE #####
        iProp = basepropattr.iProp_NumberOfElement
        value = dcam.prop_getvalue(iProp)

        if value is not False:
            nArray = int(value)
            printf( "\tNumber of valid element: %d\n"%(nArray) )

            for i in range(nArray):
                # get property name of array element
                iSubProp = basepropattr.iProp + i * basepropattr.iPropStep_Element
                text = dcam.prop_getname(iSubProp)
                if text is False:
                    print("ERROR in dcamprop_getname()", "IDPROP:%0x08x", iSubProp )
                    print(dcam.lasterr().name)
                    return

                printf( "\t0x%08x: %s\n"%(iSubProp, text))

                subpropattr = dcam.prop_getattr(iSubProp)
                if subpropattr:
                    array_prop = dcamcon_show_propertyattr( subpropattr, True )
                    prop_list.append(array_prop)
                    if SHOW_PROPERTY_MODEVALUELIST:
                        # show mode value list of property
                        if (subpropattr.attribute & DCAM_PROP.TYPE.MASK) == DCAM_PROP.TYPE.MODE:
                            dcamcon_show_supportmodevalues( dcam, subpropattr.iProp, subpropattr.valuemin, True )

    return prop_list



def dcamcon_show_property_list( dcam:Dcam ):

    printf( "\nShow Property List( ID: name")
    if SHOW_PROPERTY_ATTRIBUTE:
        printf( "\n\t-attribute")
    if SHOW_PROPERTY_MODEVALUELIST:
        printf( "\n\t-mode value list")
    if SHOW_PROPERTY_ARRAYELEMENT:
        printf( "\n\t-array element")
    printf( " )\n")

    iProp = dcam.prop_getnextid(0)

    if iProp is False:
        print("DCAMPROP_OPTION.SUPPORT error -> ", dcam.lasterr())
        return

    properties = {}

    while ( iProp != 0 ):
        # get property name
        # text = (ctypes.c_char * 64)()
        text = dcam.prop_getname(iProp)
        if text is False:
            print(f"ERROR: dcamprop_getname({iProp})")
            return
        value = dcam.prop_getvalue(iProp)
        if value is False:
            print(f"ERROR: dcamprop_getvalue({iProp})")
            return
        print("getting property: ",text)
        print("got value: ",value)
        property_dict = {"name":text,"id":iProp,"value":value}
        printf( "0x%08x: %s\n"%(iProp,text))

        # get property attribute

        basepropattr = dcam.prop_getattr(iProp)
        if basepropattr:

            # show property attribute
            if SHOW_PROPERTY_ATTRIBUTE:
                propattr_dict = dcamcon_show_propertyattr( basepropattr )
                property_dict.update(propattr_dict)

            if SHOW_PROPERTY_MODEVALUELIST:
                # show mode value list of property
                if (basepropattr.attribute & DCAM_PROP.TYPE.MASK) == DCAM_PROP.TYPE.MODE :
                    mode_dict = dcamcon_show_supportmodevalues( dcam, iProp, basepropattr.valuemin )
                    property_dict.update(mode_dict)

            if SHOW_PROPERTY_ARRAYELEMENT == 2:
                # show array element
                if (basepropattr.attribute2 & DCAM_PROP.ATTR2.ARRAYBASE):
                    array_list = dcamcon_show_arrayelement( dcam, basepropattr )
                    property_dict = {"0":property_dict}
                    property_dict.update({str(i+1):pd for i,pd in enumerate(array_list)})
            elif SHOW_PROPERTY_ARRAYELEMENT == 1:
                # show array element
                if (basepropattr.attribute2 & DCAM_PROP.ATTR2.ARRAYBASE):
                    array_list = dcamcon_show_arrayelement( dcam, basepropattr )
                    property_dict = {str(i):pd for i,pd in enumerate(array_list)}

        properties[DCAM_IDPROP(iProp).name] = property_dict

        # get next property id
        iProp = dcam.prop_getnextid(iProp)

        if iProp is False:
            print("No more properties available")
            return properties

def dcamcon_set_by_fname(dcam:Dcam, fname):
    if fname.suffix == ".yaml":
        with open(fname,'r') as yaml_file:
            props = yaml.safe_load(yaml_file)
    elif fname.suffix == ".toml":
        with open(fname,'r') as toml_file:
            props = toml.load(toml_file)        
    dcamcon_set_from_list(dcam, props)
    return props

def dcamcon_set_from_list(dcam:Dcam, props):
    if type(props) is dict:
        props = list(props.values())
    for prop_dict in props:
        dcamcon_set_prop_dict(dcam, prop_dict)

def dcamcon_set_prop_dict(dcam:Dcam, prop_dict):
    print(prop_dict["id"], " : ", prop_dict["set_value"])
    print(type(prop_dict["id"]), " : ", type(prop_dict["set_value"]))
    set_to = dcamcon_check_set(dcam,prop_dict["id"],prop_dict["set_value"])

    if set_to:
        print(prop_dict['name']," set to ", set_to)
    else:
        print("Failed to set ",prop_dict['name']," to ", prop_dict["set_value"])

    prop_dict["return"] = set_to

def dcamcon_check_set( dcam:Dcam, iProp, value ):
    # check whether the camera supports or not. (refer sample program propertylist to get the list of support values)
    value = dcam.prop_queryvalue(iProp, value)
    if value is False:
        print(f"ERROR in prop_queryvalue({DCAM_IDPROP(iProp)}, {value})")
        print(f"{dcam.lasterr().name}")
        return False

    # set value to the camera
    retval = dcam.prop_setgetvalue(iProp, value)
    if retval is False:
        print(f"ERROR in prop_setgetvalue({DCAM_IDPROP(iProp)}, {value})")
        print(f"{dcam.lasterr().name}")
        return False

    return retval



if __name__ == "__main__":
    from pydcam.api import OpenCamera
    from pydcam import save_config

    with OpenCamera(0) as dcam:
        model = dcam.dev_getstring(DCAM_IDSTR.MODEL)
        dcam.prop_setdefaults()
        props = dcamcon_get_writable(dcam)

    if model == "C15440-20UP":
        name = "fusion"
    else:
        name = "flash"

    save_config(props,f"{name}_config0")
