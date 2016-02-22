################################################################################
import StringIO
import re
import sys
import os
import math
from collections import namedtuple, OrderedDict, MutableMapping
from itertools import product, combinations
from itertools import combinations_with_replacement as combinations2
################################################################################
from .. import SLHA
from ..SLHA import CaseInsensitiveDict
import checkers as check
from ..query import query_yes_no as Y_or_N
from ..matrices import (TwoDMatrix, CTwoDMatrix, HermitianMatrix, 
                      SymmetricMatrix, AntisymmetricMatrix)
from ..constants import (PID, default_inputs, default_masses, input_names, 
                       default_ckm, particle_names, input_to_PID, 
                      PID_to_input)
from ..errors import TranslationError, TranslationPathError
from errors import FlavorMatrixError, ParamCardReadError
from .. import session
from io import read_param_card, write_param_card
from translator import translate
################################################################################
__doc__ = '''
Base class for Rosetta bases as well as some utility functions for defining the 
names of flavor block elements and sorting blocks names for writing SLHA output.
'''
# Base Basis class
class Basis(MutableMapping):
    '''
    Base class from which to derive other Higgs EFT basis classes. 
    
    Designed to be instantiated with an SLHA format parameter card using
    read_param_card(). The contents of the card are stored as an SLHA.Card 
    object and the special blocks "mass" and "sminputs" are stored as 
    SLHA.NamedBlock instances in self.mass and self.input respectively.
    
    self.name   - Unique basis identifier. This will be compared to the 0th 
                  element of the block basis in the SLHA parameter card to 
                  ensure that right basis class is being instantiated for a 
                  given input card.
    self.card   - SLHA.Card instance containing SLHA.NamedBlock and SLHA.Decay 
                  instances corresponding to those specified in the parameter 
                  card. Object names taken to be the first non-whitespace 
                  characters after a "#" character in a block or parameter 
                  definition are also stored.
    self.mass   - SLHA.NamedBlock instance for the "mass" block
    self.inputs - SLHA.NamedBlock instance for the "sminputs" block
    self.ckm    - Rosetta.matrices.CTwoDMatrix instance for the VCKM and 
                  IMVCKM blocks

    self.blocks, self.required_inputs and self.required_masses should be defined 
    in accordance with block structure of the SLHA parameter card, Blocks 
    "sminput" and "mass" respectively (the Z ahd Higgs masses are also stored 
    in self.inputs). Specifically, the block names specified as keys in 
    self.blocks should match those in the SLHA card as well as the names and 
    indices of the elements (taken to be the order in which the appear in the 
    list associated the the block in self.blocks). The blocks "mass" and 
    "sminputs" should minimally contain the entries specified in required_masses 
    and required_inputs respectively. A number of checks related to these 
    definitions are performed by check_param_data(), check_mass() and 
    check_sminputs() on the data read in from the parameter card. An example is 
    shown below where the required data members are defined outside the class 
    construtor so as to instrinsically belong to all instances of the class.
    
        >> from internal import Basis
        >> class MyBasis(Basis.Basis):
        >>    name = 'mybasis'
        >>    independent = {'A','B','C','1','2','3'}
        >>    required_inputs = {1,2,4}   # a_{EW}^{-1}, Gf and MZ required
        >>    required_masses = {23,25,6} # Z, Higgs and top masses required
        >>    blocks = {'letters':['A','B','C','D']
        >>              'numbers':['1','2','3','4']} # Expected block structure
    
    The list self.independent stored the basis parameters which should be read 
    in. Any other parameters declared in self.blocks are assumed to be set by 
    the user in the calculate_dependent() method. write_param_card() writes the 
    contents of the self.newcard into a new SLHA formatted file.
    
    Basis and any of its subclasses are designed to work similarly to a 
    dictionary in that parameter values can be referenced by name (duplicate 
    names in different blocks are not handled properly so try to avoid them). 
    A value can be referenced in various ways, see below example where the 
    parameter named 'D' is stored as entry 3 in the block 'letters' written in 
    'mycard.dat':
        
        >> instance = MyBasis(param_card='mycard.dat')
        >> instance['A'] = 0.5 # set value according to name in SLHA card
        >> instance.card['A'] = 0.5 # equivalent to the above
        >> instance.card.blocks['letters']['A'] = 0.5 # from block by name 
        >> instance.card.blocks['letters'][3] = 0.5 # from block by entry 
        
    The user can define calculate_dependent() to set any dependent parameters 
    (those listed in in self.blocks but not in self.independent) and any number 
    of additional functions, usually to translate the coefficients into a given 
    basis which sets the SLHA.Card object, self.newcard. Rosetta differentiaties 
    from general utility functions and translation functions using the 
    "translation" decorator. Any function designed to take you to another 
    existing basis implemenation should be decorated with the "translation" 
    decorator with an argument corresponding to the name of the target basis. 
    This name should match the unique name of an existing basis implementation 
    also contained in the Rosetta root directory. Below would be example of a 
    translation function from our example to the Warsaw Basis.
    
        >> @Basis.translation('warsaw') # identifies as translator to warsaw 
        >> def mytranslation(self, instance):
        >>     instance['cWW'] = 10.
        >>     instance['cpHl11'] = self['myparam']
        >>     return instance
    
    Any python module saved in the root directory of the Rosetta package is 
    assumed to be a basis implementation. Furthermore, the class name of the 
    basis implementation should be the same as the file name of the python 
    module. In our example above, the class `MyBasis` would have to be saved in 
    a file named MyBasis.py. This is to help Rosetta automatically identify the 
    possible translation paths between bases. Any such class can then be used 
    by the command line script "translate". For example, Rosetta should be able 
    to figure out all possible multi-step translations.
    '''
    
    blocks = dict()
    independent = []
    # dependent = []
    flavored = dict()
    required_inputs, required_masses = set(), set()
    translate = translate
    
    def __init__(self, param_card=None, output_basis='bsmc', flavor = 'general',
                 ehdecay=False, translate=True, dependent=True, 
                 modify_inputs=True):
        '''
        Keyword arguments:
            param_card   - SLHA formatted card conforming to the definitions in 
                           self.blocks, self.required_masses and 
                           self.required_inputs.
            output_basis - target basis to which to translate coefficients.
            ehdecay      - whether to run the eHDECAY interface to calculate the 
                           Higgs width and BRs.
            translate    - Whether to call the translate method when reading in 
                           from a parameter card.
            flavor      - flavor structure of matrices: 'diagonal, 'universal' 
                           , 'MFV' or 'general'.
            dependent    - when param_card is None, whether or not to include 
                           dependent parameters in the SLHA.Card attribute of 
                           the basis instance.
        '''
        self.translations = CaseInsensitiveDict()
        
        self.flavor = flavor

        self.param_card = param_card
        self.output_basis = output_basis
        self.newname = 'Basis'
        if not hasattr(self, 'dependent'): self.dependent=[]

        self.set_dependents()

        self.set_fblocks(self.flavor)

        # read param card (sets self.inputs, self.mass, self.name, self.card)
        if param_card is not None: 
            if not os.path.exists(self.param_card):
                err = '{} does not exist!'.format(self.param_card)
                raise ParamCardReadError(err)
            
            read_param_card(self) 

            # various input checks
            check.sminputs(self, self.required_inputs) 
            check.masses(self, self.required_masses) 
            check.param_data(self)
            check.flavored_data(self)
            # generalises potentially reduced flavor structure
            
            self.set_flavor(self.flavor, 'general')
            # add dependent coefficients/blocks to self.card
            self.init_dependent()
            # generate internal OrderedDict() object for __len__, __iter__, 
            # items() and iteritems() method
            self._gen_thedict()
            
            # user defined function
            self.calculate_dependent()

            if translate:
                # translate to new basis (User defined) 
                # return an instance of a class derived from Basis
                self.newbasis = self.translate() 
            else:
                # do nothing
                self.newbasis = self
            
            if modify_inputs:
                self.newbasis.modify_inputs()
                check.modified_inputs(self.newbasis)
            
            # delete imaginary parts of diagonal elements in hermitian matrices
            if self.output_basis != 'bsmc':
                self.newbasis.reduce_hermitian_matrices()
                
            # set new SLHA card
            self.newcard = self.newbasis.card 
            self.newname = self.newbasis.name
            
            preamble = ('###################################\n'
                      + '## DECAY INFORMATION\n'
                      + '###################################')
            for decay in self.card.decays.values():
                decay.preamble = preamble
                break
                        
            try: 
                if ehdecay: 
                    self.run_eHDECAY()
            except TranslationError as e:
                print e
                print 'Translation to SILH Basis required, skipping eHDECAY.'
            
        # if param_card option not given, instantiate with class name 
        # and all coeffs set to 0 (used for creating an empty basis 
        # instance for use in translate() method)
        else: 
            self.card = self.default_card(dependent=dependent)            
            self._gen_thedict()
            
    # overloaded container (dict) methods for indexing etc.
    
    def __getitem__(self, key):
        return self.card.__getitem__(key)

    def __setitem__(self, key, value):
        if hasattr(self,'_thedict'):
            self._thedict[key]=value
        return self.card.__setitem__(key, value)
    
    def __contains__(self, key):
        return self.card.__contains__(key)
        
    def __delitem__(self, key):
        if hasattr(self,'_thedict'):
            del self._thedict[key]
        return self.card.__delitem__(key)
    
    def __len__(self):
        return len(self._thedict)
        
    def __iter__(self):
        return iter(self._thedict)
    
    def _gen_thedict(self):
        thedict = SLHA.CaseInsensitiveOrderedDict()
        for name, blk in self.card.blocks.iteritems():
            if name in self.blocks:
                for k, v in blk.iteritems():
                    thedict[blk.get_name(k)] = v
                    if isinstance(blk, SLHA.CBlock):
                        thedict[blk._re.get_name(k)] = v.real
                        thedict[blk._im.get_name(k)] = v.imag
                        
        for name, blk in self.card.matrices.iteritems():
            if name in self.fblocks:
                for k, v in blk.iteritems():
                    cname = blk.get_name(k)
                    if cname: thedict[cname] = v
                    if isinstance(blk, SLHA.CMatrix):
                        re_name = blk._re.get_name(k)
                        im_name = blk._im.get_name(k)
                        if re_name: thedict[re_name] = v.real
                        if im_name: thedict[im_name] = v.real
        self._thedict = thedict
        
    
    def set_dependents(self):
        '''
        Populate self.independent and self.dependent lists according to 
        basis class definition.
        '''
        self.all_coeffs = [c for v in self.blocks.values() for c in v]
        # remove overlaps
        self.independent = [c for c in self.independent 
                            if c not in self.dependent]

        self.dependent.extend([c for c in self.all_coeffs if (c not in
                               self.independent and c not in self.dependent)])

        # check for block names in independent
        for k,v in self.blocks.iteritems():
            if k in self.independent and k not in self.dependent:
                for fld in v:
                    if fld not in self.independent:
                        self.independent.append(fld)
                    try:
                        self.dependent.remove(fld)
                    except ValueError:
                        pass
                        
        for name, opt in self.flavored.iteritems():
            coeffs = flavor_coeffs(name, **opt)

            if name not in (self.independent + self.dependent):
                dependents, independents = [], []
                for c in coeffs:
                    if c in self.dependent:
                        self.dependent.remove(c)
                        if c in self.independent: 
                            independents.append(c)
                        else:
                            dependents.append(c)
                    elif c in self.independent:
                        independents.append(c)
                    else:
                        dependents.append(c)
                
                if not independents:
                    self.dependent.append(name)
                elif not dependents:
                    self.independent.append(name)
                else:
                    self.dependent.extend(dependents)
                    self.independent.extend(independents)
        
    def set_fblocks(self, option='general'):
        self.fblocks = dict()
        for name, opt in self.flavored.iteritems():
            opt['flavor'] = option
            coeffs = flavor_coeffs(name, **opt)
            self.fblocks[name] = coeffs

    def default_card(self, dependent=True):
        '''
        Create a new default SLHA.Card instance according to the self.blocks 
        and self.flavored structure of the basis class specified in the 
        implementaion. The dependent option allows one to switch on or off the 
        inclusion of dependent parameters in the default card. By default they 
        are included.
        '''
        thecard = SLHA.Card(name=self.name)
        thecard.add_entry('basis', 1, self.name, name = 'translated basis')

        preamble = ('\n###################################\n'
            + '## INFORMATION FOR {} BASIS\n'.format(self.name.upper())
            + '###################################\n')
            
        thecard.blocks['basis'].preamble=preamble

        # default behaviour: create one 'newcoup' block, ignoring flavored
        if not self.blocks: 
            omit = ([] if not self.flavored else 
                    [c for (k,v) in self.fblocks.items() for c in v+[k]])
            
            all_coeffs = [c for c in self.independent if c not in omit]
            self.blocks = {'newcoup':all_coeffs}
            
        # otherwise follow self.blocks structure
        for blk, flds in self.blocks.iteritems():                
            for i,fld in enumerate(flds):                    
                if dependent or (blk not in self.dependent 
                                 and fld not in self.dependent):
                    thecard.add_entry(blk, i+1, 0., name = fld)

        # deal with flavored
        for blk, flds in self.fblocks.iteritems():
            for fld in flds:
                index = (int(fld[-3]), int(fld[-1])) # XBcoeff(I)x(J)               
                if dependent or (blk not in self.dependent 
                                 and fld not in self.dependent):
                    if self.flavored[blk]['domain']=='complex':              
                        thecard.add_entry(blk, index, 0., name = 'R'+fld[1:])
                        thecard.add_entry('IM'+blk, index, 0., name = 'I'+fld[1:])
                    else:
                        thecard.add_entry(blk, index, 0., name = fld)
        
        vckm = default_ckm
        thecard.add_block(vckm)
        thecard.ckm = vckm
        thecard.set_complex()
        self.fix_matrices(card = thecard)
        return thecard
    
    def set_flavor(self, _from, to):
        if _from == to: return

        self.set_fblocks(to) # reset fblocks according to flavor option
        newcard = self.default_card(dependent=False)
        
        if (_from, to) in (('general', 'universal'), ('general', 'diagonal')):
            blks_to_del = []
            for bname, blk in self.card.matrices.iteritems():
                # only consider declared flavor matrices
                if bname not in self.flavored: continue
                
                # only consider independent blocks
                if not newcard.has_matrix(bname):
                    blks_to_del.append(bname) 
                    continue
                
                # delete elements not present in default card
                to_del = []
                no_del = []
                for k in blk.keys():
                    cname = blk.get_name(k)
                    if k not in newcard.matrices[bname]:
                        if abs(blk[k]) < 1e-6:
                            to_del.append(k)
                        else:                            
                            no_del.append(k)
                
                # only keep 2,2 and 3,3 elements as anomalous if they 
                # sufficiently different from the 1,1 element in the universal 
                # case.
                if no_del and (_from, to) == ('general', 'universal'): 
                    for diag in ((2,2), (3,3)):
                        if diag in no_del:
                            val = abs(blk[diag])
                            if val - abs(blk[1,1]) < 1e-4*val:
                                no_del.remove(diag)
                                to_del.append(diag)
                
                for k in to_del:
                    del blk[k]

                if no_del:
                    no_del_names = [blk.get_name(k) for k in no_del]
                    session.verbose(
                    '    Warning in {}.set_flavour():\n'.format(self.__class__)+
                    '    Reduction in flavour structure ' +
                    'from "{}" to "{}" '.format(_from, to) +
                    'encountered some unexpected non-zero elements ' +
                    '(> 1e-6) which were not deleted.\n' +
                    '    Not deleted: {}\n'.format(', '.join(no_del_names)))
                
            for blk in blks_to_del:
                del self.card.matrices[blk]
                        
        elif to=='general':
            for bname, blk in newcard.matrices.iteritems():
                # only consider declared flavor matrices
                if bname not in self.flavored: continue
                # Add blocks absent in self.card but present in default card
                if not self.card.has_matrix(bname):
                    self.card.add_block(blk)
                    continue
                
                oneone = self.card.matrices[bname].get((1,1), 0.)
                for k, v in blk.iteritems():
                    # only add value if element doesn't already exist in block
                    if k in self.card.matrices[bname]: continue

                    diag = (k[0] == k[1])
                    if diag: v = oneone

                    cname = blk.get_name(k)
                    self.card.add_entry(bname, k, v, name = cname)


    def init_dependent(self):
        '''
        Adds entries defined as dependent to the corresponding block of 
        self.card so that they can be assigned values in calculate_dependent().
        '''
        for bname, fields in self.blocks.iteritems():
            theblock = self.card.blocks.get(bname,[])
            to_add = [f for f in fields if f in self.dependent 
                                        and f not in theblock]
            for entry in to_add:
                self.card.add_entry(bname, fields.index(entry)+1, 0., name=entry)
        
        for bname, fields in self.fblocks.iteritems():
            theblock = self.card.matrices.get(bname,[])
            to_add = [f for f in fields if 
                      (f in self.dependent or bname in self.dependent)
                      and f not in theblock]
            
            for entry in to_add:
                index = (int(entry[-3]), int(entry[-1]))
                if self.flavored[bname]['domain']=='complex':      
                    theblock = self.card.matrices.get(bname, None)
                    if not (isinstance(theblock, SLHA.CMatrix) 
                         or isinstance(theblock, SLHA.CNamedMatrix)):
                        self.card.add_entry(bname, index, 0., 
                                            name='R'+entry[1:])
                        self.card.add_entry('IM'+bname, index, 0.,
                                            name='I'+entry[1:])
                    else:
                        self.card.add_entry(bname, index, complex(0.,0.), 
                                            name=entry)
                else:
                    value = 0.
        
        self.card.set_complex()
        self.fix_matrices()
        

    def fix_matrices(self, card=None):
        if card is None:
            card = self.card
        for name, matrix in card.matrices.iteritems():
            if name.lower() == 'vckm':
                card.matrices['vckm'] = CTwoDMatrix(matrix)
            elif name not in self.flavored:
                continue
            else:
                opt = self.flavored[name]
                kind, domain = opt['kind'], opt['domain']
                if (kind, domain) == ('hermitian', 'complex'):
                    MatrixType = HermitianMatrix
                elif (kind, domain) == ('symmetric', 'complex'):
                    MatrixType = CSymmetricMatrix
                elif ((kind, domain) == ('hermitian', 'real') or
                      (kind, domain) == ('symmetric', 'real')):
                    MatrixType = SymmetricMatrix
                elif (kind, domain) == ('general', 'real'):
                    MatrixType = TwoDMatrix                    
                elif (kind, domain) == ('general', 'complex'):
                    MatrixType = CTwoDMatrix
                else: 
                    continue
                card.matrices[name] = MatrixType(matrix)
    
    def get_other_blocks(self, card, ignore):
        ignore = [x.lower() for x in ignore] 
        
        other_blocks, other_matrices = {}, {}
        for k, v in card.blocks.iteritems():
            if k.lower() != 'basis' and k.lower() not in ignore:
                other_blocks[k]=v
        for k, v in card.matrices.iteritems():
            if k.lower() != 'basis' and k.lower() not in ignore:
                other_matrices[k]=v

        for block in other_blocks:
            theblock = card.blocks[block]
            self.card.add_block(theblock)
        
        for matrix in other_matrices:
            theblock = card.matrices[matrix]
            self.card.add_block(theblock)
        
        for decay in card.decays.values():
            self.card.add_decay(decay, preamble = decay.preamble)
        
        if card.has_block('mass'):
            self.mass=self.card.blocks['mass']
        if card.has_block('sminputs'):
            self.inputs=self.card.blocks['sminputs']
            
        self.ckm = card.matrices['vckm']
    
    def expand_matrices(self):
        '''
        Special function to populate redundant elements of matrix blocks when 
        translating to the bsmc Lagrangian so that values for all 9 entries are 
        explicitly stored before writing out the parameter card. This is to 
        stay in accordance with the SLHA format.
        The function directly modifies the _data and  _names attributes of the 
        matrices since matrices with special properties i.e. Hermitian, 
        Symmetric etc. do not grant direct access to the redundant keys such as 
        the lower triangle of a Hermitian matrix.
        '''
        all_keys = [(1,1), (1,2), (1,3),
                    (2,1), (2,2), (2,3),
                    (3,1), (3,2), (3,3)]
                    
        for matrix in self.card.matrices.values():
            # list of missing elements in _data member of matrix instance
            missing_keys = [k for k in all_keys if k not in matrix._data]
            
            if missing_keys:
                # randomly select parameter name since they all should have 
                # the same structure: (R|I)NAMEixj
                elename = matrix._names.values()[0]
                cname = elename[1:-3] # matrix name
                pref = elename[0] 
                for k in missing_keys:
                    tail = cname + '{}x{}'.format(*k)
                    matrix._data[k] = matrix[k]
                    matrix._names[k] = pref + tail
                    matrix._numbers[pref+tail] = k
                    try:
                        matrix._re._data[k] = matrix._re[k]
                        matrix._re._names[k] = 'R' + tail
                        matrix._re._numbers['R'+tail] = k
                    except AttributeError:
                        pass
                    try:
                        matrix._im._data[k] = matrix._im[k]
                        matrix._im._names[k] = 'I' + tail
                        matrix._im._numbers['I'+tail] = k
                    except AttributeError:
                        pass
    
    def reduce_hermitian_matrices(self):
        '''
        Deletes imaginary parts of the diagonal elements of HermitianMatrix 
        instances belonging to the basis instance.
        '''
        for matrix in self.card.matrices.values():
            if isinstance(matrix, HermitianMatrix):
                for i,j in matrix.keys():
                    if i==j: del matrix._im._data[i,j]
    
    def delete_dependent(self):
        '''
        Deletes all named coefficients present in self.dependent from their 
        respective containers.
        '''
        for container in (self.card.blocks, self.card.matrices):
            for name, blk in container.iteritems():
                if name in self.dependent:
                    del container[name]
                else:    
                    for n in blk._numbers:
                        if n in self.dependent:
                            del blk[n]
                    if len(blk)==0:
                        del container[name]
        
        
    def run_eHDECAY(self):
        '''
        Interface Rosetta with eHDECAY to calculate Higgs widths and branching 
        fractions. 
        '''
        from ...interfaces.eHDECAY import eHDECAY, eHDECAYInterfaceError
        try:
            BRs = eHDECAY.run(self, electroweak=True)
            BR2 = eHDECAY.run(self, interpolate=True)
            for (k,v) in BRs.iteritems():
                if v!=0.:
                    print k,v, abs(1.-(BR2[k]/v))
                else:
                    print k,v,BR2[k]
        except eHDECAYInterfaceError:
            print e
            return
        
        sum_BRs = sum([v for k,v in BRs.items() if k is not 'WTOT'])
        
        # sometimes eHDECAY gives a sum of BRs slightly greater than 1. 
        # for now a hacky global rescaling is implemented to deal with this.
        if sum_BRs > 1: 
            if abs(sum_BRs - 1.) > 1e-2: # complain if its too wrong
                raise RuntimeError('Sum of branching fractions > 1 by more than 1%')
            else:
                for channel, BR in BRs.iteritems():
                    if channel!='WTOT':
                        BRs[channel] = BR/sum_BRs
                
        totalwidth = BRs.pop('WTOT')
        
        if totalwidth < 0.:
            session.log('eHDECAY: Negative total Higgs width. Check your EFT inputs.')
            return
        
        hdecays = {}
        
        # sometimes eHDECAY gives negative branching fractions. 
        for channel, BR in BRs.iteritems(): 
            # n1, n2 = particle_names[channel[0]], particle_names[channel[1]]
            # comment = 'H -> {}{}'.format(n1,n2)
            # if BR < 0.:
            #     print ('eHDECAY: Negative branching fraction encountered ' +
            #           'for {}. Rosetta will ignore it.'.format(comment))
            #     totalwidth -= BR # adjust total width
            #     continue
            # elif BR == 0.:
            #     continue
            if BR==0.:
                continue
            else:
                hdecays[channel] = BR

        # credit
        preamble = ('# Higgs widths and branching fractions '
                    'calculated by eHDECAY.\n# Please cite '
                    'arXiv:hep-ph/974448 & arXiv:1403.3381.')
        # new SLHA.Decay block
        decayblock = SLHA.Decay(25, totalwidth, data=hdecays, preamble=preamble)
        
        if 25 not in self.newcard.decays:
            self.newcard.add_decay(decayblock)
        else:
            self.newcard.decays[25] = decayblock
        session.log('#############################\n')
        
    def calculate_dependent(self):
        '''
        Default behaviour of calculate_dependent(). Called if a subclass of 
        Basis has not implemented the function.
        '''
        session.verbose('Nothing done for {}.calculate_'\
              'dependent()\n'.format(self.__class__.__name__))
              
    def modify_inputs(self):
        '''
        Default behavoiur of modify_inputs(). Called if a subclass of 
        Basis has not implemented the function.
        '''
        session.verbose('Nothing done for {}.modify_'\
              'inputs()\n'.format(self.__class__.__name__))
        
################################################################################
    
def flavor_coeffs(name, kind='hermitian', domain='real', flavor='general', 
                         cname = None):
    '''
    Function to create flavor components of a coefficient according to its 
    properties. Takes a parameter name as an argument and returns a tuple of 
    lists corresponding to the real and imaginary parts of the matrix elements. 
    The naming convention for real coefficients is to suffix the coefficient 
    name with the matrix indices separates by "x". 
    '''
    index = (1, 2, 3)
    if cname is None: cname = name
    
    if flavor.lower() == 'diagonal':
        include = lambda i,j: i == j 
    elif flavor.lower() in ('universal','mfv'):
        include = lambda i,j: i == 1 and j == 1
    else:
        include = lambda i,j: True
        
    if (kind, domain) == ('hermitian', 'complex'):
        real = ['{0}{1}x{1}'.format(cname,i) for i in index if include(i,i)]
        cplx = ['{}{}x{}'.format(cname,i,j) for i,j in 
                combinations(index,2) if include(i,j)]

    elif (kind, domain) == ('symmetric', 'complex'):
        real = []
        cplx = ['{}{}x{}'.format(cname,i,j) for i,j in 
                combinations2(index,2) if include(i,j)]
        
    elif ((kind, domain) == ('hermitian', 'real') or
          (kind, domain) == ('symmetric', 'real')):
        real = ['{}{}x{}'.format(cname,i,j) for i,j in 
                combinations2(index,2) if include(i,j)]
        cplx = []
        
    elif (kind, domain) == ('general', 'real'):
        real = ['{}{}x{}'.format(cname,i,j) for i,j in 
                product(index,index) if include(i,j)]
        cplx = []
        
    elif (kind, domain) == ('general', 'complex'):
        real = []
        cplx = ['{}{}x{}'.format(cname,i,j) for i,j in 
                product(index,index) if include(i,j)]
        
    else:
        err = ('flavor_matrix function got and unrecognised combination of '
               '"kind" and "domain" keyword arguments')
        raise FlavorMatrixError(err)
        # return [name]
    
    if (not cplx and domain!='complex'):
        return real
    else:
        return ['C'+c for c in real+cplx]

    