RES1=$(sbatch 1_data_scraping.sh)
RES2=$(sbatch --dependency=afterok:${RES1##* } 2_cdl_grids.sh)
RES3=$(sbatch --dependency=afterok:${RES2##* } 3_spatial_merge.sh)
RES4=$(sbatch --dependency=afterok:${RES3##* } 4_planting_season.sh)
RES5=$(sbatch --dependency=afterok:${RES4##* } 5_weather.sh)
RES6=$(sbatch --dependency=afterok:${RES5##* } 6_county_yields.sh)
echo "Submitted batch jobs ${RES1##* }, ${RES2##* }, ${RES3##* }, ${RES4##* }, ${RES5##* }, ${RES6##* }"