#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=10:00:00
#SBATCH --mem=32GB
#SBATCH --job-name=cdl_grids_2
#SBATCH --output=2_cdl_grids.out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=rc5176@nyu.edu

module purge;
module load anaconda3/2020.07;
source /share/apps/anaconda3/2020.07/etc/profile.d/conda.sh;
conda activate /scratch/rc5176/penv


python3 2_cdl_grids.py
