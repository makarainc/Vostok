# ===========================================================================
# Copyright 2010 Makara, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/DB.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import copy

from VPM.Constants import *
from VPM.Environment import Environment
from VPM.Lock import LockError, Lock
from VPM.Exceptions import *
from VPM.Utils import serialize, unserialize
from VPM.Structures import ProvidesInfo, DependencyTableInfo

# The DB class implements the package system's persistence layer.
#
# Format is simply the parsed version of all control files plus a few other
# bits of internal information. Example:
#
#  {package-name:
#      {# -- Control/Build File Fields ------------------------
#       'Name'           : <name>
#       'Version'        : <version>,
#       'Build'          : <internal build number>,
#       'Architecture'   :
#       'Provides'       : [{'Name'       : <pkg-name>,
#                            'Version'    : <version> | None,
#                            'String'     : <string repr>},
#                           ...],
#       'Depends'        : [[{'Name'       : <pkg-name>,
#                             'Predicate'  : <callable> | None,
#                             'String'     : <string repr>},
#                            ...],
#                           ...],
#       'Conflicts'      : <same as "Depends">,
#       'Description'    : '',
#       # -- Internal Fields ---------------------------------- 
#       'Quoted-Name'    : <filesystem-safe version of name>
#       'Quoted-Version' : <filesystem-safe version of version>
#       'Status'         : UNKNOWN | RESOLVED | REMOVED | PURGED | ...,
#       'Install-Prefix' : <install prefix (ins__p_)>,
#       'Install-Name'   : <install directory name (ins___n)},
#      ...
#  }
#
# Terminology:
# DB Entry: a package db entry
# Virtual Entry: db and dt entry for packages not yet installed. Used for scaffolding
#                by the Makara Console
# Virtual Feature (VF): special db and methods for virtual provides. 
#                e.g.: php => php-5.2.12
# Dependency Table (DT): special db and methods storing dependency information

class DBError (LookupError):
    pass

# Exception class for dependency/conflicts checking
    
class DB (object):
    '''
    Package Database
    '''
    __ACTION_ADD = 'a'
    __ACTION_REMOVE = 'r'

    __lock = None

    # Package States
    UNKNOWN = 'unknown'   # state for packages prior to installation
    IMPORTED = 'imported'
    VERIFIED = 'verified'
    COMMITTED = 'committed'
    RESOLVED = 'resolved'
    INSTALLED = RESOLVED
    REMOVED = 'removed'
    PURGED = 'purged'
    BROKEN = 'broken'

    INSTALLABLE = 'installable'

    REMOVABLE = frozenset([IMPORTED,
                           COMMITTED,
                           RESOLVED,
                           BROKEN])
    KNOWN = REMOVABLE

    STATES = frozenset([UNKNOWN,
                        IMPORTED,
                        VERIFIED,
                        COMMITTED,
                        RESOLVED,
                        REMOVED,
                        PURGED,
                        BROKEN])    
                   
    env = None

    def __init__(self, env):
        if not isinstance(env, Environment):
            raise ValueError("not Environment instance: '%s'" % env)
        self.env = env

        for d in (self.env.lock_dir, self.env.lib_dir, self.env.tmp_dir,
                  self.env.lib_package_dir, self.env.tmp_package_dir,
                  self.env.cartridge_dir, self.env.application_dir):
            if not os.path.exists(d):
                os.makedirs(d)

    def __del__(self):
        #object.__del__(self)

        if self.__lock:
            self.__lock.release()
    
    # Note: we can unify provides across the db and any application to
    # install, since we don't care about packages satisfying or conflicting
    # with themselves and thus don't ensure that a package's rule is not
    # checked against itself. If such rule sets made it into the db in the
    # first place they need to be treated as legitimate here.
    @staticmethod
    def _collect_provides(db, provides):
        for dummy, info in db.iteritems():
            provides += info.Provides

    # Returns a list of errors of form
    #
    #   errors := list(error*)
    #   error  := list(str(clause), list(str(close_match)+)?)

    @staticmethod
    def _chk_depends(depends, provides):
        errors = []

        if depends:
            for dclause in depends:
                close_matches = []
                err = None

                try:
                    for dexpr in dclause:
                        for pexpr in provides:
                            if dexpr.Name == pexpr.Name:
                                if dexpr.Predicate:
                                    if pexpr.Version:
                                        if eval(dexpr.Predicate)(pexpr.Version):
                                            raise DBError
                                        else:
                                            close_matches.append(pexpr.String)
                                            continue
                                    else:
                                        close_matches.append(pexpr.String)
                                        continue
                                else:
                                    raise DBError
                            else:
                                continue
                except DBError:
                    continue

                # no match found
                err = [' | '.join(map(lambda expr: expr.String, dclause))]
                if close_matches:
                    err.append(close_matches)
                errors.append(err)

        return errors

    # Returns a list of errors of form
    #
    #   errors := list(error*)
    #   error  := list(str(clause), list(str(match)+))
    @staticmethod
    def _chk_conflicts(conflicts, provides):
        errors = []

        if conflicts:
            for cclause in conflicts:
                matches = []

                for cexpr in cclause:
                    for pexpr in provides:
                        if cexpr.Name == pexpr.Name:
                            if cexpr.Predicate:
                                if pexpr.Version:
                                    if eval(cexpr.Predicate)(pexpr.Version):
                                        matches.append(pexpr.String)
                                    else:
                                        continue
                                else:
                                    matches.append(pexpr.String)
                                    continue
                            else:
                                matches.append(pexpr.String)
                        else:
                            continue

                if matches:
                    errors.append([' | '.join(map(lambda expr: expr.String,
                                                  cclause)), matches])

        return errors

    def _chk_remove(self, name, db):
        res = True
        errors = []

        if not name in db:
            errors = ["Package '%s' is not installed." % name]
        else:
            provides = []

            del db[name]
            self._collect_provides(db, provides)

            for dummy, info in db.iteritems():
                errs = self._chk_depends(info.Depends, provides)

                if errs:
                    res = False
                    errors.append({DB_KEY_NAME : info.Name,
                                   DB_KEY_VERS : info.Version,
                                   DB_KEY_BUIL : info.Build,
                                   DB_KEY_DEPS : errs})

        return res, errors or None

    def _chk_install(self, pkg_name, pkg_info, db):
        #process db, pkg depends and conflict checks
        chk_db_d = chk_db_c = chk_pkg_d = chk_pkg_c = True

        res = True
        errors = []
        provides = []

        pkg_derrs = pkg_cerrs = None # depend and conflict errors

        if pkg_name in db:              # replace
            chk_db_d = True
            del db[pkg_name]
        else:                           # install
            chk_db_d = False

        # collect provides of existing db to test against pkg
        self._collect_provides(db, provides)

        if chk_pkg_d:
            pkg_derrs = self._chk_depends(pkg_info.Depends, provides)
        if chk_pkg_c:
            pkg_cerrs = self._chk_conflicts(pkg_info.Conflicts, provides)

        if pkg_derrs or pkg_cerrs:
            errors.append({DB_KEY_NAME : pkg_info.Name,
                           DB_KEY_VERS : pkg_info.Version,
                           DB_KEY_BUIL : pkg_info.Build,
                           DB_KEY_DEPS : pkg_derrs or None,
                           DB_KEY_CONF : pkg_cerrs or None})

        # now that chk_pkg_* tests are run, add pkg's provides to the db
        provides += pkg_info.Provides
        db[pkg_name] = pkg_info

        for db_name, db_info in db.iteritems():
            if db_name is not pkg_name:
                db_derrs = db_cerrs = None

                if chk_db_d:
                    db_derrs = self._chk_depends(db_info.Depends, provides)
                if chk_db_c:
                    db_cerrs = self._chk_conflicts(db_info.Conflicts,
                                              pkg_info.Provides)
                if db_derrs or db_cerrs:
                    errors.append({DB_KEY_NAME : db_info.Name,
                                   DB_KEY_VERS : db_info.Version,
                                   DB_KEY_BUIL : db_info.Build,
                                   DB_KEY_DEPS : db_derrs or None,
                                   DB_KEY_CONF : db_cerrs or None})
        if errors:
            res = False

        return res, errors or None

    # Package Database File Operations
    def _write_db(self, db):
        fd = os.path.join(self.env.pdb_pathname, 'db')
        serialize(fd, db)

        #self.__pkg_db = None # force reload on next use

        return True

    def _create_db(self, data = {}):
        return self._write_db(data)

    def _read_db(self):
        #if self.__pkg_db is not None:
        #    return self.__pkg_db

        db = None
        fd = os.path.join(self.env.pdb_pathname, 'db')

        if os.path.exists(fd):
            db = unserialize(fd) # we trust own db blindly

            #  Fixup DB to have defaults if not present
            #for dummy, db_info in db.iteritems():
            #    self._validate_db_entry(db_info)                     

            #self.__pkg_db = db # store for further use
        else:
            db = {}
            #self.__pkg_db = db # store for further use

            self._create_db(db)

        return db

    def _chk_action(self, action, name, info = None):
        db = self._read_db()

        if action is DB.__ACTION_ADD:
            return self._chk_install(name, info, db)
        elif action is DB.__ACTION_REMOVE:
            return self._chk_remove(name, db)

    def __db_cleanup(self, db, name):
        '''
        Remove virtual entry for key name
        @param db:
        @param name:
        '''
        key = name + '-virt'
        
        if key in db:
            del db[key]
            
    def _db_entry(self, name, record = False, virtual = False):
        '''
        Store db entry
        virtual entries are stored with a postfix so they do not interfere with
        existing entries for installed versions of the same package
        @param name:
        @param record:
        @param virtual:
        '''
        db = self._read_db()
        rv = None

        if record is None:
            if name in db:
                del db[name]
                self._write_db(db)
        elif record is False:
            if name in db:
                rv = copy.deepcopy(db[name])
        else:
            if virtual:
                record.Virtual = True
            
            if record.Virtual == True:
                name = name + '-virt'
            else:
                self.__db_cleanup(db, name)
                     
            db[name] = record
            self._write_db(db)

        return rv

    def _set_pkg_state(self, info, state):
        '''
        Set the package state: i.e. imported, installed, resolved, ...
        @param info:
        @param state:
        '''
        if state in DB.STATES:
            db = self._read_db()
            name = info.InstallName

            if name in db:
                db[name].Status = state

                self._write_db(db)

    # ------------------------------------------------------------------------
    #
    # DB API methods
    #

    def lock(self, mode):
        '''
        lock db
        @param mode:
        '''
        lck = Lock()
        res = False

        try:
            res = lck.acquire(self.env.pdb_lock_pathname, mode)
        finally:
            if res is True:
                self.__lock = lck

        return True

    def unlock(self):
        '''
        unlock db
        '''
        if self.__lock:
            self.__lock.release()
            self.__lock = None

    def check_install(self, info):
        return self._chk_action(DB.__ACTION_ADD, info.Name, info)

    def check_remove(self, name):
        return self._chk_action(DB.__ACTION_REMOVE, name)

    def list_packages(self):
        '''
        return a list of all packages in the db
        '''
        return self.filter_packages(None, None)

    def filter_packages(self, filter_key = None, filter_val = None):
        '''
        apply a filter to package db
        @param filter_key:
        @param filter_val:
        '''
        db = self._read_db()
        res = []

        for pkg in sorted(db.keys()):
            info = db[pkg]

            val = {DB_KEY_NAME : info.Name,
                   DB_KEY_VERS : info.Version,
                   DB_KEY_BUIL : info.Build,
                   DB_KEY_STAT : info.Status}

            if filter_key is not None:
                if filter_val is not None:
                    filter = list(filter_val)
                    for f in filter:
                        if info.getAttrib(filter_key) == f:
                            val[filter_key] = info.getAttrib(filter_key)
                            res.append(val)
                else:
                    val[filter_key] = info.getAttrib(filter_key)
                    res.append(val)
            else:
                res.append(val)

        return res

    def status(self, name):
        db = self._read_db()

        rv = None

        if name in db:
            rv = db[name].Status
        else:
            rv = DB.UNKNOWN

        return rv

    def lookup(self, name, version = None):
        '''
        return package data from db, resolve virtual features
        @param name:
        @param version:
        '''
        db = self._read_db()

        rv = None

        if name is None:
            raise DBError("Invalid package name")

        if isinstance(name, list):
            if len(name) == 1:
                name = name[0].Name
            else:
                raise DBError("Invalid input parameter: name")
            
        if name in db:
            if version is not None and version != '':
                if eval(version)(db[name].Version):
                    rv = db[name]
            else:
                rv = db[name]

        else:
            r_p = self.resolve(name, version)
            if r_p in db:
                rv = db[r_p]
            
        return rv

    def find_package_file(self, name, type):
        path = os.path.join(self.env.lib_package_dir, name + '.' + type)
        
        res = False

        if os.path.exists(path):
            res = path

        return res

    def read_package_file(self, name, type = None):
        path = None
        data = False

        if type is None:
            path = os.path.join(self.env.lib_package_dir, name)
        else:
            path = os.path.join(self.env.lib_package_dir, name + '.' + type)

        if os.path.exists(path):
            f = open(path, 'rU')

            try:
                data = f.read()
            finally:
                f.close()

        else:
            raise DBError("non-existent resource '%s'" % \
                                 os.path.basename(path))

        return data

#    def write_package_file(self, name, type, data):
#        write_file(os.path.join(self.env.lib_package_dir, name + '.' + type),
#                   data)

#    def copy_package_file(self, file, name, type):
#        shutil.copy2(file, os.path.join(self.env.lib_package_dir,
#                                        name + '.' + type))

    def setExecutionState(self, info):
        '''
        Set if package is running or stopped
        @param info:
        '''
        db = self._read_db()
        
        db[info.Name] = info
        
        self._write_db(db)

    def commit_install(self, info):
        info.setStatus(DB.COMMITTED) # committed state

        #write virtual features table for cartridges
        if info.Type == VAL_TYPE_CRT:
            self._add_virt_prov(info)

        #store dependency table information
        if info.Depends:
            self._dt_register_deps(info)

        #store entry to package db
        self._db_entry(info.Name, info)

    def commit_remove(self, info):
        if info.Type == VAL_TYPE_CRT: #Cartridge
            self._rem_virt_prov(info)

        self._db_entry(info.Name, None)

        #remove package from dependecy table        
        # and remove package from any package depending on this package
        self.remove_dependency_table_info(info.Name)

    def set_package_state(self, info, state):
        '''
        Set package state in package db
        @param info: package info
        @param state: state
        '''
        self._set_pkg_state(info, state)
    
    # VF API Calls
    # VF api implemented in db class currently
    def resolve(self, virtual, version = None):
        db = self._read_db()

        return self._vf_db_check(db, virtual, version = None)

    def resolve_dependency_chain(self, name):
        '''
        Returns an ordered dependency chain
        @param name: Package name
        @return: Ordered list of dependencies
        '''
        db = self._read_db()

        return self._resolve_depends_chain(name, db)

    def lookup_dependency_chain(self, name):
        '''
        Returns db entries ordered according to dependency chain list
        @param name: Package name
        @return: List of DB entries
        '''
        depends = []

        db = self._read_db()

        chain = self._resolve_depends_chain(name, db)

        for dep in chain:
            if dep in db:
                depends.append(db[dep])
            else:
                #broken dependency chain found
                raise DBError("Dependency chain broken")

        return depends
    
    # ------------------------------------------------------------------------
    #
    # Dependency table methods
    # methods are located in DB.py because db uses dt and dt uses db
    # 
    # Basic dt format
    # { package a : [{'feature' : 'bar', 'provider' : {'name':'Foo','version':'2.2.0'}, ...],
    #   package b : [{'provider' : None}, ...]
    # }

    def _write_dt_db(self, db):
        file = os.path.join(self.env.pdb_pathname, 'dt')
        serialize(file, db)

        return True

    def _create_dt_db(self, data = {}):
        return self._write_dt_db(data)

    def _read_dt_db(self):
        db = None
        file = os.path.join(self.env.pdb_pathname, 'dt')

        if os.path.exists(file):
            db = unserialize(file)
        else:
            db = {}
            self._create_dt_db(db)

        return db

    def _dt_add_entry(self, dt_db, name, dtinfo):
        '''
        Add entry to the dt
        @param dt_db:
        @param name:
        @param dtinfo:
        '''
        if dtinfo.Virtual == True:
            key = name + '-virt'
        else:
            self.__db_cleanup(dt_db, name)
            key = name

        if not key in dt_db:
            # insert key=>val
            dt_db[key] = []

            # append val to key
            dt_db[key].append(dtinfo)
        else:
            found = False
            virt_found = False
            
            for v in dt_db[key]:
                if v.Feature == dtinfo.Feature and v.Provider == dtinfo.Provider:
                    # found
                    if v.Virtual == True:
                        # virtual match, overwrite
                        virt_found = True
                    else:
                        # real match
                        found = True
                    
            if virt_found is True and found is False:
                dt_db[key] = [dtinfo]
            elif virt_found is True and found is True:
                #dummy to prevent duplicate additions
                dt_db[key] = [dtinfo]
            elif virt_found is False and found is True:
                if dtinfo.Virtual == False:
                    dt_db[key] = [dtinfo]
                # else do nothing to prevent virtual entries to pollute 
            elif virt_found is False and found is False:
                dt_db[key].append(dtinfo)

    def _dt_cleanup(self, dt_db, name):
        '''
        remove unused virtual entry
        @param dt_db:
        @param name:
        '''
        key = name + '-virt'
        
        if key in dt_db:
            del dt_db[key]
            
    def _dt_get_entry(self, dt_db, name):
        res = None

        if name in dt_db:
            res = dt_db[name]

        return res

    def _dt_rem_entry(self, dt_db, name):
        if name in dt_db:
            del dt_db[name]

    def _dt_rem_dep(self, dt_db, name):
        '''
        remove dependency from dt
        @param dt_db:
        @param name:
        '''
        reregister_list = []

        for pkg in dt_db:
            for dep in dt_db[pkg]:
                if dep.Provider is not None and dep.Provider.Name == name:
                    i = dt_db[pkg].index(dep)
                    dt_db[pkg][i].Provider = None

                    if not pkg in reregister_list:
                        # make sure to reregister a new provider when one exists
                        reregister_list.append(pkg)

        return reregister_list

    def _dt_get_reregister_list(self, dt_db):
        '''
        calculate reregister list in case the dt changed
        @param dt_db:
        '''
        reregister_list = []

        for pkg in dt_db:
            for dep in dt_db[pkg]:
                if dep.Provider is None:
                    if not pkg in reregister_list:
                        reregister_list.append(pkg)

        return reregister_list
    
    def _dt_reregister_deps(self, dt_db, reregister_list):
        '''
        set new provider for each element in reregister_list
        @param dt_db:
        @param reregister_list:
        '''
        for pkg in reregister_list:
            te = dt_db[pkg]
            for entry in te:
                entry_index = dt_db[pkg].index(entry)

                for expr in entry.Feature:
                    # check all possible features
                    cname = expr.Name
                    pred = expr.Predicate or None

                    new_prov = self.lookup(cname, pred)

                    if new_prov is not None:
                        #pr = {KEY_DT_NAME : new_prov.Name, KEY_DT_VERS : new_prov.Name, KEY_DT_PROV_SF : cname}
                        
                        pr = ProvidesInfo(new_prov.Name, new_prov.Version, '')                        
                        pr._SelectedFeature = cname
                        
                        dt_db[pkg][entry_index].Provider = pr

    def _dt_register_deps(self, info):            
        '''
        register dependencies given in info in dt
        @param info:
        '''
        if info.Depends:            
            for clause in info.Depends: # iterates over all dependencies required by cartridge
                dtentry = DependencyTableInfo()
                
                # prepare dt entry            
                pr = None    
                # select providing version 
                for expr in clause: #iterate over any alternative versions                    
                    cname = expr.Name
                    pred = expr.Predicate

                    # check if cname exists in package db, with required version
                    pkg = self.lookup(cname, pred)

                    #TODO: proper version selection, currently the first found
                    # version is selected.                    
                    if pkg is not None:
                        #pr = {KEY_DT_NAME : pkg.Name, KEY_DT_VERS : pkg.Version, KEY_DT_PROV_SF : cname}
                        pr = ProvidesInfo(pkg.Name, pkg.Version, '')                      
                        pr._SelectedFeature = cname
                        
                        dtentry.setProvider(pr)
                        break

                # update dt
                dtentry.addFeature(clause)                
                                
                self.update_dependency_table(info.Name, dtentry)

    def _dt_search_deps(self, dt_db, key):
        result = []

        for k, v in dt_db.iteritems():
            if k != key:
                for vl in v:
                    if vl.Provider.Name == key:
                        if not k in result:
                            # in case the dt contains duplicate entries
                            # (should not happen but you never know)
                            result.append(k)

        return result

    def _dt_search_features(self, dt_db, key):
        result = None

        # Should only find the feature in key once
        for k, val in dt_db.iteritems():
            result = self._dt_search_features_by_pkg(dt_db, val, key)

        return result

    def _dt_search_features_by_pkg(self, dt_db, pkg, key):
        result = None

        # Should only find the feature in key once        
        for e in dt_db[pkg]:
            features = e.Feature            
            for f in features:
                if e.Virtual == True:
                    key2 = key + '-virt'
                    if f.Name == key or f.Name == key2:
                        result = e.Provider
                else:
                    if f.Name == key:
                        result = e.Provider

        return result
    
    ######################################
    ## API
    ######################################
    def update_dependency_table(self, name, dtentry):
        dt_db = self._read_dt_db()

        self._dt_add_entry(dt_db, name, dtentry)

        self._write_dt_db(dt_db)
        
    def calculate_dependency_table(self):
        dt_db = self._read_dt_db()
        
        reregister_list = self._dt_get_reregister_list(dt_db)

        self._dt_reregister_deps(dt_db, reregister_list)

        self._write_dt_db(dt_db)

    def get_dependency_table_info(self, name):
        dt_db = self._read_dt_db()

        return self._dt_get_entry(dt_db, name)

    def remove_dependency_table_info(self, name):
        dt_db = self._read_dt_db()

        reregister_list = self._dt_rem_dep(dt_db, name)

        self._dt_rem_entry(dt_db, name)

        self._dt_reregister_deps(dt_db, reregister_list)

        self._write_dt_db(dt_db)

    def find_depending_packages(self, name):
        dt_db = self._read_dt_db()

        return self._dt_search_deps(dt_db, name)

    def find_feature_packages(self, key, pkg = None):
        dt_db = self._read_dt_db()

        if pkg is None:
            return self._dt_search_features(dt_db, key)
        else:
            return self._dt_search_features_by_pkg(dt_db, pkg, key)
        
    def _write_vf_db(self, db):
        file = os.path.join(self.env.pdb_pathname, 'vf')
        serialize(file, db)

        return True

    #
    # Virtual features
    # methods implemented in db because db uses vf and vf uses db
    #
    
    def _create_vf_db(self, data = {}):
        return self._write_vf_db(data)

    def _read_vf_db(self):
        db = None
        file = os.path.join(self.env.pdb_pathname, 'vf')

        if os.path.exists(file):
            db = unserialize(file)
        else:
            db = {}
            self._create_vf_db(db)

        return db
    
    # virtual provide1 : [ pkg 1, pkg 2, pkg 3]
    # virtual provide2 : [ pkg 1, pkg 2, pkg 3]
    # virtual provide3 : [ pkg 1, pkg 2, pkg 3]
    #
    #example:
    # php   : [php-5.1, php-5.2, php-5.3]
    # php5  : [php-5.1, php-5.2, php-5.3]
    # php52 : [php-5.2]
    def _vf_db_entry(self, virt_prov, real_prov):
        '''
        Add entry to dependency tree table
        @param virt_prov: the virtual provide key
        @param real_prov: the real provide name
        '''
        vf_db = self._read_vf_db()

        for p in virt_prov:
            prov = p.Name
            if prov in vf_db:
                # key exists. check value list
                rp = vf_db[prov]
                if real_prov not in rp:
                    rp.append(real_prov)

            else:
                # key does not exist. add
                vf_db[prov] = [real_prov]

        self._write_vf_db(vf_db)

    def _vf_db_check(self, db, virt_prov, version = None):
        '''
        
        @param db:
        @param virt_prov:
        @param version: Lambda expression to validate version number
        '''
        res = None

        vf_db = self._read_vf_db()

        if virt_prov in vf_db:
            # key exists: resolve real provides
            rv = vf_db[virt_prov]

            if version is not None:
                valid_version = []
                #TODO: better resolver taking required version numbers into account
                for r in rv:
                    pkg = db[r]
                    if eval(version)(pkg.Version):
                        valid_version.append(r)

                #process valid_version list
                if len(valid_version) > 1:
                    en = len(rv) - 1
                    res = valid_version[en]
                elif len(valid_version) == 1:
                    res = valid_version[0]
            else:
                #return last entry
                en = len(rv) - 1
                res = rv[en]

        return res

    def _add_virt_prov(self, info):
        '''
        Add virtual provide to vf db
        @param info:
        '''
        provides = info.Provides
        name = info.InstallName

        self._vf_db_entry(provides, name)

    def _rem_virt_prov(self, info):
        '''
        remove virtual provide from vf db
        @param info:
        '''
        vf_db = self._read_vf_db()

        real_prov = info.InstallName

        empty = []

        for prov in vf_db.iterkeys():
            rp = vf_db[prov]
            if real_prov in rp:
                rp.remove(real_prov)

            if len(rp) == 0:
                empty.append(prov)

        for prov in empty:
            vf_db.pop(prov, None)

        self._write_vf_db(vf_db)
        
    def _chain_resolver(self, db, chain, deps):
        '''
        resolve dependency chain
        @param db:
        @param chain:
        @param deps:
        '''
        new_deps = []

        if deps is not None and len(deps) > 0:
            for d in deps: # add deps to chain
                if isinstance(d, list):
                    d = d[0]

                n = self._vf_db_check(db, d.Name) or d.Name

                n_d = None
                if n in db:
                    n_d = db[n].Depends

                inserted = False
                if not n_d is None:
                    for l in n_d:
                        _l = l[0]

                        l_n = self._vf_db_check(db, _l.Name) or _l.Name

                        if l_n in chain and not n in chain:
                            # depend on item in chain, insert before
                            i = chain.index(l_n)
                            chain.insert(i, n)
                            inserted = True
                        else:
                            #print 'append: ', l
                            new_deps.append(l)

                if not n in chain and not inserted:
                    chain.append(n)

            self._chain_resolver(db, chain, new_deps)

    def _resolve_depends_chain(self, name, db):
        chain = []

        name = self._vf_db_check(db, name) or name

        if name in db:
            deps = db[name].Depends
            self._chain_resolver(db, chain, deps)

        return chain
#
# EOF
