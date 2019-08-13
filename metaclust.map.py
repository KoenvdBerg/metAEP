#! usr/bin/env python3

"""Author: Koen van den Berg
University: Wageningen University and Research
Department: Department of Bioinformatics
Date: 01/07/2019

The purpose of this script is to map the metagenomic and
metatranscriptomic samples to the fasta database that has been created
by module 2. This will allow to find the abundance and expression for
the found metabolic gene clusters and biosynthetic gene clusters by
gutSMASH and antiSMASH respecively. The core of this part of the
pipeline will consist of bowtie2 which, according to my BSC thesis,
performs most optimal using the sensitive-local setting. 
"""

# Import statements:
import os.path
import subprocess
from sys import argv
import sys
import argparse
from pathlib import Path
import json
import pandas as pd
import shutil
import re
import textwrap

# Functions:
def get_arguments():
    """Parsing the arguments"""
    parser = argparse.ArgumentParser(description="This script maps\
    the\ fastq files to the reference GCFs. It works as follows: ...",
    usage="metacluster.map.py [Options] -i1 [mate-1s] -i2 [mate-2s] -R\
 [reference] -O [outdir]")
    parser.add_argument("-R", "--reference", help="Provide the\
    reference fasta file. format = .fasta or .fa", required=True)
    parser.add_argument("-O", "--outdir", help="Put the path to the\
    output folder for the results here. The folder should be an\
    existing folder. Default = current folder (.)", required=True)
    parser.add_argument("-i1","--fastq1", nargs='+',help="Provide the\
    mate 1s of the paired metagenomic and/or metatranscriptomic\
    samples here. These samples should be provided in fastq-format\
    (.fastq, .fq, .fq.gz). Also, this can be a comma seperated list\
    from the command line", required=True)
    parser.add_argument("-i2","--fastq2",nargs='+',help="Provide the\
    mate 2s of the paired metagenomic and/or metatranscriptomic\
    samples here. These samples should be provided in fastq-format\
    (.fastq, .fq, .fq.gz). Also, this can be a comma seperated list\
    from the command line", required = True)
    parser.add_argument( "-cc", "--corecalculation", help="Also\
    calculate the TPM, RPKM and coverage values for the core of the\
    cluster present in the bedfile. Specify the bedfile\
    here. !Attention: the 'metaclust.GCFs_coreDNA_reference.fna'\
    should also be present in the exact same folder as the normal\
    reference file", required = False)
    parser.add_argument( "-ct", "--coverage_treshold", help="Output\
    data with a coverage higher than coverage_threshold. Default =\
    0.4", default=0.4, type=float, required = False)
    parser.add_argument( "-b", "--biom_output", help=f"Outputs the\
    resulting read counts in biom format (v1.0) as well. This will be\
    useful to analyze the results in other programs as well, most\
    importantly metagenomeSeq. If metagenomical data is provided,\
    these will be included as well in the end. This metagenomical\
    data should be in the same format as the example metadata",
    type=str, required = False)

    # Has become obsolete since I will be using Docker for publishing
    parser.add_argument( "-p1", "--bowtie2", help="Specify the full\
    path to the Bowtie2 program location here. default =\
    /bin/bowtie2. In the case that the program is not installed,\
    download the binary from:\
    https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.3.5.1/. Then\
    unzip the package and use the path to that folder here.", required
    = False)
    parser.add_argument( "-p2", "--samtools", help="Specify the full\
    path to the samtools program location here. default =\
    /bin/samtools. In the case that the program is not installed,\
    download the binary from: http://www.htslib.org/download/. Then\
    unzip the package and use the path to that folder here.", required
    = False)
    parser.add_argument( "-p3", "--bedtools", help="Specify the full\
    path to the bedtools program location here. default =\
    /bin/bedtools. In the case that the program is not installed,\
    download the binary from:\
    https://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.3.5.1/. Then\
    unzip the package and use the path to that folder here.", required
    = False)


    return(parser.parse_args())

######################################################################
# Functions for mapping the reads against GCFs and % aligned
######################################################################
def bowtie2_index(bowtie2path, reference, outdir):
    """indexes the fasta reference file
    parameters
    ----------
    bowtie2path
        string, the path to the bowtie2 program
    reference
        string, the name of the reference fasta file (GCFs)
    outdir
        string, the path of the output directory
    returns
    ----------
    index name = the name of the built bowtie2 index 
    """
    try:
        stem = Path(reference).stem
        index_name = f"{outdir}{stem}"
        if not os.path.exists(index_name + ".1.bt2"):
            if bowtie2path:
                cmd_bowtie2_index = f"{bowtie2path}/bowtie2-build {reference} {index_name}"
            else:
                cmd_bowtie2_index = f"bowtie2-build {reference} {index_name}"
            res_index = subprocess.check_output(cmd_bowtie2_index, shell=True)
    except(subprocess.CalledProcessError):
        print("Error-code M3:001, check error table")
        # Proper error here, also exit code
    return(index_name)

def bowtie2_map(bowtie2path, outdir, mate1, mate2, index):
    """Maps the .fq file to the reference (fasta)
    parameters
    ----------
    bowtie2path
        string, the path to the bowtie2 program
    outdir
        string, the path of the output directory
    mate1
    mate2
    index
        string, the stemname of the bowtie2 index
    returns
    ----------
    samfile = the .sam filename that contains all the results
    writes the mapping percentage to bowtie2_log.txt
    """
    stem = Path(mate1).stem
    sample = stem.split("_")[0]
    samfile = f"{outdir}{sample}.sam"
    
    try:
        if not os.path.exists(samfile):
            cmd_bowtie2_map = f"{bowtie2path if bowtie2path else ''}bowtie2\
            --sensitive\
            --no-unal\
            --threads 6 \
            -x {index} \
            -1 {mate1} \
            -2 {mate2} \
            -S {samfile}" # The .sam file will contain only the map results for 1 sample
            print(f"the following command will be executed by bowtie2:\n--\
--------\n{cmd_bowtie2_map}\n----------")
            res_map = subprocess.check_output(cmd_bowtie2_map, shell=True, stderr = subprocess.STDOUT)
            # Saving mapping percentage:
            with open(f"{outdir}bowtie2_log.txt", "a+") as f:
                f.write(f"#{sample}\n{res_map.decode('utf-8')}")
    except(subprocess.CalledProcessError):
        pass # raise error here
    return(samfile)

def parse_perc(outdir):
    """parses the percentage from the bowtie2 stdout
    parameters
    ----------
    outdir
        string, the path of the output directory
    returns
    ----------
    ret = dictionary containing the mapping % for each sample
    """
    ret = {}
    sample = ""
    infile = f"{outdir}bowtie2_log.txt"
    with open(infile, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                sample = line[1:]
            if "overall" in line:
                perc = line.split(" ")[0][:-1]
                perc = float(perc)/100
                ret[sample] = [perc]
    return(ret)

######################################################################
# Functions for reading SAM and BAM files
######################################################################
def samtobam(samtoolspath, sam, outdir):
    """converts .sam to .bam using samtools view
    parameters:
    ----------
    samtoolspath
        string, path to the samtools installation directory
    sam 
        string, name of the outputted bowtie2 mapping
    outdir
        string, the path of the output directory
    returns
    ----------
    bamfile = the name of the .bam file
    """
    stem = Path(sam).stem
    bamfile = f"{outdir}{stem}.bam"
    try:
        cmd_samtobam = f"{samtoolspath if samtoolspath else ''}samtools view\
        -b {sam}\
        > {bamfile}"
        res_samtobam = subprocess.check_output(cmd_samtobam, shell=True)
    except(subprocess.CalledProcessError):
        pass # raise error here
    return(bamfile)

def sortbam(samtoolspath, bam, outdir):
    """sorts the bam file
    parameters
    ----------
    samtoolspath
        string, path to the samtools installation directory
    bam
        string, the name of the accession bamfile, ".bam"-file
    outdir
        string, the path of the output directory
    returns
    ----------
    sortedbam = name of the sorted bam file
    """
    stem = Path(bam).stem
    sortedbam = f"{outdir}{stem}.sorted.bam"
    try:
        cmd_sortbam = f"{samtoolspath if samtoolspath else ''}samtools sort {bam} > {sortedbam}"
        res_sortbam = subprocess.check_output(cmd_sortbam, shell=True)
    except(subprocess.CalledProcessError):
        pass # raise error here
    return(sortedbam)

def indexbam(samtoolspath, sortedbam, outdir):
    """Builds a bam index
    parameters
    ----------
    samtoolspath
        string, path to the samtools installation directory
    sortedbam
        string, the name of the sorted bam file
    outdir
        string, the path of the output directory
    returns
    ----------
    none
    """
    try:
        cmd_bam_index = f"{samtoolspath if samtoolspath else ''}samtools index {sortedbam}"
        res_index = subprocess.check_output(cmd_bam_index, shell=True)
    except(subprocess.CalledProcessError):
        pass # raise error here
    return()

def countbam(samtoolspath, sortedbam, outdir):
    """calculates the raw counts from a BAM index
    parameters
    ----------
    samtoolspath
        string, path to the samtools installation directory
    sortedbam
        string, the name of the sorted bam file
    outdir
        string, the path of the output directory
    returns
    ----------
    counts_file = file containing the counts
    """
    counts_file = f"{sortedbam[:-3]}count"
    try:
        cmd_count = f"{samtoolspath if samtoolspath else ''}samtools idxstats {sortedbam} > {counts_file}"
        res_count = subprocess.check_output(cmd_count, shell=True)
    except(subprocess.CalledProcessError):
        pass # raise error here
    return(counts_file)

def extractcorefrombam(samtoolspath, bam, outdir, bedfile):
    """extracts regions in bedfile format from bam file
    parameters:
    ----------
    samtoolspath
        string, path to the samtools installation directory
    bam 
        string, the name of the accession bamfile, ".bam"-file
    outdir
        string, the path of the output directory
    bedfile
        the name of the bedfile with core coordinates
    returns
    ----------
    bamfile = the name of the .bam file
    """
    #  samtools view -b -L metaclust.enzymes.bedfile SRR5947807.bam > bedfile.bam
    bamstem = Path(bam).stem
    bamfile = f"{outdir}core_{bamstem}.bam"
    if os.path.exists(bedfile):
        try:
            cmd_extractcore = f"{samtoolspath if samtoolspath else ''}samtools view\
            -b {bam}\
            -L {bedfile}\
            > {bamfile}"
            res_extractcore = subprocess.check_output(cmd_extractcore, shell=True)
            print(cmd_extractcore)
        except(subprocess.CalledProcessError):
            pass # raise error here
    else:
        # raise bedfile error here!!!
        pass
    return(bamfile)

######################################################################
# RPKM and TPM counting
######################################################################
def calculateTPM(countsfile):
    """Calculates the TPM values for a sample 
    TPM = rate/sum(rate) * 10^6
    rate = nreads/cluster_length (kb)
    parameters
    ----------
    counts_file
        file containing the counts
    core
        bool, skip housekeeping genes
    returns
    ----------
    TPM = dictionary containing TPM counts per cluster
    """
    rates = {}
    ratesum = 0
    with open(countsfile, "r") as f:
        for line in f:
            line = line.strip()
            cluster, length, nreads, nnoreads = line.split("\t")
            try:
                rate = float(nreads)/float(length)
                rates[cluster] = rate
                ratesum += rate
            except(ZeroDivisionError):
                pass
    TPM = {}
    for key in rates:
        try:
            TPM[key] = rates[key]/ratesum
        except(ZeroDivisionError):
            TPM[key] = 0
    return(TPM)

def calculateRPKM(countsfile):
    """Calculates the RPKM values for a sample 
    RPKM = read_counts/(cluster_length * sum(read_counts)) * 10^9
    parameters
    ----------
    counts_file
        file containing the counts
    returns
    ----------
    RPKM = dictionary containing RPKM counts per cluster
    """
    sum_reads = 0
    read_counts = {}
    cluster_lengths = {}
    with open(countsfile, "r") as f:
        for line in f:
            if "*" not in line:
                line = line.strip()
                cluster, length, nreads, nnoreads = line.split("\t")
                sum_reads += float(nreads)
                read_counts[cluster] = float(nreads)
                cluster_lengths[cluster] = float(length)
    RPKM = {}
    for key in read_counts:
        try:
            RPKM[key] = read_counts[key]/(sum_reads*cluster_lengths[key]) * 1000000000
        except(ZeroDivisionError):
            RPKM[key] = 0
    return(RPKM)
    
######################################################################
# Functions for analysing coverage with Bedtools genomecov
######################################################################
def preparebedtools(outdir, reference):
    """makes the -g genome.file for bedtools from a fasta file. This 
    file is formatted as follows: 
    fastaheader, length
    hseq1, len(seq1)
     :       : 
    hseqn, len(seqn)
    parameters
    ----------
    outdir
        string, the path of the output directory
    reference
        string, the name of the reference fasta file (GCFs)
    returns
    ----------
    genome_file = name of the by bedtools required genome file
    """
    c = ""
    genome_file = f"{outdir}genome.file"
    with open(genome_file, "w") as w:
        with open(reference, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    line = line.replace("core_", "")
                    w.write(f"{c}\n")
                    c = 0
                    w.write(f"{line[1:]}\t")
                else:
                    c += len(line)
            w.write(f"{c}")

    #try:
    #    # This could also be done using samtools idxstats and extracting $1 & $2
    #    cmd_prepare = """awk \
    #    '$0 ~ ">" {\
    #         print c; \
    #         c=0;\
    #         printf substr($0,2,150) "\t";\
    #         } \
    #    $0 !~ ">" {\
    #        c+=length($0);\
    #    } \
    #    END { \
    #    print c; \
    #    }\
    #    ' %s > %s"""%(reference, genome_file) 
    #    res_prepare = subprocess.check_output(cmd_prepare, shell=True)
    #except(subprocess.CalledProcessError):
    #    pass # raise error here

    return(genome_file)
    
def bedtoolscoverage(bedtoolspath, gfile, outdir, sortedbam):
    """computes the coverage for each mapped region
    parameters
    ----------
    bedtoolspath
        path to the bedtools installation
    gfile
        genome file build by preparebedtools()
    outdir
        string, the path of the output directory
    sortedbam
        name of the sorted bam file
    returns
    ----------
    bg_file = the name of the bedgraph file
    """
    stem = Path(sortedbam).stem
    bg_file = f"{outdir}{stem.split('.')[0]}.bg"
    
    try:
        cmd_bedtools = f"{bedtoolspath if bedtoolspath else ''}bedtools genomecov -bga -ibam {sortedbam} -g {gfile} > {bg_file}"
        res_bedtools = subprocess.check_output(cmd_bedtools, shell=True)
    except(subprocess.CalledProcessError):
        pass # raise error here
    return(bg_file)

def computetotalcoverage(bgfile):
    """computes the total coverage of a gene cluster from a .bg file
    parameters
    ----------
    bgfile
        name of the bedgraph file
    returns
    ----------
    total_coverage = {cluster: totalcov}
    """
    nocov = {}                                                 
    clusterlen = {}                                            
    with open(bgfile, "r") as f:                               
        for line in f:                                         
            line = line.strip()                                
            cluster, start, end, cov = line.split("\t")
            clusterlen[cluster] = float(end) # last encounter is length
            if not cluster in nocov: # make entry
                nocov[cluster] = 0
            if float(cov) == 0: # enter no coverage values
                    nocov[cluster] += (float(end)-float(start))
    total_coverage = {}
    for key in nocov.keys():
        perc = (clusterlen[key] - nocov[key])/clusterlen[key]
        # Set treshold here!!!
        total_coverage[key] = perc
    return(total_coverage)

def computecorecoverage(bedgraph, bedfile):
    """computes the core "enzymatic" coverage for gene clusters
    This computation is based on the fact that the core_coverage can
    be calculated using the number of bases covered divided by the
    length of the core like this:
    cc = bc/cl
    cc = core coverage
    bc = bases covered for individual cluster
    cl = lenght of particular cluster
    parameters
    ----------
    bedgraph
        name of the bedgraph file
    bedfile
        the name of the bedfile with core coordinates        
    returns
    ----------
    core_coverage = dict, {cluster: corecov}
    """
    # Finding the lengths of the core clusters
    core_starts = {}
    core_ends = {}
    core_lengths = {}
    with open(bedfile, "r") as bf:
        for line in bf:
            line = line.strip()
            clust, start, end = line.split("\t")
            if not clust in core_lengths.keys():
                core_lengths[clust] = 0
            core_lengths[clust] += int(end) - int(start)
            if not clust in core_starts.keys():
                core_starts[clust] = []
            if not clust in core_ends.keys():
                core_ends[clust] = []
            core_starts[clust].append(int(start))
            core_ends[clust].append(int(end))
    # Whole cluster coverage calculation for each enzyme (including
    # flanking genes)
    core_cov = {}
    flag = False
    index = {}
    with open(bedgraph, "r") as f:
        for line in f:
            line = line.strip()       
            cluster, start, end, cov = line.split("\t")
            start = float(start)
            end = float(end)
            cov = float(cov)
            if not cluster in core_cov: # make entry
                core_cov[cluster] = 0
                index = 0
            try:
                try:
                    if core_ends[cluster][index] <= end and core_ends[cluster][index] >= start:
                        if cov != 0: # enter no coverage values
                            core_cov[cluster] += core_ends[cluster][index]-start
                        flag = False
                        index += 1
                    if flag:
                        if cov != 0:
                            core_cov[cluster] += end - start
                    if core_starts[cluster][index] >= start and core_starts[cluster][index] <= end:
                        if cov != 0: # enter no coverage values
                            core_cov[cluster] += end-core_starts[cluster][index]
                        flag = True
                except(IndexError):
                    pass
            except(KeyError):
                core_cov[cluster] = 0
    # Calculation
    core_coverage = {}
    for key in core_cov.keys():
        try:
            perc = (core_cov[key])/core_lengths[key]
            if perc > 1: # Sometimes core is no more than 30bp longer than expected
                perc = 1
            core_coverage[key] = perc
        except(KeyError):
            core_coverage[key] = 0
    return(core_coverage)

######################################################################
# Functions for writing results and cleaning output directory
######################################################################
def writejson(dictionary, outdir, outfile_name):
    """writes results in a dict to json format
    parameters
    ----------
    dictionary
        dict, dicionary containing some results (here mapping results)
    outdir
        string, the path to output directory
    outfile_name
        string, name for the outfile 
    returns
    ----------
    outfile = name of the .json outfile
    """
    outfile = f"{outdir}{outfile_name}"
    with open(outfile, "w") as w:
        w.write(json.dumps(dictionary, indent=4))
    return(outfile)

def export2biom(outdir, core = ""):
    """writes the results to biom format for easy loading into metagenomeSeq
    parameters
    ----------
    outdir
        string, the path to output directory
    returns
    ----------
    biom_file = the created biom-format file (without metadata)
    """    
    biom_file = f"{outdir}metaclust.map{core}.biom"
    cmd_export2biom = f"biom convert -i {outdir}metaclust.map.results.{core}RPKM_filtered.txt -o {biom_file} --table-type='Pathway table' --to-json"
    res_export = subprocess.check_output(cmd_export2biom, shell=True)
    return(biom_file)

def decoratebiom(biom_file, outdir, metadata):
    """inserts rows and column data
    """
    cmd_addmetadata = f"biom add-metadata -i {biom_file} -o {biom_file} -m {metadata}"
    res_add = subprocess.check_output(cmd_addmetadata, shell=True)
    with open(biom_file, "r") as f:
        biom_dict = json.load(f)
    with open(biom_file, "w") as w:
        w.write(json.dumps(biom_dict, indent=4))
    return(biom_file)

def purge(d, pattern):
    """removes files matching a pattern
    parameters
    ----------
    d
        string, directory path
    pattern
        string, regex
    returns
    ----------
    """
    for f in os.listdir(d):
        if re.search(pattern, f):
            os.remove(os.path.join(d, f))        

def movetodir(outdir, dirname, pattern):
    """moves files matching a patterd into new directory
    parameters
    ----------
    outdir
        string, the path to output directory
    dirname
        string, name of the new direcory
    pattern
        string, regex
    returns
    ----------
    None
    """
    # Make directory
    try:
        os.mkdir(f"{outdir}{dirname}")
        print(f"Directory {outdir}{dirname} created")
    except(FileExistsError):
        print(f"Directory {outdir}{dirname} already exists")
    # Move files into new directory
    for f in os.listdir(outdir):
        if re.search(pattern, f):
            shutil.move(os.path.join(outdir,f), os.path.join(outdir, dirname))

######################################################################
# MAIN
######################################################################
def main():
    """
    The following steps are performed:
    1) preparation of mapping (=alignment)
    2) bowtie2 for mapping, counting reads
    3) bedtools for computing coverage for each cluster
    4) saving all the results in dictionary (=memory)
    5) writing the results to .json and .csv
    6) cleaning output directory
    """
    args = get_arguments()
    print("\n".join(args.fastq1))
    print("----------\n")
    print("\n".join(args.fastq2))

    results = {} #Will be filled with TPM,RPKM,coverage for each sample
    results_core = {}
    mapping_percentages = {} #Mappping percs for each sample
    
    ##############################
    # Preparing mapping
    ##############################
    i = bowtie2_index(args.bowtie2, args.reference, args.outdir)

    ##############################
    # Whole cluster calculation
    ##############################
    for m1, m2 in zip(args.fastq1, args.fastq2):
        s = bowtie2_map(args.bowtie2, args.outdir, m1, m2, i)
        b = samtobam(args.samtools, s, args.outdir)
        sortb = sortbam(args.samtools, b, args.outdir)
        indexbam(args.samtools, sortb, args.outdir)
        countsfile = countbam(args.samtools, sortb, args.outdir)
        TPM =  calculateTPM(countsfile)
        RPKM = calculateRPKM(countsfile)

        ##############################
        # bedtools: coverage
        ##############################
        bedtools_gfile = preparebedtools(args.outdir, args.reference)
        bedgraph = bedtoolscoverage(args.bedtools, bedtools_gfile, args.outdir, sortb)
        coverage = computetotalcoverage(bedgraph)

        ##############################
        # saving results in one dictionary
        ##############################
        sample = Path(b).stem
        results[f"{sample}.TPM"] = [TPM[k] for k in TPM.keys()]
        results[f"{sample}.RPKM"] = [RPKM[k] for k in TPM.keys()]
        results[f"{sample}.cov"] = [coverage[k] for k in TPM.keys()]
        results["gene_clusters"] = list(TPM.keys()) # add gene clusters as well

        ##############################
        # Core calculation
        ##############################
        if args.corecalculation:
            sortb = extractcorefrombam(args.samtools, sortb, args.outdir, args.corecalculation)
            indexbam(args.samtools, sortb, args.outdir)
            countsfile = countbam(args.samtools, sortb, args.outdir)
            core_TPM =  calculateTPM(countsfile)
            core_RPKM = calculateRPKM(countsfile)
            # Coverage
            core_bedgraph = bedtoolscoverage(args.bedtools, bedtools_gfile, args.outdir, sortb)
            core_coverage = computecorecoverage(core_bedgraph, args.corecalculation)
            results[f"{sample}.coreTPM"] = [core_TPM[k] for k in core_TPM.keys()]
            results[f"{sample}.coreRPKM"] = [core_RPKM[k] for k in core_TPM.keys()]
            results[f"{sample}.corecov"] = [core_coverage[k] if "DNA--" in k else 0 for k in core_TPM.keys()]

    ##############################
    # writing results file: pandas
    ##############################
    # writing all the results to csv
    df = pd.DataFrame(results)
    df.set_index("gene_clusters", inplace=True)
    df.to_csv(f"{args.outdir}metaclust.map.results.ALL.csv")
    df = df.loc[(df != 0).any(1)]
    #coverage_treshold = df[f"{sample}.cov"] > args.coverage_treshold
    #df = df[coverage_treshold]
    df.to_csv(f"{args.outdir}metaclust.map.results.ALL_filtered.csv")
    
    # writing RPKM (core) filetered results
    headers_RPKM = [rpkmkey for rpkmkey in results.keys() if ".RPKM" in rpkmkey]
    df_RPKM = df[headers_RPKM]
    df_RPKM.columns = [h[:-5] for h in headers_RPKM]
    df_RPKM.to_csv(f"{args.outdir}metaclust.map.results.RPKM_filtered.csv")
    df_RPKM.to_csv(f"{args.outdir}metaclust.map.results.RPKM_filtered.txt", sep="\t")
    headers_coreRPKM = [rpkmkey for rpkmkey in results.keys() if ".coreRPKM" in rpkmkey]
    df_coreRPKM = df[headers_coreRPKM]
    df_coreRPKM.columns = [h[:-9] for h in headers_coreRPKM]
    df_coreRPKM.to_csv(f"{args.outdir}metaclust.map.results.coreRPKM_filtered.csv")
    df_coreRPKM.to_csv(f"{args.outdir}metaclust.map.results.coreRPKM_filtered.txt", sep="\t")

    # writing the results to biom format:
    if args.biom_output:
        try:
            biomfile = export2biom(args.outdir)
            biomdict = decoratebiom(biomfile, args.outdir, args.biom_output)
            if args.corecalculation:
                biomfile = export2biom(args.outdir, "core")
                biomdict = decoratebiom(biomfile, args.outdir, args.biom_output)
        except(EOFError):
            biomfile = export2biom(args.outdir)
    
    # writing mapping percentages for each sample to csv
    mapping_percentages = parse_perc(args.outdir)
    df_perc = pd.DataFrame(mapping_percentages)
    df_perc.to_csv(f"{args.outdir}metaclust.percentages.csv")


    ##############################
    # Moving and purging files
    ##############################
    movetodir(args.outdir, "bowtie2-index", ".bt2")
    movetodir(args.outdir, "bedtools-results", ".bg")
    movetodir(args.outdir, "bedtools-results", ".file")
    movetodir(args.outdir, "bowtie2-map-results", ".bam")
    movetodir(args.outdir, "bowtie2-map-results", ".sam")
    movetodir(args.outdir, "bowtie2-map-results", ".bai")
    movetodir(args.outdir, "bowtie2-raw-counts", ".count")
    movetodir(args.outdir, "map-results", ".csv")
    movetodir(args.outdir, "map-results", ".txt")
    movetodir(args.outdir, "map-results", ".biom")
    
if __name__ == "__main__":
    main()