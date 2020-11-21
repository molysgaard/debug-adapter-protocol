import json
import toposort

# These should not be code-generated
ignored_schems = ['ProtocolMessage', 'Request', 'Event', 'Response']
prop_name_to_field = {'type':'type_', '__restart':'restart__'}
field_name_to_prop = dict([(v,k) for k,v in prop_name_to_field.items()])

dap_json = json.load(open('debugProtocol.json'))

indent = 0

class UnknownRefException(Exception):
    def __init__(self, converted, n):
        self.converted = converted
        self.n = n

    def __str__(self):
        return 'Couldnt find {} in {}'.format(self.n, self.converted)

def deref(converted, schem):
    ref = schem['$ref']
    prefix = '#/definitions/'
    assert ref.startswith(prefix)

    name = ref[len(prefix):]
    if name in converted:
        return converted[name]
    else:
        raise UnknownRefException(converted, name)

def deref_if_ref(converted, obj):
    if isinstance(obj, RefObj):
        prefix = '#/definitions/'
        assert obj.ref.startswith(prefix)

        name = obj.ref[len(prefix):]
        if name in converted:
            return converted[name]
        else:
            raise UnknownRefException(converted, name)
    else:
        return obj

class UnionException(Exception):
    def __init__(self, cur, new):
        self.cur = cur
        self.new = new

    def __str__(self):
        return 'Could not union:\n  {}\n  {}'.format(self.cur, self.new)


def process_union(converted, objs, schem):
    dereffed_ojbs = []
    for o in objs:
        dereffed_ojbs.append(deref_if_ref(converted, o))

    out_obj = dereffed_ojbs[0]
    for o in dereffed_ojbs:
        out_obj = out_obj.union(o)

    return out_obj

def make(converted, name, schem):
    if 'allOf' in schem:
        obj = process_union(converted, [make(converted, name, o) for o in schem['allOf']], schem)
        obj.name = name
        obj.descr = schem.get('description', obj.descr)
        return obj
    elif 'type' not in schem and '$ref' in schem:
        return RefObj(name, schem)

    t = schem['type']
    if t=='integer':
        return Integer(schem)
    elif t == 'number':
        return Real(schem)
    elif t=='string':
        return String(schem)
    elif t=='boolean':
        return Boolean(schem)
    elif t=='array':
        tmp = make(converted, name, schem['items'])
        return Array(tmp)
    elif t=='object' and 'properties' in schem:
        return Record(converted, name, schem)
    elif t == 'object' and 'additionalProperties' in schem and set(schem['additionalProperties']['type']) == {'string', 'null'}:
        return StringMap(NullableString(schem))
    elif t == 'object' and 'additionalProperties' in schem and {schem['additionalProperties']['type']} == {'string'}:
        return StringMap(String(schem))
    elif t=='object' and set(schem.keys()) == {'description','type'}:
        return JsonObject(schem)
    elif isinstance(t,list) and set(t) == {'integer','string'}:
        return IntOrString(schem)
    elif isinstance(t, list) and set(t) == {'null', 'string'}:
        return NullableString(schem)
    elif isinstance(t, list) and set(t) == {'array', 'boolean', 'integer', 'null', 'number', 'object', 'string'}:
        return JsonObject(schem)
    elif 'enum' in schem or '_enum' in schem:
        return Enum(name, schem)
    else:
        assert False

class TypeBase(object):
    def __init__(self, schem):
        self.descr = schem.get('description', '')

    def deps(self):
        return set()

    def union(self, other):
        if self == other:
            return self
        else:
            raise UnionException(self, other)


class Enum(TypeBase):
    def __init__(self, name, schem):
        self.name = name
        self.descr = schem.get('description', '')
        self.values = schem.get('enum', schem.get('_enum'))

    def s(self):
        'datatype {} = '

    def to_json(self, f):
        if f:
            return '"{}"'.format(f)
        else:
            assert False

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Enum) and self.values==other.values


class RefObj(TypeBase):
    def __init__(self, name, schem):
        self.name = name
        self.descr = schem.get('description', '')
        self.ref = schem['$ref']

    def s(self):
        return self.parse_name()

    def to_json(self, f):
        if f:
            return '"{}"'.format(f)
        else:
            return '{}.toJson'.format(self.parse_name())

    def parse_name(self):
        prefix = '#/definitions/'
        assert self.ref.startswith(prefix)
        return self.ref[len(prefix):]

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Enum) and self.values==other.values

    def union(self, other):
        assert False, 'Union called for RefObj which should never happen'

class Record(TypeBase):
    def __init__(self, *args):
        if isinstance(args[0], str):
            self.from_internal(*args)
        else:
            self.from_json(*args)

    def from_internal(self, name, descr, props):
        self.name=name
        self.descr=descr
        self.props=props
        self.deps = set()

    def from_json(self, converted, name, obj):
        self.name = name
        self.descr = obj.get('description','')
        self.props = {}
        self.deps = set()

        deps = set()

        # first we rename any properties that should be renamed because of name classeh with SML syntax
        if 'properties' in obj:
            ks = list(obj['properties'].keys())
            for k in ks:
                if k in prop_name_to_field:
                    obj['properties'][prop_name_to_field[k]] = obj['properties'][k]
                    del obj['properties'][k]

        # compute which properties are required and not
        props = set(obj['properties'].keys()) if 'properties' in obj else set()
        req_props = set(obj['required']) if 'required' in obj else props
        opt_props = props.difference(req_props)

        if props:
            for prop_name, prop_descr in obj['properties'].items():
                #basic_descr = get_prop_type(opt_props, prop_name, prop_descr)
                basic_descr = make(converted, prop_name, prop_descr)
                self.props[prop_name] = basic_descr

    def s(self):
        tmp = []
        for k,v in self.props.items():
            assert hasattr(v,'s')
            tmp.append('  {}: {}'.format(k,v.s()))
        fields = ',\n'.join(tmp)
        return '{{\n{}\n}}'.format(fields)

    def to_json(self, f):
        if f:
            fields = []
            for k,v in self.props.items():
                fields.append('("{}", {})'.format(k, v.to_json('(#{} {})'.format(k, f))))
            return '(Json.OBJECT [{}])'.format(', '.join(fields))
        else:
            return 'id'

    def deps(self):
        d = set()
        for v in self.props.values():
            d = d.union(v.deps())

        return d

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Record) and self.props==other.props

    def union(self, other):
        if isinstance(other, Record):
            n_props = {}
            all_keys = set(self.props.keys()).union(set(other.props.keys()))
            for k in all_keys:
                if k in self.props and not k in other.props:
                    n_props[k] = self.props[k]
                elif not k in self.props and k in other.props:
                    n_props[k] = other.props[k]
                else:
                    n_props[k] = self.props[k].union(other.props[k])

            return Record(self.name, self.descr, n_props)
        elif isinstance(other, JsonObject):
            return self
        else:
            raise UnionException(self, other)


class Integer(TypeBase):
    def __init__(self, schem):
        super(Integer, self).__init__(schem)

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


class Real(TypeBase):
    def __init__(self, schem):
        super(Real, self).__init__(schem)

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


class Boolean(TypeBase):
    def __init__(self, schem):
        super(Boolean, self).__init__(schem)

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


class String(TypeBase):
    def __init__(self, schem):
        super(String, self).__init__(schem)

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


class IntOrString(TypeBase):
    def __init__(self, schem):
        super(IntOrString, self).__init__(schem)

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


class NullableString(TypeBase):
    def __init__(self, schem):
        super(NullableString, self).__init__(schem)

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


class StringMap(TypeBase):
    def __init__(self, e):
        self.e = e

    def s(self):
        return '({} StringMap)'.format(self.e.s())

    def to_json(self, f):
        if f:
            return '(StringMap.toJson ({},{}))'.format(self.e.to_json(f), f)
        else:
            return 'StringMap.toJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, StringMap)


class JsonObject(TypeBase):
    def __init__(self, schem):
        super(JsonObject, self).__init__(schem)

    def s(self):
        return 'Json.t'

    def to_json(self, f):
        if f:
            return f
        else:
            return 'id'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, JsonObject)


    def union(self, other):
        return other


class Array(TypeBase):
    def __init__(self, e):
        self.e = e

    def s(self):
        return '({} array)'.format(self.e.s())

    def to_json(self, f):
        if f:
            return 'Array.map ({}, {})'.format(self.e.to_json(False), f)
        else:
            return 'TODO Array.map ({}, {})'.format(self.e.to_json(False), f)

    def deps(self):
        return self.e.deps()

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Array) and self.e == other.e


class Option(TypeBase):
    def __init__(self, o):
        self.o = o

    def s(self):
        return '({} option)'.format(self.o.s())

    def to_json(self, f):
        if f:
            return '(Option.toJson ({},{}))'.format(self.o.to_json(False), f)
        else:
            assert False

    def deps(self):
        return self.o.deps()

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Option) and self.o==other.o


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


def lookup(name, converted, o):
    if '$ref' in o:
        n = deref(o['$ref'])
        if n.s() in converted.keys():
            return converted[n.s()]
        else:
            print('ERROR: {} not found in converted'.format(n.s()))
            assert False
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


def obj_list_intersection(name, converted, objs):
    olist = [lookup(name, converted, o) for o in objs]

    out = {'properties':{}, 'deps':set()}
    for o in olist:
        out['properties'] = intersect(out, o)

    for n,t in out['properties'].items():
        out['deps'] = out['deps'].union(t.deps())

    return out


def i_print(s):
    global indent

    idnt = ''
    for _i in range(indent):
        idnt = ' ' + idnt

    s = s.replace('\n', '\n'+idnt)
    s = idnt + s

    print(s)

def is_basic(name, descr):
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
        e = is_basic(name, descr['items'])
        if e:
            return Array(e)
        else:
            return False
    elif t=='object' and 'properties' in descr:
        return Record(convert_obj(name, descr))
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
    basic_descr = is_basic(name, descr)
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

    deps = set()

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
            deps = deps.union(set(basic_descr.deps()))

    o['deps'] = deps

    return o


def convert_enum(name, obj):
    desc = obj.get('description','')
    o = {'name':name, 'description':desc, 'enum':Enum(obj['enum'])}
    return o


def print_obj(obj):
    global indent
    i_print('structure {} = struct'.format(obj.name))
    indent += 2
    i_print('(* {} *)'.format(obj.descr))

    i_print('type t = {')
    fields = []
    for prop_name,prop_type in obj.props.items():
        fields.append('{}: {}'.format(prop_name, prop_type.s()))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print('}')

    print()
    print()

    i_print('fun toJson (x : t) = Json.OBJECT [')
    fields = []
    for prop_name,prop_type in obj.props.items():
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

def create_converted(names):
    import copy
    unprocessed = copy.deepcopy(names)
    failed = []
    processed = {}

    while len(failed)!=0 or len(unprocessed)!=0:
        while len(unprocessed)!=0:
            current_name = unprocessed.pop()
            try:
                processed[current_name] = make(processed, current_name, dap_json['definitions'][current_name])
            except UnknownRefException as e:
                failed.append(current_name)

        unprocessed = failed
        failed = []

    return processed

header = '''

structure Json = JSON

fun id x = x

structure Option = struct
  fun toJson (f,v) = case v of
      NONE => Json.NULL
    | SOME v' => f v'
end

structure Int = struct
  type t = int
  
  fun toJson x = Json.INT (IntInf.fromInt x)
end

structure Real = struct
  type t = real
  
  fun toJson x = Json.FLOAT x
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

dep_graph = {}

converted = create_converted(list(dap_json['definitions'].keys()))

#print(list(order))
#exit(0)

i_print(header)
for name, schem in converted.items():
    if name in ignored_schems:
        continue
    if isinstance(schem, Enum):
        print_enum(schem)
    elif hasattr(schem, 'props'):
        print_obj(schem)
    else:
        continue
