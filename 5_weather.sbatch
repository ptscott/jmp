#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=48:00:00
#SBATCH --mem=32GB
#SBATCH --job-name=planting_season_5
#SBATCH --output=planting_season_5.out
#SBATCH --array=1-56
#SBATCH --mail-type=ALL
#SBATCH --mail-user=rc5176@nyu.edu

module purge;
module load anaconda3/2020.07;
source /share/apps/anaconda3/2020.07/etc/profile.d/conda.sh;
conda activate /scratch/rc5176/penv

python 5_weather.py $SLURM_ARRAY_TASK_ID
