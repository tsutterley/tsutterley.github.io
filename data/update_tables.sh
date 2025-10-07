#!/bin/bash
python -c "import gravity_toolkit.utilities; gravity_toolkit.utilities.from_gfz(directory='.')"
#curl https://www.atmosp.physics.utoronto.ca/~peltier/datasets/Ice6G_C_VM5a/ICE-6G_High_Res_Stokes_trend.txt.gz \
#  -o ICE-6G_High_Res_Stokes_trend.txt.gz
#gunzip ICE-6G_High_Res_Stokes_trend.txt.gz
grace_mean_harmonics.py --verbose @parameters_CSR_RL06_mean_Ylms_013-108.txt
grace_mean_harmonics.py --verbose @parameters_GFZ_RL06_mean_Ylms_013-108.txt
grace_mean_harmonics.py --verbose @parameters_JPL_RL06_mean_Ylms_013-108.txt
python plot_global_grace_maps.py plot_parameters_CSR_RL06_L60_r350km.txt
python plot_global_grace_maps.py plot_parameters_GRFO_CSR_RL06_L60_r350km.txt
python plot_global_grace_maps.py plot_parameters_GFZ_RL06_L60_r350km.txt
python plot_global_grace_maps.py plot_parameters_GRFO_GFZ_RL06_L60_r350km.txt
python plot_global_grace_maps.py plot_parameters_JPL_RL06_L60_r350km.txt
python plot_global_grace_maps.py plot_parameters_GRFO_JPL_RL06_L60_r350km.txt
python plot_GSFC_global_mascons.py plot_parameters_GSFC_glb_rl06v2.0.txt
python grace_months_html.py
