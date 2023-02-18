#!/bin/bash
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --time=48:00:00
#SBATCH --mem=64GB
#SBATCH --job-name=3spatial
#SBATCH --mail-type=END
#SBATCH --mail-user=rc5176@nyu.edu
#SBATCH --array=1-56
#SBATCH -o ./spatial_3.out

module purge;
module load r/gcc/4.2.0;


INFILE="data/processed/grids/$SLURM_ARRAY_TASK_ID.csv"
if test -f "$INFILE"; then
  Rscript 3_spatial_merge.R $SLURM_ARRAY_TASK_ID
fi
