import json

# These should not be code-generated
ignored_schems = ['ProtocolMessage', 'Request', 'Event', 'Response']
prop_name_to_field = {'type':'type_', '__restart':'restart__'}
field_name_to_prop = dict([(v,k) for k,v in prop_name_to_field.items()])

dap_json = json.load(open('debugProtocol.json'))

indent = 0

def deref(ref):
    prefix = '#/definitions/'
    if ref.startswith(prefix):
        name = ref[len(prefix):]
        return RefObject(name)
    else:
        return False


class Integer(object):
    def s(self):
        return 'int'

    def to_json(self, f):
        if f:
            return '(Int.toJson {})'.format(f)
        else:
            return 'Int.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Integer)


class Real(object):
    def s(self):
        return 'real'

    def to_json(self, f):
        if f:
            return '(Real.toJson {})'.format(f)
        else:
            return 'Real.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Real)


class Boolean(object):
    def s(self):
        return 'bool'

    def to_json(self, f):
        if f:
            return '(Bool.toJson {})'.format(f)
        else:
            return 'Bool.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Boolean)


class String(object):
    def s(self):
        return 'string'

    def to_json(self, f):
        if f:
            return '(String.toJson {})'.format(f)
        else:
            return 'String.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, String)


class IntOrString(object):
    def s(self):
        return 'IntOrString'

    def to_json(self, f):
        if f:
            return '(IntOrString.toJson {})'.format(f)
        else:
            return 'IntOrString.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, IntOrString)


class NullableString(object):
    def s(self):
        return 'NullableString'

    def to_json(self, f):
        if f:
            return '(NullableString.toJson {})'.format(f)
        else:
            return 'NullableString.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, NullableString)


class StringMap(object):
    def __init__(self, e):
        self.e = e

    def s(self):
        return '({} StringMap)'.format(self.e.s())

    def to_json(self, f):
        if f:
            return '(StringMap.toJson ({},{}))'.format(self.e.to_json(), f)
        else:
            return 'StringMap.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, StringMap)


class JsonObject(object):
    def s(self):
        return 'Json.OBJECT'

    def to_json(self, f):
        if f:
            return f
        else:
            return 'id'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, JsonObject)


class Array(object):
    def __init__(self, e):
        self.e = e

    def s(self):
        return '({} array)'.format(self.e.s())

    def to_json(self, f):
        if f:
            return 'Array.map ({}, {})'.format(self.e.to_json(False), f)
        else:
            return 'TODO Array.map ({}, {})'.format(self.e.to_json(False), f)

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Array) and self.e == other.e


class RefObject(object):
    def __init__(self, n):
        self.name = n

    def s(self):
        return self.name

    def to_json(self, f):
        if f:
            return '({}.toJson {})'.format(self.name, f)
        else:
            return '{}.toJson'.format(self.name)

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return other.name==self.name


class Record(object):
    def __init__(self, rec):
        self.rec = rec

    def s(self):
        tmp = []
        for k,v in self.rec['properties'].items():
            assert hasattr(v,'s')
            tmp.append('  {}: {}'.format(k,v.s()))
        fields = ',\n'.join(tmp)
        return '{{\n{}\n}}'.format(fields)

    def to_json(self, f):
        if f:
            fields = []
            for k,v in self.rec['properties'].items():
                fields.append('("{}", {})'.format(k, v.to_json('(#{} {})'.format(k, f))))
            return '(Json.OBJECT [{}])'.format(', '.join(fields))
        else:
            return 'id'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Record) and self.rec==other.rec


class Option(object):
    def __init__(self, o):
        self.o = o

    def s(self):
        return '({} option)'.format(self.o.s())

    def to_json(self, f):
        if f:
            return '(Option.toJson ({},{}))'.format(self.o.to_json(False), f)
        else:
            return 'TODO Option.toJson {}'.format(self.o.to_json(False))

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Option) and self.o==other.o


class Enum(object):
    def __init__(self, values):
        self.values = values

    def s(self):
        'datatype {} = '

    def to_json(self, f):
        if f:
            return '"{}"'.format(f)
        else:
            return 'TODO ENUM'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Enum) and self.values==other.values


class Unimplemented(object):
    def __init__(self, o):
        self.o = o

    def s(self):
        return str(self.o)

    def to_json(self, f):
        return 'Unimplemented.toJson ({})'.format(self.s())

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return False


def lookup(converted, o):
    if '$ref' in o:
        n = deref(o['$ref'])
        if n.s() in converted.keys():
            return converted[n.s()]
        else:
            print('ERROR: {} not found in converted'.format(n.s()))
    else:
        return convert_obj(name, o)


def type_union(ta, tb):
    if ta==tb:
        return ta

    elif isinstance(ta,Unimplemented) and (not isinstance(tb,Unimplemented)):
        return tb
    elif (not isinstance(ta,Unimplemented)) and isinstance(tb,Unimplemented):
        return ta

    elif isinstance(ta, Option) and isinstance(tb, Option):
        return Option(type_union(ta.o, tb.o))

    elif isinstance(ta, Option) and isinstance(ta.o, JsonObject) and not isinstance(tb, (Unimplemented,JsonObject)):
        return tb
    elif isinstance(tb, Option) and isinstance(tb.o, JsonObject) and not isinstance(ta, (Unimplemented,JsonObject)):
        return ta


    elif isinstance(ta, JsonObject) and (not isinstance(tb, JsonObject)):
        return tb
    elif (not isinstance(ta, JsonObject)) and isinstance(tb, JsonObject):
        return ta

    else:
        print(ta)
        print(tb)
        assert False


def intersect(a, b):
    pa = a['properties']
    pb = b['properties']

    ka = set(pa.keys())
    kb = set(pb.keys())

    out = dict()

    for k in ka.intersection(kb):
        out[k] = type_union(pa[k], pb[k])

    for k in ka.difference(kb):
        out[k] = pa[k]

    for k in kb.difference(ka):
        out[k] = pb[k]

    return out


def obj_list_intersection(converted, objs):
    olist = [lookup(converted, o) for o in objs]

    out = {'properties':{}}
    for o in olist:
        out['properties'] = intersect(out, o)

    return out['properties']


def i_print(s):
    global indent

    idnt = ''
    for _i in range(indent):
        idnt = ' ' + idnt

    s = s.replace('\n', '\n'+idnt)
    s = idnt + s

    print(s)

def is_basic(descr):
    if 'type' not in descr:
        if '$ref' in descr:
            return deref(descr['$ref'])
        else:
            return False
    t = descr['type']
    if t=='integer':
        return Integer()
    elif t == 'number':
        return Real()
    elif t=='string':
        return String()
    elif t=='boolean':
        return Boolean()
    elif t=='array':
        e = is_basic(descr['items'])
        if e:
            return Array(e)
        else:
            return False
    elif t=='object' and 'properties' in descr:
        return Record(convert_obj('tmp', descr))
    elif t == 'object' and 'additionalProperties' in descr and set(descr['additionalProperties']['type']) == {'string', 'null'}:
        return StringMap(NullableString())
    elif t == 'object' and 'additionalProperties' in descr and set([descr['additionalProperties']['type']]) == {'string'}:
        return StringMap(String())
    elif isinstance(t,list) and set(t)=={'integer','string'}:
        return IntOrString()
    elif isinstance(t, list) and set(t) == {'null', 'string'}:
        return NullableString()
    elif isinstance(t, list) and set(t) == {'array', 'boolean', 'integer', 'null', 'number', 'object', 'string'}:
        return JsonObject()
    else:
        return False

def get_prop_type(opt_props, name, descr):
    basic_descr = is_basic(descr)
    if basic_descr:
        if name in opt_props:
            return Option(basic_descr)
        else:
            return basic_descr
    else:
        return Unimplemented(descr)

def convert_obj(name, obj):
    desc = obj.get('description','')
    o = {'name':name, 'description':desc, 'properties':{}}

    import copy
    if 'properties' in obj:
        ks = list(obj['properties'].keys())
        for k in ks:
            if k in prop_name_to_field:
                obj['properties'][prop_name_to_field[k]] = obj['properties'][k]
                del obj['properties'][k]

    props = set(obj['properties'].keys()) if 'properties' in obj else set()
    req_props = set(obj['required']) if 'required' in obj else props
    opt_props = props.difference(req_props)

    if props:
        for prop_name, prop_descr in obj['properties'].items():
            basic_descr = get_prop_type(opt_props, prop_name, prop_descr)
            o['properties'][prop_name] = basic_descr

    return o


def convert_enum(name, obj):
    desc = obj.get('description','')
    o = {'name':name, 'description':desc, 'enum':Enum(obj['enum'])}
    return o


def print_obj(obj):
    global indent
    i_print('structure {} = struct'.format(obj['name']))
    indent += 2
    i_print('(* {} *)'.format(obj['description']))

    i_print('type t = {')
    fields = []
    for prop_name,prop_type in obj['properties'].items():
        fields.append('{}: {}'.format(prop_name, prop_type.s()))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print('}')

    print()
    print()

    i_print('fun toJson (x : t) = Json.OBJECT [')
    fields = []
    for prop_name,prop_type in obj['properties'].items():
        fields.append('("{}", {})'.format(field_name_to_prop.get(prop_name,prop_name), prop_type.to_json('(#{} x)'.format(prop_name))))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print(']')


    indent -= 2
    i_print('end\n')


def print_enum(obj):
    global indent
    i_print('structure {} = struct'.format(obj['name']))
    indent += 2
    i_print('(* {} *)'.format(obj['description']))

    props = set(obj['properties'].keys()) if 'properties' in obj else set()

    tmp = 'datatype t = ' + ' | '.join(obj['enum'].values)

    i_print(tmp)

    print()
    print()

    i_print('fun toJson x = case x of')
    indent += 2
    first = True
    for e in obj['enum'].values:
        if first:
            first = False
            i_print('  {} => "{}"'.format(e, e))
        else:
            i_print('| {} => "{}"'.format(e, e))
    indent -= 2

    indent -= 2
    i_print('end\n')


converted = {}
for name, schem in dap_json['definitions'].items():
    if 'allOf' in schem:
        obj = {'name':name, 'description':'TODO'}
        converted[name] = obj
        converted[name]['properties'] = obj_list_intersection(converted, schem['allOf'])
    elif '_enum' in schem:
        schem['enum'] = schem['_enum']
        converted[name] = convert_enum(name, schem)
    elif 'enum' in schem:
        converted[name] = convert_enum(name, schem)
    elif 'type' in schem and schem['type'] == 'object':
        converted[name] = convert_obj(name,schem)
    else:
        assert False

header = '''
fun id x = x

structure Option = struct
  fun toJson (f,v) = case v of
      NONE => Json.NULL
    | SOME v' => f v'
end

structure Int = struct
  type t = int
  
  fun toJson x = Json.INT x
end

structure Real = struct
  type t = real
  
  fun toJson x = Json.NUMBER x
end

structure String = struct
  type t = string
  
  fun toJson x = Json.STRING x
end

structure Bool = struct
  type t = bool
  
  fun toJson x = Json.BOOL x
end

structure NullableString = struct
  type t = string option
  
  fun toJson x = case x of
      SOME s => String.toJson s
    | NONE => Json.NULL
end

structure IntOrString = struct
  datatype t = IsInt of int | IsString of string
  
  fun toJson x = case x of
      IsInt i => Int.toJson i
    | IsString s => String.toJson s
end
'''

i_print(header)

for name, schem in converted.items():
    if name in ignored_schems:
        continue
    if 'enum' in schem:
        print_enum(schem)
    else:
        print_obj(schem)
