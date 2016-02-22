import sys

from .. import session
from ..constants import (PID, default_inputs, default_masses, input_names, 
                        default_ckm, particle_names, input_to_PID, 
                        PID_to_input) 
from .. import SLHA

__doc__ = '''
Module for Rosetta basis consistency checking functions. Compares existing data 
stored in a basis instance with its declared data structure in the basis 
implementation. 
'''

def sminputs(basis, required_inputs, message='Rosetta'):
    '''
    Check consistency of sminputs w.r.t required_inputs. Any inconsistencies
    found will raise a warning and a question of whether the user wishes 
    to continue assuming default values for offending inputs. Higgs and Z 
    masses will also be stored as SM inputs.
    '''
    # Check all required inputs have been set
    input_list = ', '.join( ['{} ({})'.format(x,input_names[x]) 
                            for x in required_inputs] )
    if required_inputs:
        if basis.inputs is None:
            repr_default = ['{}={: .5e}'.format(input_names[k], 
                             default_inputs.get(k,0.)) for 
                             k in required_inputs]
            
            session.log('    Warning: Block "sminputs" not found. '\
                        'Assume default values for required inputs?')
            session.log('    Required inputs: {}'.format(input_list))
            carry_on = session.query('    Continue with default values '\
                             'for unspecified inputs? '\
                             '({})'.format(', '.join(repr_default)))
            if carry_on:
                theblock = SLHA.NamedBlock(name='sminputs')
                for m in required_inputs: 
                    theblock.new_entry(m, default_inputs[m], 
                                       name=input_names[m])
                basis.card.add_block(theblock)
                basis.inputs = theblock
            else:
                session.exit()
        else:
            if basis.mass:
                for k,v in [(i,j) for i,j in basis.mass.iteritems() 
                            if i in (23,25)]:
                    i = PID_to_input[k]
                    if i in basis.inputs:
                        v2 = float(basis.inputs[i])
                        if v!=v2:
                            session.log('    Warning: {} '.format(input_names[i])
                            + 'specified in block sminput[{}] '.format(i)
                            + '({:.5e}) not consistent with '.format(v2)
                            + 'value specified in block mass '
                            + '[{}] ({:.5e}).\n'.format(k,float(v))
                            + '    Rosetta will keep value from sminputs.')
                            basis.mass[k]=v2
                    else:
                        mstring = 'M{}'.format(particle_names[k])
                        basis.inputs.new_entry(i, v,name=mstring)

            required = set(required_inputs)
            inputs = set(basis.inputs.keys())
            missing_inputs = required.difference(inputs)
            missing_values = {k:default_inputs.get(k,0.) 
                              for k in missing_inputs}
            repr_default = ['{}={: .5e}'.format(input_names[k], 
                             default_inputs.get(k,0.)) for 
                             k in missing_inputs]
            if missing_inputs: # Deal with unassigned SM inputs
                session.log( '    Warning: Not all required SM inputs are '\
                      'defined for {}.'.format(message))
                session.log('    Required inputs: {}'.format(input_list))
                missing_list = ', '.join([str(x) for x in missing_inputs])
                session.log('    Missing inputs: {}'.format(missing_list))
                carry_on = session.query(
                    '    Continue with default values '\
                    'for unspecified inputs? '\
                    '({})'.format(', '.join(repr_default))
                                 )
                if carry_on: # sets unspecified inputs
                    for m in missing_inputs: 
                        basis.inputs.new_entry(m, default_inputs[m], 
                                              name=input_names[m])
                else:
                    session.exit()
        # ensure presence of CKM matrix
        vckm = basis.card.matrices.get('vckm', None)
        if vckm is None:
            session.once('Block "VCKM" not found, will use default values.\n')
            vckm = default_ckm
            basis.card.add_block(vckm)
        basis.ckm = vckm
    
def masses(basis, required_masses, message='Rosetta'):
    '''
    Check consistency of particle masses w.r.t required_masses. Any 
    inconsistencies found will raise a warning and a question of whether 
    the user wishes to continue assuming default values for masses. Higgs 
    and Z masses are also stored as SM inputs.
    '''
    PID_list = ', '.join([str(x) for x in required_masses])
    if required_masses:
        if basis.mass is None:

            repr_default = ['{}={:.5e}'.format(particle_names[k], 
                             default_masses.get(k,0.)) for 
                             k in required_masses]
            mass_list = ', '.join( ['{} (M{})'.format(x,particle_names[x]) 
                                    for x in required_masses] )
                                    
            session.log( '    Warning: Block "mass" not found. ')
                  # '    Assume default values for required masses?'
            session.log( '    Required PIDs: {}'.format(mass_list))

            carry_on = session.query(
                '    Assume default values '\
                'for unspecified masses? '\
                '({})'.format(', '.join(repr_default))
                             )
                
            if carry_on:
                theblock = SLHA.NamedBlock(name='mass')
                for m in required_masses: 
                    theblock.new_entry(m, default_masses[m], 
                                       name='M%s' % particle_names[m])
                basis.card.add_block(theblock)
                basis.mass = theblock
            else:
                session.exit()
        else:
            if basis.inputs:
                for k,v in [(i,j) for i,j in basis.inputs.iteritems() 
                            if i in (4,25)]:
                    i = input_to_PID[k]
                    if i in basis.mass:
                        v2 = float(basis.mass[i])
                        if v!=v2:
                            session.log('    Warning: M{} '.format(particle_names[i])
                            + 'specified in block sminput[{}] '.format(k)
                            + '({:.5e}) not consistent with '.format(v)
                            + 'value specified in block mass '
                            + '[{}] ({:.5e}).\n'.format(i,float(v2))
                            + '    Rosetta will keep value from sminputs.')
                            basis.mass[i]=v
                    else:
                        mstring = 'M{}'.format(particle_names[i])
                        basis.mass.new_entry(i, v, name=mstring)
                        
            masses = set(basis.mass.keys())
            required = set(required_masses)
            missing_masses = required.difference(masses)
            missing_values = {k:default_masses.get(k,0.) 
                              for k in missing_masses}
            if missing_masses: # Deal with unassigned fermion masses
                repr_default = ['M{}={: .5e} GeV'.format(particle_names[k],v) 
                                for k,v in missing_values.items()]
                mass_list = ', '.join(['{} (M{})'.format(x,particle_names[x]) 
                                        for x in missing_masses])

                session.log('    Warning: Not all required masses are '\
                      'defined for {}.'.format(message))
                session.log( '    Required PIDs: {}'.format(PID_list))
                session.log( '    Missing PIDs: {}'.format(mass_list))
                carry_on = session.query(
                    '    Continue assuming default values '\
                    'for unspecified masses?\n'\
                    '    ({})\n'.format(', '.join(repr_default))
                    )

                if carry_on: 
                    for m in missing_masses: 
                        basis.mass.new_entry(m, default_masses[m], 
                                            name='M%s' % particle_names[m])
                        
                else:
                    session.exit()


def param_data(basis, do_unknown=True, 
                     do_consistency=True,
                     do_dependent=True,
                     do_independent=True):
    '''
    Cross check of parameter data read in the SLHA formatted card.
    Compares lists of coefficients declared in basis.independent and 
    basis.dependent to those read in from basis.param_card.
       1)  Deals with unrecognised names by removing them from the block
       2)  Check consistency of name & numbering for the EFT basis blocks 
           declared in basis.blocks. Renames coefficients according to their 
           position in each block's list.
       2)  Prints a warning if coefficients declared as dependent are 
           assigned values in param_card. The user is asked whether or not 
           they wish to continue knowing these values could be overwritten 
           by calculate_dependent().
       3)  Checks if all coefficients declared as independent are 
           assigned values. If not, the user is given the option to 
           continue with them set to 0.
    '''
    for bname, defined in basis.blocks.iteritems():
        # collect block info
        inputblock = basis.card.blocks.get(bname, None)
        if inputblock is None:
            theblock = SLHA.NamedBlock(name=bname)
            basis.card.add_block(theblock)
            inputblock = theblock
        
        input_eles = set(inputblock.keys())
        
        defined_block = {i+1:v for i,v in enumerate(defined)}
        defined_eles = set(defined_block.keys())
        
        independent = {i:v for i,v in defined_block.iteritems() 
                       if v in basis.independent}
        dependent = {i:v for i,v in defined_block.iteritems() 
                       if v in basis.dependent}
                       
        # check for unrecognised coefficient numbers              
        unknown = input_eles.difference(defined_eles)
        if unknown and do_unknown:
            unknown_names = {i:inputblock.get_name(i,'none') 
                             for i in unknown}
            session.log( '    Warning: you have declared coefficients '\
                  'undefined in {}, block:{}.'.format(basis.__class__,
                                                      bname))
            session.log( '    The following will be ignored - '\
                  '{}'.format(', '.join(['{}:"{}"'.format(k,v) for k,v 
                                         in unknown_names.iteritems()])))
                                         
            for x in unknown: del inputblock[x]
                                         
        # check that name, number pairs match
        mismatched = []
        unnamed = []
        
        for index, name in independent.items():
            input_name = inputblock.get_name(index, None)
            if input_name is None: 
                inputblock._names[index] = name
            elif input_name.lower()!=name.lower():
                mismatched.append((index,name,input_name))
                
        if mismatched and do_consistency:
            session.log('    Warning: Mismatch of coefficient names '\
                        'in {}, block "{}".'.format(basis.__class__, bname))
            for index, name, input_name in mismatched:
                if not silent:
                    session.log('    Coefficient ' +
                           '{}, named {} '.format(index, input_name) +
                           'will be renamed to {}'.format(name))
                inputblock._names[index] = name
                inputblock._numbers[name] = index
        
        # check if coefficients defined as dependent 
        # have been assigned values
        defined_dependent = set(dependent).intersection(input_eles)
        if defined_dependent and do_dependent: 
            session.log('    Warning: you have assigned values to some '\
                       'coefficients defined as dependent '\
                       'in {}, block "{}".'.format(basis.__class__, bname))
            session.log('    Coefficients: {}'.format(', '.join(
                                            ['{}:"{}"'.format(k,v) 
                                            for k,v in dependent.items() 
                                            if k in defined_dependent]
                                            )))
            session.log('    These may be overwritten by an implementation of '\
                   '{}.calculate_dependent()'.format(basis.__class__.__name__))
                   
            carry_on = session.query('Continue?')

            if not carry_on:
                session.exit()

        
        # check if all independent coefficients are assigned values
        missing = set(independent).difference(input_eles).difference(set(dependent))
        if missing and do_independent: # Deal with unassigned independent coefficients
            session.log('    Warning: some coefficients defined as independent '\
                  'in {}, block "{}", have not been assigned values'\
                  '.'.format(basis.__class__,bname))
            session.log('    Undefined: {}'.format(', '.join(
                                            ['{}:"{}"'.format(k,v) 
                                             for k,v in independent.items() 
                                             if k in missing])))
            carry_on = session.query('Continue assuming unspecified '\
                                     'coefficients are Zero?')

            if carry_on:
                for m in missing: 
                    inputblock.new_entry(m, 0., independent[m])
            else:
                session.exit()

                
        if len(inputblock)==0:
            del basis.card.blocks[inputblock.name]


def flavored_data(basis):
    '''
    Cross check of flavored part of parameter data read in the SLHA 
    formatted card. Compares lists of coefficients declared in 
    basis.independent and basis.dependent to those read in from basis.param_card.
       1)  Deals with unrecognised names by removing them from the block
       2)  Check consistency of name & numbering for the EFT basis blocks 
           declared in basis.blocks. Renames coefficients according to their 
           position in each block's list.
       2)  Prints a warning if coefficients declared as dependent are 
           assigned values in param_card. The user is asked whether or not 
           they wish to continue knowing these values could be overwritten 
           by calculate_dependent().
       3)  Checks if all coefficients declared as independent are 
           assigned values. If not, the user is given the option to 
           continue with them set to 0.
    '''

    for bname, defined in basis.fblocks.iteritems():
        # collect block info
        inputblock = basis.card.matrices.get(bname, None)
        if inputblock is None:
            theblock = SLHA.NamedMatrix(name=bname)
            basis.card.add_block(theblock)
            inputblock = theblock
            
        input_eles = set(inputblock.keys())
        
        defined_block = {(int(v[-3]),int(v[-1])):v for 
                            i,v in enumerate(defined)}
        defined_eles = set(defined_block.keys())
        
        independent = {k:v for k,v in defined_block.iteritems() 
                       if v in basis.independent or bname in basis.independent}
        dependent = {k:v for k,v in defined_block.iteritems() 
                       if v in basis.dependent}
        # check for unrecognised coefficient numbers              
        unknown = input_eles.difference(defined_eles)
        if unknown:
            unknown_names = {i:inputblock.get_name(i,'none') 
                             for i in unknown}
            session.log('    Warning: you have declared coefficients '\
                        'undefined in {}, matrix:{}.'.format(basis.__class__,
                                                      bname))
            session.log('    The following will be ignored - '\
                        '{}'.format(', '.join(['{}:"{}"'.format(k,v) for k,v 
                                               in unknown_names.iteritems()])))
                                         
            for x in unknown: del inputblock[x]
                                         
        # check that name, number pairs match
        mismatched = []
        unnamed = []
        
        for index, name in independent.items():
            input_name = inputblock.get_name(index, None)
            if input_name is None: 
                inputblock._names[index] = name
            elif input_name.lower()!=name.lower():
                mismatched.append((index,name,input_name))
                
        if mismatched:

            session.log('    Warning: Mismatch of coefficient names '\
                  'in {}, matrix "{}".'.format(basis.__class__,
                                                      bname))
            for index, name, input_name in mismatched:
                if not silent:
                    session.log('    Coefficient ' +
                                '{}, named {} '.format(index, input_name) +
                                'will be renamed to {}'.format(name))
                inputblock._names[index] = name
                inputblock._numbers[name] = index

        # check if coefficients defined as dependent 
        # have been assigned values
        defined_dependent = set(dependent).intersection(input_eles)
        if defined_dependent: 

            session.log('    Warning: you have assigned values to some '\
                        'coefficients defined as dependent '\
                        'in {}, matrix "{}".'.format(basis.__class__, bname))
            session.log('    Coefficients: {}'.format(', '.join(
                                           ['{}:"{}"'.format(k,v) 
                                            for k,v in dependent.items() 
                                            if k in defined_dependent]
                                            )))
            session.log('    These may be overwritten by an implementation of '\
                   '{}.calculate_dependent()'.format(basis.__class__.__name__))

            carry_on = session.query('Continue?')

            if not carry_on:
                session.exit()

        # check if all independent coefficients are assigned values
        missing = set(independent).difference(input_eles).difference(set(dependent))
        if missing: # Deal with unassigned independent coefficients

            session.log('    Warning: some coefficients defined as independent '\
                  'in {}, matrix "{}", have not been assigned values'\
                  '.'.format(basis.__class__,bname))
                  
            session.log('    Undefined: {}'.format(', '.join(
                                        ['{}:"{}"'.format(k,v) 
                                         for k,v in independent.items() 
                                         if k in missing])))
            carry_on = session.query('    Continue assuming unspecified '\
                                     'coefficients are Zero?')

            if carry_on:
                for m in missing: 
                    inputblock.new_entry(m, 0., independent[m])
            else:
                session.exit()
        
        if len(inputblock)==0:
            del basis.card.matrices[inputblock.name]

def calculated_data(basis):
    '''
    Compares basis.dependent and basis.card to see if all dependent 
    coefficients have been calculated. If not, asks whether the user wants 
    to continue assuming they are zero.
    '''
    missing_dependents = set(basis.dependent).difference(basis.par_dict.keys())
    if missing_dependents and basis.dependent:
        session.log('    Warning: Set of dependent coefficients calculated '\
                    'by {0}.calculate_dependent() does not match those '\
                    'specified in {0}.'.format(basis.__class__))
        session.log('    Undefined: {}'.format(', '.join(missing_dependents)))
        
        carry_on = session.query('Continue assuming coefficients are Zero?')
        if carry_on:
            for m in missing_dependents: basis.par_dict[m]=0.
        else:
            session.exit()

        session.verbose('    Calculated coefficients match those defined '\
                        'in {}.dependent.'.format(basis.__class__.__name__))

def modified_inputs(basis):
    for k,v in [(i,j) for i,j in basis.inputs.iteritems() 
                if i in (4,5,6,7,25)]:
        i = input_to_PID[k]
        if i in basis.mass:
            v2 = float(basis.mass[i])
            if v!=v2:
                session.log('Warning: M{} '.format(particle_names[i])
                + 'in block sminputs[{}] '.format(k)
                + '({:.5e}) not consistent with '.format(v)
                + 'value specified in block mass'
                + '[{}] ({:.5e}) '.format(i,float(v2))
                + 'after modify_inputs().\n')
                
                keep_from_input = session.query(('Keep value from sminputs?'))
                    
                if keep_from_input:
                    session.verbose('Modified M{} '.format(particle_names[i]) +
                                    'in block mass[{}]'.format(i))
                    basis.mass[i]=v
                else:
                    session.verbose('Modified M{} '.format(particle_names[i]) +
                                   'in block sminputs[{}]'.format(k))
                    basis.inputs[k]=v2
                    
        else:
            mstring = 'M{}'.format(particle_names[i])
            basis.mass.new_entry(i, v,name=mstring)

