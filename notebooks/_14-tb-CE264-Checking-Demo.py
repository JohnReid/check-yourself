# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.5
#   kernelspec:
#     display_name: Python 2
#     language: python
#     name: python2
# ---

# # Purpose
# The purpose of this notebook is to demonstrate the use of possterior predictive checks for checking one's discrete choice models.
#

# ## Import needed packages

# +
import sys
from collections import OrderedDict

import scipy.stats
import pandas as pd
import numpy as np

import pylogit as pl

sys.path.insert(0, '../src')
from visualization import predictive_viz as viz

# %matplotlib inline
# -

# ## Define helper functions

from zipfile import ZipFile

ZipFile.


def unpack_on_binder(zip_file_path, temp_dir='./temp'):
    import os
    import json
    from zipfile import ZipFile
    import pandas as pd
    from collections import OrderedDict

    # Unpack the zip file to the temporary directory.
    with ZipFile(zip_file_path, 'r') as zipfile:
        zipfile.extractall(temp_dir) 

    # Load the needed objects from the temporary directory
    cov_path = os.path.join(temp_dir, 'cov.csv')
    cov_df = pd.read_csv(cov_path)

    df_path = os.path.join(temp_dir, 'df.csv')
    df = pd.read_csv(df_path)

    param_path = os.path.join(temp_dir, 'params.csv')
    params = pd.read_csv(param_path)

    spec_path = os.path.join(temp_dir, 'spec.json')
    with open(spec_path, 'rb') as f:
        spec = json.load(f, object_pairs_hook=OrderedDict)

    name_path = os.path.join(temp_dir, 'names.json')
    with open(name_path, 'rb') as f:
        name_spec = json.load(f, object_pairs_hook=OrderedDict)

    # Save the alt_id_col, obs_id_col, and choice_col
    col_dict_path = os.path.join(temp_dir, 'col_dict.json')
    with open(col_dict_path, 'rb') as f:
        col_dict = json.load(f)

    # Package the loaded objects into a dictionary for return
    results_dict =\
        {'cov_df': cov_df,
         'df': df,
         'param_series': params,
         'spec_dict': spec,
         'name_dict': name_spec,
         'col_dict': col_dict}

    # Return the created dictionary
    return results_dict



# # Load one's data

# +
estimation_results = unpack_on_binder('./temp.zip')

df = estimation_results['df']
estimated_params = estimation_results['param_series']
estimated_cov_df = estimation_results['cov_df']
model_col_dict = estimation_results['col_dict']
# -

# # Recreate the model object

# Recreate the mnl model
mnl = pl.create_choice_model(data=df,
                             alt_id_col=model_col_dict['alt_id_col'],
                             obs_id_col=model_col_dict['obs_id_col'],
                             choice_col=model_col_dict['choice_col'],
                             specification=estimation_results['spec_dict'],
                             model_type='MNL',
                             names=estimation_results['name_dict'])

print(np.round(pd.concat([car_mnl.params,
                    car_mnl.standard_errors],
                   axis=1),
               decimals=3).to_latex())

# # Replication Results
#
# The original modeling results have been replicated. To do so, I needed to change the vehicle fuel types in the mlogit data to correct a likely transcription error.

# # MNL Model Checking

# Simulate values from the sampling distribution of coefficients
cov_matrix = np.linalg.inv(-1 * car_mnl.hessian)
mnl_sampling_dist =\
    scipy.stats.multivariate_normal(mean=car_mnl.params.values,
                                    cov=cov_matrix)

# Take Draws from the sampling distribution
num_draws = 1000
np.random.seed(325)
simulated_coefs = mnl_sampling_dist.rvs(num_draws)
simulated_coefs.shape

# +
# Predict the model probabilities
simulated_probs =\
    car_mnl.predict(car_df,
                    param_list=[simulated_coefs.T, None, None, None])

# Simulate y from the sampling distribution
likelihood_sim_y =\
    viz.simulate_choice_vector(simulated_probs,
                               car_df['obs_id'].values,
                               rseed=1122018)
# -

# # Make the seven desired plots

import seaborn as sbn
import matplotlib.pyplot as plt

# ### 1. Log-Likelihood plot

# +
reload(viz)

sim_log_likes =\
    viz.compute_prior_predictive_log_likelihoods(likelihood_sim_y,
                                                 car_df,
                                                 "choices",
                                                 car_mnl)

log_like_path = '../reports/figures/log-predictive-vehicle-choice-mnl.pdf'
viz.plot_predicted_log_likelihoods(sim_log_likes,
                                   car_mnl.llf,
                                   output_file=log_like_path)
# -

# ### 2. Outcome Boxplot

# +
reload(viz)
market_path = '../reports/figures/market-share-plot-vehicle-choice-mnl.pdf'

market_dict = dict(cng='compressed_natural_gas')

viz.plot_simulated_market_shares(car_df.fuel_type.values,
                                 likelihood_sim_y,
                                 car_df.choice.values,
                                 x_label='Fuel Type',
                                 y_label='Number\nof times\nchosen',
                                 display_dict=market_dict,
                                 output_file=market_path)
# -

reload(viz)
viz.plot_simulated_market_shares(car_df.body_type.values,
                                 likelihood_sim_y,
                                 car_df.choice.values,
                                 x_label='Body Type',
                                 y_label='Number\nof times\nchosen')

# ### 3. Binned Reliability Plot

# +
reload(viz)
current_fuel = 'methanol'
filter_idx = np.where((car_df.fuel_type == current_fuel).values)[0]
# current_probs = simulated_probs[filter_idx, :]
current_probs = car_mnl.long_fitted_probs[filter_idx]
current_choices = car_mnl.choices[filter_idx]
current_sim_y = likelihood_sim_y[filter_idx, :]
current_line_label = 'Observed vs Predicted ({})'.format(current_fuel)
current_sim_label = 'Simulated vs Predicted ({})'.format(current_fuel)

current_sim_color = '#a6bddb'
current_obs_color = '#045a8d'

# viz.plot_binned_reliability(
#     current_probs,
#     current_choices,
#     sim_y=current_sim_y,
#     line_label=current_line_label,
#     line_color=current_obs_color,
#     sim_label=current_sim_label,
#     sim_line_color=current_sim_color,
#     figsize=(10, 6),
#     ref_line=True,
#     output_file='../reports/figures/reliability-plot-vehicle-choice-mnl-methanol-point.pdf')

viz.plot_binned_reliability(
    current_probs,
    current_choices,
    sim_y=current_sim_y,
    line_label=current_line_label,
    line_color=current_obs_color,
    sim_label=current_sim_label,
    sim_line_color=current_sim_color,
    figsize=(10, 6),
    ref_line=True,
    output_file='../reports/figures/reliability-plot-vehicle-choice-mnl-methanol-point.jpeg')
# -

# ###  4. Binned Marginal Model Plot

# +
current_body = 'sportuv'
selection_idx = (car_df.body_type == current_body).values

num_traces = 500
current_probs = simulated_probs[selection_idx]
current_y = car_df.loc[selection_idx, 'choice'].values
current_x = car_df.loc[selection_idx, 'price_over_log_income'].values
current_sim_y = likelihood_sim_y[selection_idx]

# filename =\
#     '../reports/figures/marginal-model-plot-vehicle-choice-mnl-suv.pdf'
filename =\
    '../reports/figures/marginal-model-plot-vehicle-choice-mnl-suv.jpeg'

viz.make_binned_marginal_model_plot(current_probs,
                                    current_y,
                                    current_x,
                                    partitions=10,
                                    sim_y=current_sim_y,
                                    y_label='Observed P(Y=SUV)',
                                    prob_label='Predicted P(Y=SUV)',
                                    sim_label='Simulated P(Y=SUV)',
                                    x_label='Binned, Mean SUV Price / ln(income)',
                                    alpha=0.5,
                                    figsize=(10, 6),
                                    output_file=filename)
# -

# ### 5. Simulated Histogram

# +
reload(viz)

filter_row = ((car_df.body_type == 'regcar') &
              (car_df.cents_per_mile == 2))
# current_title = 'Num Observations by Cents per Mile for Body = {}'
current_title = ''
# filename =\
#     '../reports/figures/histogram-vehicle-choice-mnl-regcar-operating-costs.pdf'
filename =\
    '../reports/figures/histogram-vehicle-choice-mnl-regcar-operating-costs.jpeg'

viz.plot_categorical_predictive_densities(
    car_df,
    None,
    likelihood_sim_y,
    'cents_per_mile',
    filter_row,
    car_mnl.choices,
    title=current_title.format('Regular Car'),
    filter_name='observations',
    post_color=sbn.color_palette('colorblind')[0],
    figsize=(10, 6),
    legend_loc='upper left',
    output_file=filename)
# -

# ### 6. Simulated KDE

# +
reload(viz)
current_fuel = 'electric'
filter_row = car_df.fuel_type == current_fuel
# current_title = 'KDE of Price/log(income) for {} vehicles'
current_title = ''
filename =\
    '../reports/figures/kde-vehicle-choice-mnl-electric-price.pdf'

viz.plot_simulated_kde_traces(likelihood_sim_y,
                              car_df,
                              filter_row,
                              'price_over_log_income',
                              'choice',
                              title=current_title.format(current_fuel),
                              figsize=(10, 6),
                              label='Simulated',
                              n_traces=500,
                              output_file=filename)
# -

# ### 7. Simulated CDF

# +
reload(viz)
current_body = 'sportuv'
filter_row = car_df.body_type == current_body
# current_title =\
#     'CDF of Price/log(income) for Sport Utility Vehicles'
current_title = ''
# filename =\
#     '../reports/figures/cdf-vehicle-choice-mnl-suv-price.pdf'
filename =\
    '../reports/figures/cdf-vehicle-choice-mnl-suv-price.jpeg'

viz.plot_simulated_cdf_traces(likelihood_sim_y,
                              car_df,
                              filter_row,
                              'price_over_log_income',
                              'choice',
                              label='Simulated',
                              title=current_title,
                              figsize=(10, 6),
                              output_file=filename)
# -

# ## Sandbox:
# Look at additional plots.

for body in ['regcar', 'sportcar', 'stwagon', 'van', 'truck']:
    current_body = body
    selection_idx = (car_df.body_type == current_body).values

    num_traces = 500
    current_probs = simulated_probs[selection_idx]
    current_y = car_df.loc[selection_idx, 'choice'].values
    current_x = car_df.loc[selection_idx, 'price_over_log_income'].values
    current_sim_y = likelihood_sim_y[selection_idx]

    filename = None

    viz.make_binned_marginal_model_plot(current_probs,
                                        current_y,
                                        current_x,
                                        partitions=10,
                                        sim_y=current_sim_y,
                                        y_label='Observed P(Y={})'.format(body),
                                        prob_label='Predicted P(Y={})'.format(body),
                                        sim_label='Simulated P(Y={})'.format(body),
                                        x_label='Binned, Mean {} Price / ln(income)'.format(body),
                                        alpha=0.5,
                                        figsize=(10, 6),
                                        output_file=filename)

for body in ['regcar', 'sportcar', 'stwagon', 'van', 'truck']:
    current_body = body
    filter_row = car_df.body_type == current_body
    # current_title =\
    #     'CDF of Price/log(income) for Sport Utility Vehicles'
    current_title = ''
    filename = None
    viz.plot_simulated_cdf_traces(likelihood_sim_y,
                                  car_df,
                                  filter_row,
                                  'price_over_log_income',
                                  'choice',
                                  label='Simulated ({})'.format(body),
                                  title=current_title,
                                  figsize=(10, 6),
                                  output_file=filename)

for body in ['regcar', 'sportcar', 'stwagon', 'van', 'truck']:
    filter_idx = (car_df.body_type == body).values
    current_probs = car_mnl.long_fitted_probs[filter_idx]
    current_choices = car_mnl.choices[filter_idx]
    current_sim_y = likelihood_sim_y[filter_idx, :]
    current_line_label = 'Observed vs Predicted ({})'.format(body)
    current_sim_label = 'Simulated vs Predicted ({})'.format(body)

    current_sim_color = '#a6bddb'
    current_obs_color = '#045a8d'

    reliability_path = None
    viz.plot_binned_reliability(
        current_probs,
        current_choices,
        sim_y=current_sim_y,
        line_label=current_line_label,
        line_color=current_obs_color,
        sim_label=current_sim_label,
        sim_line_color=current_sim_color,
        figsize=(10, 6),
        ref_line=True,
        output_file=reliability_path)

for fuel in ['cng', 'electric', 'gasoline']:
    current_fuel = fuel
    filter_idx = np.where((car_df.fuel_type == current_fuel).values)[0]
    current_probs = car_mnl.long_fitted_probs[filter_idx]
    current_choices = car_mnl.choices[filter_idx]
    current_sim_y = likelihood_sim_y[filter_idx, :]
    current_line_label = 'Observed vs Predicted ({})'.format(current_fuel)
    current_sim_label = 'Simulated vs Predicted ({})'.format(current_fuel)

    current_sim_color = '#a6bddb'
    current_obs_color = '#045a8d'

    reliability_path = None
    viz.plot_binned_reliability(
        current_probs,
        current_choices,
        sim_y=current_sim_y,
        line_label=current_line_label,
        line_color=current_obs_color,
        sim_label=current_sim_label,
        sim_line_color=current_sim_color,
        figsize=(10, 6),
        ref_line=True,
        output_file=reliability_path)
