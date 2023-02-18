RES1=$(sbatch 1_data_scraping.sbatch)
RES2=$(sbatch --dependency=afterok:${RES1##* } 2_cdl_grids.sbatch)
RES3=$(sbatch --dependency=afterok:${RES2##* } 3_spatial_merge.sbatch)
RES4=$(sbatch --dependency=afterok:${RES3##* } 4_planting_season.sbatch)
RES5=$(sbatch --dependency=afterok:${RES4##* } 5_weather.sbatch)
RES6=$(sbatch --dependency=afterok:${RES5##* } 6_county_yields.sbatch)
echo "Submitted batch jobs ${RES1##* }, ${RES2##* }, ${RES3##* }, ${RES4##* }, ${RES5##* }, ${RES6##* }"
