import os
import sys
import subprocess32 as subprocess
sys.path.append('../') #go up one in the modules
import stage_wrapper

#function for auto-making svedb stage entries and returning the stage_id
class picard_dict(stage_wrapper.Stage_Wrapper):
    #path will be where a node should process the data using the in_ext, out_ext
    #stage_id should be pre-registered with db, set to None will require getting
    #a new stage_id from the  db by writing and registering it in the stages table
    def __init__(self,wrapper,dbc,retrieve,upload,params):
        #inheritance of base class stage_wrapper    
        stage_wrapper.Stage_Wrapper.__init__(self,wrapper,dbc,retrieve,upload,params)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return 0  
    
    #override this function in each wrapper...
    #bwa sampe ref.fa L.sai R.sai L.fq R.fq -f out.sam
    def run(self,run_id,inputs):
        #workflow is to run through the stage correctly and then check for error handles
    
        #[1a]get input names and output names setup
        in_name  = {'.fa':inputs['.fa'][0]}
        out_ext = self.split_out_exts()[0]
        out_name = self.strip_in_ext(in_name['.fa'],'.fa')+out_ext 
        
        #[2a]build command args
        software = self.software_path
        java = self.tools['JAVA-1.8']
        mem = '-Xmx8g'
        picard = self.tools['PICARD']
        command = [java,mem,'-jar',picard,'CreateSequenceDictionary',
                   'R='+in_name['.fa'], 'O='+out_name, 'CREATE_INDEX=true']
        
        #[2b]make start entry which is a new staged_run row
        self.command = command
        print(self.get_command_str())
        #self.db_start(run_id,in_name['.fa'])
        
        #[3a]execute the command here----------------------------------------------------
        output,err = '',{}
        try:
            output = subprocess.check_output(command,stderr=subprocess.STDOUT)
        #catch all errors that arise under normal call behavior
        except subprocess.CalledProcessError as E:
            print('call error: '+E.output)        #what you would see in the term
            err['output'] = E.output
            #the python exception issues (shouldn't have any...
            print('message: '+E.message)          #?? empty
            err['message'] = E.message
            #return codes used for failure....
            print('code: '+str(E.returncode))     #return 1 for a fail in art?
            err['code'] = E.returncode
        except OSError as E:
            print('os error: '+E.strerror)        #what you would see in the term
            err['output'] = E.strerror
            #the python exception issues (shouldn't have any...
            print('message: '+E.message)          #?? empty
            err['message'] = E.message
            #the error num
            print('code: '+str(E.errno))
            err['code'] = E.errno
        print('output:\n'+output)
        
        #[3b]check results--------------------------------------------------
        if err == {}:
            #self.db_stop(run_id,{'output':output},'',True)
            results = [out_name]
            #for i in results: print i
            if all([os.path.exists(r) for r in results]):
                print("<<<<<<<<<<<<<picard dict sucessfull>>>>>>>>>>>>>>>\n")
                return results   #return a list of names
            else:
                print("<<<<<<<<<<<<<picard dict failure>>>>>>>>>>>>>>>\n")
                return False
        else:
            #self.db_stop(run_id,{'output':output},err['message'],False)
            return None
