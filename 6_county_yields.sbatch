#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=48:00:00
#SBATCH --mem=64GB
#SBATCH --job-name=county_yields_6
#SBATCH --output=county_yields_6.out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=rc5176@nyu.edu

module purge;
module load anaconda3/2020.07;
source /share/apps/anaconda3/2020.07/etc/profile.d/conda.sh;
conda activate /scratch/rc5176/penv

python 6_county_yields.py
