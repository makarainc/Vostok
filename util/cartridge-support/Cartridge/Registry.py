#!/usr/bin/env python
# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/cartridge-support/Cartridge/Registry.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

# TODO
#
#   - implement change journaling so we can recover from catastrophic failure

import imp
import re
import new, types, copy_reg             # for pickling lambdas
import logging

log = logging.getLogger(__name__)

MAINTAINER = '_'                        # special cartridge maintainer token

REGISTRY_VERSION = '1.0'
PRINT_WIDTH = 76
PRINT_FORMAT = "%s%-14s%s\n"

NORMAL   = 1
ADVANCED = 2
EXPERT   = 3
LOCKED   = 4

# Formatters
_item_formatter  = None
_group_formatter = None
_scope_formatter = None


def hfill(string, pattern, width):
    return string + (pattern * (max(width - len(string), 0) / len(pattern)))


#
# Theory
# ------
# The options registry is a hierarchy of objects containing an options
# database and a tree of elements embodying the configuration:
#
#    registry      := options configuration
#    options       := option*
#    configuration := ELEMENT*
#
# Elements are either single items or groups or scopes of elements.  The
# difference between scopes and groups is that the former define namespaces,
# whereas groups don't.  As a result, equally qualified elements may exist
# in different scopes, but not within the same scope, even if they are
# members of different groups.
#
#    ELEMENT       := item | group | scope
#    group         := ( ELEMENT* )
#    scope         := ( ELEMENT* )
#
# Options use a number of slots that are used to describe their complete
# behavior, both functionally and logically (e.g. when displayed in a UI):
#
#    option        := CORE ANNOTATION DEPENDENCY META
#    CORE          := name syntax range default
#    ANNOTATION    := label description
#    DEPENDENCY    := requires conflicts
#    META          := level tags memo
#


# ----------------------------------------------------------------------------
#
#  Options DB
#

# TODO
#
# * support dependencies between option states of the form
#     
#     option[:state] [[AND|OR] ...] -> option[:state] [[AND|OR] ...]
# 
#   by expressing the dependent option base state as either enabled or
#   disabled, defining a logical partition of its value space as states, and
#   then addressing a set of states from the antecedent option.  the
#   antecedent option may also have its value space partitioned into states.
# 
#   = present target options/states as daughter options

_option_args = frozenset(['name', 'syntax', 'default', 'label', 'help',
                          'requires', 'conflicts',
                          'level', 'tags', 'memo'])

class Option (object):
    name      = None
    syntax    = None
    range     = None
    default   = None
    label     = None
    help      = None
    requires  = None                    # e.g. 'RewriteEngine == On'
    conflicts = None                    # e.g. 'ServerSignature' != <value>

    level     = None
    tags      = None
    memo      = None

    def __init__(self, locale, **args):
        keys = set(args.keys())

        if keys == _option_args:
            for k, v in args.iteritems():
                if k in ('label', 'help') and isinstance(v, basestring):
                    v = {locale: v}
                setattr(self, k, v)
        else:
            raise ValueError \
                  ("Invalid record:\n  " + \
                   "\n  ".join(map(lambda x: "%-10s: %s" % (x[0], str(x[1])),
                                   args.items())))

    # NOTE: ignore warnings re 'self' being unused; it is used in 'eval' below
    def to_string(self, indent = 0):
        s = ''

        for slot in ('name', 'syntax', 'range', 'default', 'label', 'help',
                     'requires', 'conflicts',
                     'level', 'tags', 'memo'):
            s += PRINT_FORMAT % \
                 ('  ' * indent, slot + ':', str(eval('self.' + slot)))
        s += '  ' * indent + "---\n"

        return s
    
    def __str__(self):
        return self.to_string()


class Options (object):
    __options = None

    def __init__(self):
        self.__options = []
        
    def to_string(self, indent = 0):
        s = hfill('Options ', '-', PRINT_WIDTH) + "\n"

        for o in self.__options:
            s += o.to_string(indent + 1)

        return s
    
    def __str__(self):
        return self.to_string()

    def filter_by_locale(self, locale, default_locale):
        for o in self.__options:
            if o.label:
                if locale in o.label:
                    o.label = o.label[locale]
                else:
                    o.label = o.label[default_locale]
            if o.help:
                if locale in o.help:
                    o.help = o.help[locale]
                else:
                    o.help = o.help[default_locale]

    def filter_by_level(self, level):
        self.__options = filter(lambda x: x.level <= level, self.__options)
            
    def find_by_name(self, name):
        for o in self.__options:
            if name == o.name:
                return o

        return None

    def add(self, option):
        self.__options.append(option)


# ----------------------------------------------------------------------------
#
#  Configuration
#

class ConfigurationError (ValueError):
    pass

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Abstract Classes

class ElementMixin (object):
    __new       = False
    __parent    = None
    __owner     = None
    __key       = None
    __values    = None
    
    def __init__(self, key, *values):
        self.__key = key
        self.__values = values
        
    def new(self, new = None):
        if isinstance(new, bool):
            self.__new = new
        
        return self.__new

    def parent(self, container = None):
        if container != None:
            self.__parent = container

        return self.__parent
    
    def owner(self, owner = None):
        if owner != None:
            self.__owner = owner
        
        return self.__owner

    def key(self):
        return self.__key

    def values(self):
        return self.__values


class SetMixin (object):
    __children = None

    def __init__(self):
        self.__children = []
        
    def children(self, children = None):
        if children != None:
            self.__children = children
        
        return self.__children


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Concrete Classes

class Item (ElementMixin):
    def to_string(self, indent = 0):
        return "%s%-24s%s\n" % \
               ('  ' * indent, \
                self.owner() + '.' + self.key() + ':', self.values())
    
    def __str__(self):
        return self.to_string()

    def _write(self, selector, indent = 0):
        if selector.match(self.owner()):
            if callable(_item_formatter):
                return _item_formatter(indent, self.key(), self.values())
            else:
                return self.to_string(indent)


class Container (ElementMixin, SetMixin):
    def __init__(self, key, *values):
        ElementMixin.__init__(self, key, *values)
        SetMixin.__init__(self)
    
    # Output
    def to_string_aux(self, type, indent = 0):
        s = '%s%s: %s.%s %s ' % \
            ('  ' * indent, type, self.owner(), self.key(), str(self.values()))

        s = hfill(s, '- ', PRINT_WIDTH) + "\n"
        for ch in self.children():
            s += ch.to_string(indent + 1)
        s += hfill('  ' * indent, '- ', PRINT_WIDTH) + "\n"
        
        return s

    def _write(self, selector, indent = 0):
        s = ''
        
        for ch in self.children():
            s += ch._write(selector, indent)
        
        return s

    # Tree Construction
    def add_scope(self, scope):
        # Note: Scope conflict detection is hard (think Apache 'Directory'
        # regexp resolution), so we won't even try.
        self.children().append(scope)
        
        return True
     
    def add_group(self, group):
        self.children().append(group)

        return True
    
    def add_item(self, item):
        self.children().append(item)

        return True

    # Tree Filtering
    def remove_by_owner(self, owner):
        changed = False
        l = []

        for c in self.children():
            if c.owner() == owner:
                changed = True
            else:
                if isinstance(c, Container):
                    if c.remove_by_owner(owner):
                        changed = True
                    l.append(c)
                else:
                    l.append(c)
        self.children(l)

        return changed
                
    def filter_by_db(self, options_db):
        l = []

        # Note: empty nodes are perfectly OK
        for c in self.children():
            if isinstance(c, Group):
                # groups are purely cosmetic and thus not recorded in db
                l.append(c.filter_by_db(options_db))
            else:
                if options_db.find_by_name(c.key()):
                    if isinstance(c, Container):
                        l.append(c.filter_by_db(options_db))
                    else:
                        l.append(c)
        self.children(l)

        return self

    # Tree Walk
    def walk(self, function):
        for c in self.children():
            function(c)
            if isinstance(c, Container):
                c.walk(function)


class Group (Container):
    def to_string(self, indent = 0):
        return Container.to_string_aux(self, 'Group', indent)
    
    def __str__(self):
        return self.to_string()

    # def _write_content(self, indent):
    #     return Container._write(self, indent)
    
    def _write(self, selector, indent = 0):
        if selector.match(self.owner()):
            if callable(_group_formatter):
                return _group_formatter(indent,
                                        self.key(),
                                        self.values(),
                                        lambda ind: Container._write(self,
                                                                     selector,
                                                                     ind)
                                        # self._write_content
                                        )
            else:
                return self.to_string(indent)


class Scope (Container):
    def to_string(self, indent = 0):
        return Container.to_string_aux(self, 'Scope', indent)
    
    def __str__(self):
        return self.to_string()

    # def _write_content(self, indent):
    #     return Container._write(self, indent)
    
    def _write(self, selector, indent):
        if selector.match(self.owner()):
            if callable(_scope_formatter):
                return _scope_formatter(indent,
                                        self.key(),
                                        self.values(),
                                        lambda ind: Container._write(self,
                                                                     selector,
                                                                     ind)
                                        # self._write_content
                                        )
            else:
                return self.to_string(indent)


# WARNING: Tree construction methods are not reentrant!
#
# In order to keep the intermediate settings data format as simple as
# possible, 'Configuration' keeps state in '__current_node' during tree
# construction.  Since construction always goes through
# 'Registry.install_settings()', though, we can call 'reinit()' there and
# will be safe as long as we're not multithreaded.

class Configuration (object):
    __root          = None
    __current_node  = None
    __options_db    = None

    # Housekeeping
    def __init__(self, options_db):
        self.__root         = Container('<root>')
        self.__current_node = self.__root
        self.__options_db   = options_db
        
        self.__root.owner('')

    def reinit(self):
        self.__current_node = self.__root

    # Output
    def to_string(self, indent = 0):
        s = hfill('Configuration ', '-', PRINT_WIDTH) + "\n"

        for el in self.__root.children():
            s += el.to_string(indent)

        return s
    
    def __str__(self):
        return self.to_string()

    def write(self, owner = None, private = False, indent = 0):
        p = None
        s = ''

        if owner:
            if private:
                p = re.compile('^' + owner + '$')
            else:
                p = re.compile('^(?:' + MAINTAINER + '|' + owner + ')$')
        else:
            p = re.compile('.')
        
        for el in self.__root.children():
            r = el._write(p, indent)
            if r:
                s += r

        return s
    
    # Tree Construction
    def _begin_aux(self, node, adder):
        scope = False
        o     = None
        
        if isinstance(node, Scope):
            scope = True
            o     = self.__options_db.find_by_name(node.key())

        node.parent(self.__current_node)
        node.new(True)

        # drop unsupported scopes unless owned by maintainer
        if scope and o == None and not node.owner() == MAINTAINER:
            # FIXME collect and raise on exit from install?
            self.__current_node = node
        else:
            res = adder(self.__current_node, node)

            if res is True:
                self.__current_node = node
            else:
                raise ConfigurationError(res)

    def begin(self, object):
        if isinstance(object, Scope):
            self._begin_aux(object, Container.add_scope)
        elif isinstance(object, Group):
            self._begin_aux(object, Container.add_group)
        else:
            raise TypeError ("Not a scope or group: '%s'" % type(object))

    def end(self):
        self.__current_node = self.__current_node.parent()

    def add(self, item):
        log.debug("Adding item: %s" % str(item))
        if isinstance(item, Item):
            o = self.__options_db.find_by_name(item.key())

            # drop unsupported items unless owned by maintainer
            if o == None and not item.owner() == MAINTAINER:
                # FIXME collect and raise on exit from install?
                pass
            else:
                res = None
                
                item.parent(self.__current_node)
                item.new(True)
                
                res = Container.add_item(self.__current_node, item)
                if res is True:
                    pass
                else:
                    raise ConfigurationError(res)
        else:
            raise TypeError ("Not an item: '%s'" % type(item))

    # Tree Filtering
    def remove_by_owner(self, owner):
        return self.__root.remove_by_owner(owner)

    def filter_by_db(self, options_db):
        self.__options_db = options_db
        self.__root.filter_by_db(options_db)

    # Tree Walk
    def walk(self, function):
        self.__root.walk(function)

    # Consistency Checks
    #def satisfy(self, requirement):
    #    # FIXME implement; satisfy in current or any parent scope
    #    return True
    #
    #def detect(self, conflict):
    #    # FIXME implement; detect in current scope only
    #    return False

    def check(self,
              old_requires = False,
              old_conflicts = False,
              new_requires = False,
              new_conflicts = False):
        errors = []
        
        if old_requires:
            # FIXME implement
            # for el in tree
            #   find el in options
            #   determine applicable requirements
            #   for r in requirements
            #     for el2 in tree
            #       if el2 satisfies r
            #         break
            #     push "el requires r" on errors
            pass
        if old_conflicts:
            # FIXME implement
            pass
        if new_requires:
            # FIXME implement
            pass
        if new_conflicts:
            # FIXME implement
            pass

        if errors:
            raise ConfigurationError("Error:\n  " + "\n  ".join(errors))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class Registry (object):
    __version        = REGISTRY_VERSION
    __default_locale = None
    __locale         = None
    __level          = None
    __options        = None
    __configuration  = None

    # Private
    def __init__(self, default_locale):
        self.__default_locale = default_locale
        self.__options        = Options()
        self.__configuration  = Configuration(self.__options)

    def _install_settings_aux(self, owner, settings):
        # Note: we flatten sublists unless their first element is a Container
        if len(settings) > 0:
            container = False

            if isinstance(settings[0], ElementMixin):
                settings[0].owner(owner)
                if isinstance(settings[0], Container):
                    self.__configuration.begin(settings[0])
                    container = True
                else:
                    self.__configuration.add(settings[0])
            elif isinstance(settings[0], list):
                self._install_settings_aux(owner, settings[0])
            else:
                raise ValueError("Invalid element: '%s'" % settings[0])
            
            for el in settings[1:]:
                if isinstance(el, list):
                    self._install_settings_aux(owner, el)
                elif isinstance(el, ElementMixin):
                    el.owner(owner)
                    self.__configuration.add(el)
                else:
                    raise TypeError ("Bad structure: '%s'" % settings)

            if container:
                self.__configuration.end()

    def _install_settings(self, owner, settings):
        self.__configuration.reinit()
        self._install_settings_aux(owner, settings)
    
    def _uninstall_settings(self, owner):
        return self.__configuration.remove_by_owner(owner)

    # Output
    def to_string(self):
        s = hfill('Registry v%s ' % self.__version, '=', PRINT_WIDTH) + "\n"
        
        s += self.__options.to_string()
        s += self.__configuration.to_string()
        s += hfill('', '=', PRINT_WIDTH) + "\n"
        
        return s
    
    def __str__(self):
        return self.to_string()

    def write_configuration(self, owner = None, private = False):
        return self.__configuration.write(owner, private)

    # API
    def version(self):
        return self.__version

    def default_locale(self):
        return self.__default_locale

    def options(self):
        return self.__options

    def configuration(self):
        return self.__configuration

    def select_locale(self, locale):
        self.__options.filter_by_locale(locale, self.__default_locale)
        self.__locale = locale

    # you can't select "LOCKED"
    def select_level(self, level):
        if level in (NORMAL, ADVANCED, EXPERT):
            self.__options.filter_by_level(level)
            self.__configuration.filter_by_db(self.__options)
            self.__level = level
        else:
            raise ValueError \
                  ("Invalid level: '%s' (must be one of '%d', '%d', or '%d')" \
                   % (level, NORMAL, ADVANCED, EXPERT))

    @staticmethod
    def load_module(name, location):
        f, p, d = imp.find_module(name, [location])

        try:
            module = imp.load_module(name, f, p, d)
        finally:
            if f:
                f.close()

        return module

    def update_settings(self, owner, settings):
        changed = False
        
        if settings:
            changed = self._uninstall_settings(owner)
            self._install_settings(owner, settings)

            # FIXME: cartridges are either multitenant or multihomed.
            #        Since multitenant cartridges produce one monolithic
            #        configuration, they require that no two client's
            #        settings conflict with each other. Multihomed
            #        cartridges on the other hand produce one configuration
            #        per client and thus only require that client settings
            #        don't conflict with the cartridge base
            #        configuration. The checks below (once implemented) must
            #        take these two classes of cartridges into account.

            # install marked settings elements as 'new'
            self.__configuration.check(old_requires  = changed,
                                       old_conflicts = True,
                                       new_requires  = True,
                                       new_conflicts = True)
            # past exception == check OK; unmark elements again
            self.__configuration.walk(lambda el: el.new(False))
        else:
            changed = self._uninstall_settings(owner)
            if changed:
                self.__configuration.check(old_requires  = True)

    # Maintainer Reset
    def reset_options(self, options):
        self.__options  = Options()

        for rec in options:
            o = Option(self.__default_locale, **rec)

            if not self.__options.find_by_name(o.name):
                self.__options.add(o)

    def reset_configuration(self, settings):
        self.__configuration  = Configuration(self.__options)

        self._install_settings(MAINTAINER, settings)
    

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# Options DB Syntax
#
# Every item in the options db is a dictionary with the following set of
# keys, which are intended for either (I)nternal or (E)xternal use:
#
# Field Name  I E  Description
# ----------------------------------------------------------------------------
#   name      I E  Name of option
#   syntax      E  Parameter syntax.  For every parameter, an object specifies
#                    - the parameter type (e.g. BOOLEAN, STRING, etc.)
#                    - range control data (e.g. min/max value, if any)
#                    - a validate method to be used by UIs
#   default   I    Default provided by cartridge
#   label       E  Short label for option
#   help        E  More extensive help (HTML)
#   requires  I E  Options' prerequisites (not yet implemented)
#   conflicts I E  Options' prohibitions (not yet implemented)
#   level       E  Options' level (normal, advanced, expert)
#   tags      I    Array of tags (annotations)
#   memo      I    Memo
#
# Notes:
#    - syntax is a list of objects, one per parameter.  As a shorthand, a
#      single object is equivalent to the single-element list [object].
#    - label and help are dictionaries of the form locale : string.  As a
#      shorthand, a single string is equivalent to the dictionary
#      {default-locale : string}
#    - requires and conflicts are always tuples
#    - tags is a tuple of strings
#    - memo is either None or a string
#
# Syntax objects may be either operators or types.  Currently, the only
# operator is OR, whith OR.operands holding the operands.
#
# Validators are to be called by the UI with the character string to validate 
# stripped of whitespace on both ends.

#
# Base Operators

class _operator (object):
    operands = None
    

class OR (_operator):
    def __init__(self, *args):
        self.operands = args


#
# Base Option Types

# We need to add support pickling of functions to Python so Cartridge
# authors can use lambda forms as validators as in
#
#   STRING(validator = lambda self, val: set(val) <= set('abcd'))
#
# Note the required use of 'self' in lambda expressions.
#
# This appears to work, but see also section "Pickling customization with
# the copy_reg module" on p.283f of Martelli: "Python in a Nutshell", 2nd
# Ed., O'Reilly, 2006 for an example of an alternative approach by
# delegating function pickling to marshal, reproduced below.
# 
#   import pickle, copy_reg, marshal
#   
#   def viaMarshal(x): return marshal.loads, (marshal.dumps(x),)
#   
#   c = compile('2+2', '', 'eval')
#   copy_reg.pickle(type(c), viaMarshal)
#   s = pickle.dumps(c, 2)
#   cc = pickle.loads(s)
#   
#   print eval(cc)

def thaw_lambda(*args):
    c = new.code(*args)

    return new.function(c, globals())

def freeze_lambda(f):
    c = f.func_code
    
    return thaw_lambda, (c.co_argcount, c.co_nlocals, c.co_stacksize,
                         c.co_flags, c.co_code, c.co_consts, c.co_names,
                         c.co_varnames, c.co_filename, c.co_name,
                         c.co_firstlineno, c.co_lnotab)

copy_reg.pickle(types.FunctionType, freeze_lambda)

class option_type (object):
    pattern     = None                  # free-form pattern
    token       = None                  # token pattern
    separator   = None                  # separator (if list)
    list_min    = None                  # minimum list length
    list_max    = None                  # maximum list length
    match_flags = 0                     # flags to re.match

    validator   = None                  # free-form validator callable
    
    def __init__(self, **args):
        self._set_slots(args)

    def _set_slots(self, d):
        for n, v in d.iteritems():
            if v is not None:
                setattr(self, n, v)

    def validate(self, value):
        if callable(self.validator):
            return self.validator(value)
        else:
            pat = None
            
            if self.pattern:
                pat = self.pattern
            elif self.token:
                if self.separator:
                    # pattern to construct based on list_min and list_max
                    #
                    #   lb  ub                fr  to
                    #   --------------------------------
                    #   0 - 0          ''                  ; special case
                    #   0 - 1          (t(st){0  ,u-1})?   ; add ()?
                    #   0 - n          (t(st){0  ,u-1})?
                    #   0 -            (t(st){0  ,   })?
                    #   1 - 1           t(st){l-1,u-1}     ; standard
                    #   1 - n           t(st){l-1,u-1}
                    #   1 -             t(st){l-1,   }
                    #   m - m           t(st){l-1,u-1}
                    #   m - n           t(st){l-1,u-1}
                    lb = self.list_min or 0
                    ub = self.list_max
                    fr = max(lb - 1, 0)
                    to = None

                    if ub is None:
                        to = ''
                    else:
                        if ub < lb: ub = lb
                        to = max(ub - 1, 0)

                    if ub is not None and ub == 0:
                        pat = ''
                    else:
                        pat = self.token + \
                              '(?:' + self.separator + self.token + ')' + \
                              '{' + str(fr) + ',' + str(to) + '}'
                        if lb == 0:
                            pat = '(?:' + pat + ')?'
                else:
                    pat = '(?:' + self.token + ')?'

            if pat:
                pat = '^' + pat + '$'
                print "--", pat
                return re.match(pat, value, self.match_flags) and True
            else:
                # nothing to validate against.  this is a package error we
                # can't fix in general anyway and at this time in particular
                return True

        
class BOOLEAN (option_type):
    labels = None
    validator = lambda self, v: v in self.labels

    def __init__(self, labels = ('0', '1', 'Off', 'On',
                                 'No', 'Yes', 'False', 'True')):
        self.labels = labels
    

class INTEGER (option_type):
    min   = None
    max   = None
    validator = lambda self, v: \
                    v.isdigit() and \
                    (not self.min or self.min <= int(v)) and \
                    (not self.max or int(v) <= self.max)

    def __init__(self, min = None, max = None):
        self.min = min
        self.max = max

class STRING (option_type):
    max   = None
    validator = lambda self, v: True

class OPTIONS (option_type):
    items         = None
    selection_min = None
    selection_max = None
    # implemented by __validator function for readability
    validator     = lambda self, csl: self.__validator(csl)

    def __validator(self, csl):         # comma-separated list
        # Note that an empty 'csl' is ambiguous.  If '' is an option, it is
        # treated as a selection, otherwise as "no selection"
        if csl == '':
            n = csl in self.items and 1 or 0

            return (self.selection_min is None or self.selection_min <= n)and \
                   (self.selection_max is None or self.selection_max >= n)
        else:
            v = frozenset(re.split(r'\s*,\s*', csl))
            n = len(v)

            return (self.selection_min is None or self.selection_min <= n)and \
                   (self.selection_max is None or self.selection_max >= n)and \
                   v <= frozenset(self.items)
    
    def __init__(self, items, selection_min = None, selection_max = None):
        self.items = items
        self.selection_min = selection_min
        self.selection_max = selection_max


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Format Helpers

# Options

name      = 'name'
syntax    = 'syntax'
default   = 'default'
label     = 'label'
help      = 'help'
requires  = 'requires'
conflicts = 'conflicts'
level     = 'level'
tags      = 'tags'
memo      = 'memo'


# Settings
#
# Note: Double quotes in RHS arguments must be doubly backslashed.

def _container_aux(cls, args, *content):
    l = []
    
    if isinstance(args, basestring):
        l.append(cls(args))
    else:
        l.append(cls(args[0], *args[1:]))
    if len(content) > 0:
        l += list(content)
    return l
    
def scope(args, *content):
    return _container_aux(Scope, args, *content)

def group(args, *content):
    return _container_aux(Group, args, *content)

def item (key, *values):
    return Item(key, *values)


#
# EOF
