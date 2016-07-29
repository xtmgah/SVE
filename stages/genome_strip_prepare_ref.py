import csv
import os
import sys
import subprocess32 as subprocess
sys.path.append('../') #go up one in the modules
import stage_wrapper
import read_utils as sr


#function for auto-making svedb stage entries and returning the stage_id
class genome_strip(stage_wrapper.Stage_Wrapper):
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
    #~/software/svtoolkit/lib/...
    def run(self,run_id,inputs):
        #workflow is to run through the stage correctly and then check for error handles
             
        #[1a]get input names and output names setup
        in_names = {'.fa':inputs['.fa'][0]}
        #will have to figure out output file name handling
        out_exts = self.split_out_exts()
        cascade = self.strip_in_ext(in_names['.fa'],'.fa')
        out_names = {'.fa' :cascade+'_S'+str(self.stage_id)+out_exts[0],
                     '.fa.svmask.fasta' : cascade+'_S'+str(self.stage_id),
                     '.dict': cascade+'_S'+str(self.stage_id)+out_exts[2],
                     '.ploidymap.txt':cascade+'_S'+str(self.stage_id)+out_exts[3],
                     '.rdmask.bed':cascade+'_S'+str(self.stage_id)+out_exts[4]}  
        refd = self.strip_name(in_names['.fa']) #this is a bit hackish
        print(refd)
        #[2a]build command args
        
        #environment variable passing here
        SV_DIR = self.software_path+'/svtoolkit'
        PATH = self.software_path+'/jre1.7.0_72/bin:'+\
               self.software_path+'/svtoolkit/bwa:'+os.environ['PATH']
        LD_LIB = self.software_path+'/svtoolkit/bwa'
        if os.environ.has_key('LD_LIBRARY_PATH'):
            LD_LIB += ':'+os.environ['LD_LIBRARY_PATH']
        print('printing dynamically calculated PATH for bwa exe..............')
        #reused paths and files...
        sv = self.software_path+'/svtoolkit'
        classpath = sv+'/lib/SVToolkit.jar:'+sv+'/lib/gatk/GenomeAnalysisTK.jar:'+sv+'/lib/gatk/Queue.jar'
        java = 'java -Xmx64g'
        cgm  = 'org.broadinstitute.sv.apps.ComputeGenomeMask'    
        ref  = in_names['.fa']

        #must index with bwa-version-set to svtoolkit...
        
        #cp the reference....
        copy = ['cp',ref,out_names['.fa']]
        print(copy)
        indexref = ['bwa index',out_names['.fa']]
        print(indexref)
        picard = self.software_path+'/picard-tools-1.126/picard.jar'
        dictbuild = [java,'-jar',picard,'CreateSequenceDictionary',
                     'R='+out_names['.fa'], 'O='+out_names['.dict'], 'CREATE_INDEX=true']
        #builg genome_mask
#        java -Xmx2g -cp SVToolkit.jar:GenomeAnalysisTK.jar \
#        org.broadinstitute.sv.apps.ComputeGenomeMask \ 
#        -R Homo_sapiens_assembly18.fasta \ 
#        -O Homo_sapiens_assembly18.mask.chr1.36.fasta \ 
#        -readLength 36 \
#        -sequence chr13
        
        #build ploidy map, need chrom names and lens...
        seq_n = sr.get_fasta_seq_names(in_names['.fa']) #assume last two are sex chroms
        seq_l = sr.get_fasta_seq_lens(in_names['.fa'])  #get the lens here
        ploidy_name = out_names['.ploidymap.txt']
# could try this default human ploidy mapping.......
#        X  2699521  154931043  F  2
#        X  2699521  154931043  M  1
#        Y        1   59373566  F  0
#        Y        1   59373566  M  1
#        *        *          *  *  2
        x_n,y_n = '',''
        for i in range(0,len(seq_n)):
            if seq_n[i] == 'X'or seq_n[i] == 'chrX': x_n,x_l = seq_n[i],seq_l[i]
            if seq_n[i] == 'Y'or seq_n[i] == 'chrY': y_n,y_l = seq_n[i],seq_l[i] 
        doubles = ['*',' *',' *',' *',' 2\n']
        if x_n == '' or y_n == '':
            ploidy = ''.join(doubles)
        else:
            singles = [x_n,' 1 ',str(x_l),' F',' 2\n',
                       x_n,' 1 ',str(x_l),' M',' 1\n',
                       y_n,' 1 ',str(y_l),' F',' 0\n',
                       y_n,' 1 ',str(y_l),' M',' 1\n']
            ploidy = ''.join(singles+doubles)
#        print(ploidy)
        with open(ploidy_name,'w') as f:
            print('writing ploidy map file for genomestrip')
            f.write(ploidy) #white space delimited with newline
        
        #[1] this is now a readDepthMaskFile...reference.rdmask.bed
#        CHR	START	END
#        1	61699999	61900000
        rdmask_name = out_names['.rdmask.bed']
        rdmask = [['CHR','START','END']]
        for i in range(len(seq_n[:-2])):
            rdmask += [[seq_n[i],'1',str(seq_l[i])]]
        with open(rdmask_name,'w') as csvfile:
            print('writing rdmask for genomestrip')
            csvwriter = csv.writer(csvfile, delimiter='\t')
            for row in rdmask:
                csvwriter.writerow(row)
#        for row in rdmask:
#            for r in row: print r+'\t',
#            print('')
        #[2] gc mask fasta
        
        #[3] gender_map this is for each sample...       
        
        self.db_start(run_id,out_names['.fa'])        
        #[3a]execute the command here----------------------------------------------------
        output,err = '',{}
        try:
            print('duplicating the reference for genomestrip')
            output = subprocess.check_output(' '.join(copy),stderr=subprocess.STDOUT,shell=True)
            print('bwa indexing the reference for genomestrip')
            output = subprocess.check_output(' '.join(indexref),stderr=subprocess.STDOUT,
                                             shell=True,env={'PATH':PATH,'SV_DIR':SV_DIR,'LD_LIBRARY_PATH':LD_LIB})
            print('samtools faidx indexing for the reference')
            output = subprocess.check_output(' '.join(['samtools faidx',out_names['.fa']]),stderr=subprocess.STDOUT,
                                             shell=True,env={'PATH':PATH,'SV_DIR':SV_DIR,'LD_LIBRARY_PATH':LD_LIB})
            print('building picardtools dict for genomestrip')
            output = subprocess.check_output(' '.join(dictbuild),stderr=subprocess.STDOUT,
                                             shell=True,env={'PATH':PATH,'SV_DIR':SV_DIR,'LD_LIBRARY_PATH':LD_LIB})
            chrmasks = []
            for chrom in seq_n:
                chrmask = out_names['.fa.svmask.fasta']+'_'+chrom+'.fa.svmask.fasta'
                genomemask = [java,'-cp',classpath,cgm,'-R',out_names['.fa'],
                              '-O',chrmask,'-readLength',str(100),'-sequence',chrom] #try with a large read length = 250?
                print('preparing genome mask for genomestrip chr = %s'%chrom)
                output = subprocess.check_output(' '.join(genomemask),stderr=subprocess.STDOUT,
                                                 shell=True,env={'PATH':PATH,'SV_DIR':SV_DIR,'LD_LIBRARY_PATH':LD_LIB})
                chrmasks += [chrmask]
            #concate the results here...
            seqs = []
            for chrom in chrmasks:
                seqs += sr.read_fasta(chrom)
            print('concatenating the chrom masks')
            sr.write_fasta(seqs,out_names['.fa.svmask.fasta']+out_exts[1])    
            #then index the final
            print('samtools faidx for genome mask')
            output = subprocess.check_output(' '.join(['samtools faidx',out_names['.fa.svmask.fasta']+out_exts[1]]),
                                             stderr=subprocess.STDOUT,shell=True,
                                             env={'PATH':PATH,'SV_DIR':SV_DIR,'LD_LIBRARY_PATH':LD_LIB})
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
            self.db_stop(run_id,{'output':output},'',True)
            results = [out_names['.fa.svmask.fasta']+out_exts[1]]
            #for i in results: print i
            if all([os.path.exists(r) for r in results]):
                print("sucessfull........")
                return results   #return a list of names
            else:
                print("failure...........")
                return False
        else:
            self.db_stop(run_id,{'output':output},err['message'],False)
            return None