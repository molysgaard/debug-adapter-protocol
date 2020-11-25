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
    if 'enum' in schem or '_enum' in schem:
        return Enum(name, schem)
    elif isinstance(t,list) and set(t) == {'integer','string'}:
        return IntOrString(schem)
    elif isinstance(t, list) and set(t) == {'null', 'string'}:
        return NullableString(schem)
    elif isinstance(t, list) and set(t) == {'array', 'boolean', 'integer', 'null', 'number', 'object', 'string'}:
        return JsonObject(schem)
    else:
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
        else:
            assert False

class TypeBase(object):
    def __init__(self, schem):
        if schem!=False:
            self.descr = schem.get('description', '')

    def deps(self):
        return set()

    def union(self, other):
        if self == other:
            return self
        else:
            raise UnionException(self, other)


class Enum(TypeBase):
    def __init__(self, *args):
        super().__init__(False)
        if len(args)==2:
            self.init_from_json(*args)
        elif len(args)==3:
            self.init_from_values(*args)
        else:
            assert False, 'Enum with wrong number of arguments'

    def init_from_values(self, name, descr, values):
        self.name = name
        self.descr = descr
        self.values = values

    def init_from_json(self, name, schem):
        self.name = name
        self.descr = schem.get('description', '')
        self.values = schem.get('enum', schem.get('_enum'))

    def s(self, n):
        return 'string'

    def to_json(self, n, f):
        if len(self.values)==1:
            return '(String.toJson "{}")'.format(next(iter(self.values)))
        else:
            if f:
                return '(String.toJson {})'.format(f)
            else:
                return 'String.toJson'
    
    def from_json(self, n, f):
        if f:
            return '(JSONUtil.asString {})'.format(f)
        else:
            return 'JSONUtil.asString'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Enum) and self.values==other.values

    def union(self, other):
        if isinstance(other, Enum):
            valid_values = set(self.values).intersection(other.values)
            if len(valid_values)!=0:
                return Enum(self.name, self.descr, valid_values)
            else:
                assert False, 'empty valid values set for Enum'
        elif isinstance(other, String):
            return self


class RefObj(TypeBase):
    def __init__(self, name, schem):
        super().__init__(schem)
        self.name = name
        self.descr = schem.get('description', '')
        self.ref = schem['$ref']

    def s(self, n):
        if n==self.parse_name():
            return 't'
        else:
            return self.parse_name()+'.t'

    def to_json(self, n, f):
        if n==self.parse_name():
            if f:
                return '(toJson {})'.format(f)
            else:
                return 'toJson'
        else:
            if f:
                return '({}.toJson {})'.format(self.parse_name(), f)
            else:
                return '{}.toJson'.format(self.parse_name())
    
    def from_json(self, n, f):
        if n==self.parse_name():
            if f:
                return '(fromJson {})'.format(f)
            else:
                return 'fromJson'
        else:
            if f:
                return '({}.fromJson {})'.format(self.parse_name(), f)
            else:
                return '{}.fromJson'.format(self.parse_name())

    def parse_name(self):
        prefix = '#/definitions/'
        assert self.ref.startswith(prefix)
        return self.ref[len(prefix):]

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Enum) and self.values==other.values

    def deps(self):
        return {self.parse_name()}

    def union(self, other):
        assert False, 'Union called for RefObj which should never happen'

class Record(TypeBase):
    def __init__(self, *args):
        super().__init__(False)
        if isinstance(args[0], str):
            self.init_from_internal(*args)
        else:
            self.init_from_json(*args)

    def init_from_internal(self, name, descr, props):
        self.name=name
        self.descr=descr
        self.props=props
        deps = set()
        for p in self.props.values():
            deps = deps.union(p.deps())
        self.ddeps = deps

    def init_from_json(self, converted, name, obj):
        self.name = name
        self.descr = obj.get('description','')
        self.props = {}
        self.ddeps = set()

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

        deps = set()
        if props:
            for prop_name, prop_descr in obj['properties'].items():
                #basic_descr = get_prop_type(opt_props, prop_name, prop_descr)
                basic_descr = make(converted, prop_name, prop_descr)
                self.props[prop_name] = basic_descr
                deps = deps.union(basic_descr.deps())

        self.ddeps = deps

    def s(self, n):
        tmp = []
        for k,v in self.props.items():
            assert hasattr(v,'s')
            tmp.append('  {}: {}'.format(k,v.s(n)))
        fields = ',\n'.join(tmp)
        return '{{\n{}\n}}'.format(fields)

    def to_json(self, n, f):
        if f:
            fields = []
            for k,v in self.props.items():
                fields.append('("{}", {})'.format(k, v.to_json(n, '(#{} {})'.format(k, f))))
            return '(Json.OBJECT [{}])'.format(', '.join(fields))
        else:
            return 'id'

    def from_json(self, n, f):
        if f:
            fields = []
            for k,v in self.props.items():
                fields.append('{}={}'.format(k, v.from_json(n, '(JSONUtil.lookupField {} "{}")'.format(f, k))))
            return '{{ {} }}'.format(', '.join(fields))
        else:
            return 'id'

    def deps(self):
        return self.ddeps

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
        super().__init__(schem)

    def s(self, n):
        return 'int'

    def to_json(self, n, f):
        if f:
            return '(Int.toJson {})'.format(f)
        else:
            return 'Int.toJson'
    
    def from_json(self, n, f):
        if f:
            return '(JSONUtil.asInt {})'.format(f)
        else:
            return 'JSONUtil.asInt'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Integer)


class Real(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'real'

    def to_json(self, n, f):
        if f:
            return '(Real.toJson {})'.format(f)
        else:
            return 'Real.toJson'
    
    def from_json(self, n, f):
        if f:
            return '(JSONUtil.asNumber {})'.format(f)
        else:
            return 'JSONUtil.asNumber'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Real)


class Boolean(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'bool'

    def to_json(self, n, f):
        if f:
            return '(Bool.toJson {})'.format(f)
        else:
            return 'Bool.toJson'
    
    def from_json(self, n, f):
        if f:
            return '(JSONUtil.asBool {})'.format(f)
        else:
            return 'JSONUtil.asBool'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Boolean)


class String(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'string'

    def to_json(self, n, f):
        if f:
            return '(String.toJson {})'.format(f)
        else:
            return 'String.toJson'
    
    def from_json(self, n, f):
        if f:
            return '(JSONUtil.asString {})'.format(f)
        else:
            return 'JSONUtil.asString'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, String)

    def union(self, other):
        if isinstance(other, Enum):
            return other
        else:
            return super().union(other)


class IntOrString(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'IntOrString.t'

    def to_json(self, n, f):
        if f:
            return '(IntOrString.toJson {})'.format(f)
        else:
            return 'IntOrString.toJson'

    def from_json(self, n, f):
        if f:
            return '(IntOrString.fromJson {})'.format(f)
        else:
            return 'IntOrString.fromJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, IntOrString)


class NullableString(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'NullableString.t'

    def to_json(self, n, f):
        if f:
            return '(NullableString.toJson {})'.format(f)
        else:
            return 'NullableString.toJson'

    def from_json(self, n, f):
        if f:
            return '(NullableString.fromJson {})'.format(f)
        else:
            return 'NullableString.fromJson'

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, NullableString)


class StringMap(TypeBase):
    def __init__(self, e):
        super().__init__(False)
        self.e = e

    def s(self, n):
        return '({} StringMap.map)'.format(self.e.s(n))

    def to_json(self, n, f):
        if f:
            return '(StringMap.toJson {} {})'.format(self.e.to_json(n,False), f)
        else:
            return '(StringMap.toJson {})'.format(self.e.to_json(n,False))

    def from_json(self, n, f):
        if f:
            return '(StringMap.fromJson {} {})'.format(self.e.from_json(n,False), f)
        else:
            return '(StringMap.fromJson {})'.format(self.e.from_json(n,False))

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, StringMap)

    def deps(self):
        return self.e.deps()


class JsonObject(TypeBase):
    def __init__(self, schem):
        super().__init__(schem)

    def s(self, n):
        return 'Json.value'

    def to_json(self, n, f):
        if f:
            return f
        else:
            return 'id'

    def from_json(self, n, f):
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
        super().__init__(False)
        self.e = e

    def s(self, n):
        return '({} list)'.format(self.e.s(n))

    def to_json(self, n, f):
        if f:
            return '(Json.ARRAY (List.map {} {}))'.format(self.e.to_json(n, False), f)
        else:
            assert False, 'List.to_json without field'

    def from_json(self, n, f):
        if f:
            return '(List.map {} (vectorToList (JSONUtil.asArray {})))'.format(self.e.from_json(n, False), f)
        else:
            assert False, 'List.from_json without field'

    def deps(self):
        return self.e.deps()

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other, Array) and self.e == other.e


class Option(TypeBase):
    def __init__(self, o):
        super().__init__(False)
        self.o = o

    def s(self, n):
        return '({} option)'.format(self.o.s(n))

    def to_json(self, n, f):
        if f:
            return '(Option.toJson ({},{}))'.format(self.o.to_json(n, False), f)
        else:
            assert False

    def from_json(self, n, f):
        if f:
            return '(Option.fromJson ({},{}))'.format(self.o.to_json(n, False), f)
        else:
            assert False

    def deps(self):
        return self.o.deps()

    def __str__(self):
        return self.s()

    def __eq__(self, other):
        return isinstance(other,Option) and self.o==other.o


def i_print(s):
    global indent

    idnt = ''
    for _i in range(indent):
        idnt = ' ' + idnt

    s = s.replace('\n', '\n'+idnt)
    s = idnt + s

    print(s)

def print_obj(obj):
    global indent
    i_print('structure {} = struct'.format(obj.name))
    indent += 2
    i_print('(* {} *)'.format(obj.descr))

    i_print('datatype t = T of {')
    fields = []
    for prop_name,prop_type in obj.props.items():
        fields.append('{}: {}'.format(prop_name, prop_type.s(obj.name)))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print('}')

    print()
    print()

    i_print('fun toJson ((T x) : t) = Json.OBJECT [')
    fields = []
    for prop_name,prop_type in obj.props.items():
        fields.append('("{}", {})'.format(field_name_to_prop.get(prop_name,prop_name), prop_type.to_json(obj.name, '(#{} x)'.format(prop_name))))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print(']')

    i_print('fun fromJson (x : Json.value) : t = T {')
    fields = []
    for prop_name,prop_type in obj.props.items():
        fn = field_name_to_prop.get(prop_name,prop_name)
        fields.append('{}={}'.format(prop_name, prop_type.from_json(obj.name, '(JSONUtil.lookupField x "{}")'.format(fn))))
    indent += 2
    i_print(',\n'.join(fields))
    indent -= 2
    i_print('}')

    indent -= 2
    i_print('end\n')


def print_enum(obj):
    global indent
    i_print('structure {} = struct'.format(obj.name))
    indent += 2
    i_print('(* {} *)'.format(obj.descr))

    tmp = 'datatype t = ' + ' | '.join(obj.values)

    i_print(tmp)

    print()
    print()

    i_print('fun toJson x = case x of')
    indent += 2
    first = True
    for e in obj.values:
        if first:
            first = False
            i_print('  {} => String.toJson "{}"'.format(e, e))
        else:
            i_print('| {} => String.toJson "{}"'.format(e, e))
    indent -= 2

    i_print('fun fromJson x = case JSONUtil.asString x of')
    indent += 2
    first = True
    for e in obj.values:
        if first:
            first = False
            i_print('  "{}" => {}'.format(e, e))
        else:
            i_print('| "{}" => {}'.format(e, e))
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

fun vectorToList vec = Vector.foldr (op ::) [] vec

structure Option = struct
  fun toJson (f,v) = case v of
      NONE => Json.NULL
    | SOME v' => f v'

  fun fromJson (f,v) = case v of
      Json.NULL => NONE
    | _ => f v
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

  fun fromJson x = case x of
      Json.NULL => NONE
    | x => SOME (JSONUtil.asString x)
end

structure IntOrString = struct
  datatype t = IsInt of int | IsString of string
  
  fun toJson x = case x of
      IsInt i => Int.toJson i
    | IsString s => String.toJson s

  fun fromJson x = (IsInt (JSONUtil.asInt x))
        handle JSONUtil.NotInt a => (IsString (JSONUtil.asString x))
end

structure StringMap = struct
    open StringMap

    fun toJson f x = Json.OBJECT (List.map (fn (k,v) => (k,f v)) (list x))

    fun fromJson f x = case x of
        Json.OBJECT ls => StringMap.fromList (List.map (fn (k,v) => (k,f v)) ls)
end
'''

converted = create_converted(list(dap_json['definitions'].keys()))
dep_graph = {}
for name, obj in converted.items():
    dep_graph[name] = obj.deps()

#for n,deps in dep_graph.items():
#    print(n, deps)
#exit(0)

dep_ord_names = []
for name_group in toposort.toposort(dep_graph):
    dep_ord_names += list(name_group)

msgs = {'requests':{}, 'events':{}}

for name, schem in converted.items():
    if hasattr(schem, 'props'):
        t = schem.props.get('type_', None)
        if isinstance(t, Enum) and t.values == {'request'}:
            assert name.endswith('Request')
            name = name[0:-len('Request')]
            if name=='':
                continue
            if name in msgs['requests']:
                msgs['requests'][name]['req'] = schem
            else:
                msgs['requests'][name] = {'req':schem}
        if isinstance(t, Enum) and t.values == {'response'}:
            assert name.endswith('Response')
            name = name[0:-len('Response')]
            if name=='':
                continue
            if name in msgs['requests']:
                msgs['requests'][name]['resp'] = schem
            else:
                msgs['requests'][name] = {'resp':schem}

#print(msgs)
#exit(0)

def upper_first(s):
    return s[0].upper() + s[1:]

def lower_first(s):
    return s[0].lower() + s[1:]

def print_handle_sig(requests):
    sig_template = '''
signature HANDLERS = sig
{}
end
'''
    handlers_sig = ['    val handle{} : {}.t -> {}.t'.format(upper_first(name), upper_first(name)+'Request', upper_first(name)+'Response') for name in requests.keys()]
    handle_sig = '\n'.join(handlers_sig)
    i_print(sig_template.format(handle_sig))

def print_handler(requests):
    handleRequestTemplate ='''
functor DebugAdapterProtocol(structure Handlers : HANDLERS) :> sig val handleRequest : Json.value -> Json.value end = struct
    open Handlers
    fun handleRequest req = case JSONUtil.asString (JSONUtil.lookupField req "command") of
        {}
end
'''
    handlers = ['"{}" => {}.toJson (handle{} ({}.fromJson req))'.format(lower_first(name), upper_first(name)+'Response', upper_first(name), upper_first(name)+'Request') for name in requests.keys()]
    handle = '\n      | '.join(handlers)

    i_print(handleRequestTemplate.format(handle))
    
    #handlerTemplate = '''
    #fun handleProtocolMessage msg = case Json.lookup "type_" msg of
    #    "request" => handleRequest msg
    #  | "event"   => handleEvent msg
    #  | _ => print ("Unhandled protocolMessage: " ^ Json.toString msg)
    #'''

#print(dep_ord_names)
#exit(0)

i_print(header)
for name in dep_ord_names:
    schem = converted[name]
    if name in ignored_schems:
        continue
    if isinstance(schem, Enum):
        print_enum(schem)
    elif hasattr(schem, 'props'):
        print_obj(schem)
    elif isinstance(schem, JsonObject):
        i_print('structure {} = struct type t = Json.value fun toJson x = x fun fromJson x = x end'.format(name))
    else:
        assert False

print_handle_sig(msgs['requests'])
print_handler(msgs['requests'])