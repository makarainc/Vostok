'''
Created on 15.04.2010

@author: cmk
'''

class ProvidesInfo(object):
    '''
    classdocs
    '''

    Name = ''
    Version = ''
    String = ''
    
    _SelectedFeature = '' # String refering to selected feature in DT
    
    def __init__(self, name='', version='', string=''):
        '''
        Constructor
        '''
        self.Name = name
        self.Version = version
        self.String = string
        
    def __cmp__(self, other):
        # self == other
        if self.Name == other.Name and self.Version == other.Version and self.String == other.String:
            return 0
        #elif self.Name == other.Name and self.Version >= other.Version:
        #    return 1
        else:
            return -1
    
    def __hash__(self):
        return id(self)     

    
class DependsInfo(object):
    '''
    Depends Info
    '''
    Name        = ''
    Predicate   = None
    String      = ''
    
    def __init__(self, name='', predicate=None, string=''):
        self.Name = name
        self.Predicate = predicate
        self.String = string
    
    def __cmp__(self, other):
        # self == other
        if self.Name == other.Name and self.Predicate == other.Predicate and self.String == other.String:
            return 0
        #elif self.Name == other.Name and self.Version >= other.Version:
        #    return 1
        else:
            return -1
    
    def __hash__(self):
        return id(self)     

class DependencyTableInfo(object):
    '''
    Dependency Info
    '''

    Feature = []
    Provider = None
    Virtual = False
    
    def __init__(self, virtual = False):
        self.Virtual = virtual
    
    def setProvider(self, providerInfo):
        self.Provider = providerInfo
    
    def addFeature(self, featureInfo):
        if not featureInfo in self.Feature:
            self.Feature = featureInfo
    
class VfInfo(object):
    '''
    Virtual features info
    '''
    pass