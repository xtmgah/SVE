import os
import sys
import subprocess32 as subprocess
sys.path.append('../') #go up one in the modules
import stage_wrapper

#function for auto-making svedb stage entries and returning the stage_id
class bwa_index(stage_wrapper.Stage_Wrapper):
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
    def run(self,run_id,inputs):
        #workflow is to run through the stage correctly and then check for error handles
        #[1b]get some metadata for I/O names
        
        #[2]build command args
        samtools = self.tools['SAMTOOLS']
        view = [samtools, 'view', '-Sh', inputs['.bam']]

        path = self.tools['BWA-POSTALT']
        alt_fix = [self.tools['BWA-POSTALT'], '-p', self.files['GRCH38-EXTRA'], self.files['GRCH38-ALT']]

        out_file = self.strip_in_ext(inputs['.bam'],'.bam') + '.alt.bam'
        if ('out_file' in inputs) and (inputs['out_file'] != ''):
            out_file = inputs['out_file']
        view2 = [samtools, 'view', '-1', '-', '-o', out_file]
        
        #[1a]make start entry which is a new staged_run row
        
        #[3a]execute the command here----------------------------------------------------
        print ("<<<<<<<<<<<<<SVE command>>>>>>>>>>>>>>>\n")
        print (' '.join(view + ['|'] + alt_fix + ['|'] + view2))
        subprocess.check_output(' '.join(view + ['|'] + alt_fix + ['|'] + view2),stderr=subprocess.STDOUT, shell=True)
        
        #[3b]check results--------------------------------------------------
        if err == {}:
            #self.db_stop(run_id,{'output':output},'',True)
            results = [out_file]
            #for i in results: print i
            if all([os.path.exists(r) for r in results]):
                print("<<<<<<<<<<<<<bwa index sucessfull>>>>>>>>>>>>>>>\n")
                return results
            else:
                print("<<<<<<<<<<<<<bwa index failure>>>>>>>>>>>>>>>\n")
                return None
        else:
            #self.db_stop(run_id,{'output':output},err['message'],False)
            return None
