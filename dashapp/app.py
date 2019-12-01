# -*- coding: utf-8 -*-
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import os
from itertools import product
import numpy as np
import pandas as pd
from scipy import stats
import plotly.graph_objs as go
import seaborn as sns

import dash_daq as daq

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True

opath = '../data/{basin}/gauges/{attr}.csv'
PATH_TEMPLATES = {
    'mcm': '../results/{basin}/with optimization/{scenario}/{res_type}_{res_attr}_mcm.csv',
    'Variable Head': '../results/{basin}/with optimization/{scenario}/{res_type}_{res_attr}_m.csv',
}

basin = 'stanislaus'

MCM_TO_CFS = 1e6 / 24 / 3600 * 35.31
MCM_TO_TAF = 1.2335

AXIS_LABELS = {
    'storage': 'Storage (TAF)',
    'flow': 'Flow (cfs)',
    'generation': 'Generation (MWh)',
    'M': 'Month',
    'Y': 'Year'
}

PLOTLY_CONFIG = {
    'scrollZoom': True,
    'modeBarButtonsToRemove': ['toggleSpikelines', 'sendDataToCloud', 'autoScale2d', 'zoomOut2d', 'zoomIn2d',
                               'editInChartStudio', 'boxSelect',
                               'lassoSelect'],
    'showLink': False,
}

source_text = {'simulated': 'Simulated', 'observed': 'Observed'}
# source_name = {'simulated': 'Simulated'}
source_color = {'simulated': 'blue', 'observed': 'darkgrey'}

PALETTES = {
    'P2009': 'BuGn_r',
    'P2030': 'Blues_r',
    'P2060': 'OrRd_r'
}

GCMS = ['Livneh', 'HadGEM2-ES', 'CNRM-CM5', 'CanESM2', 'MIROC5']
RCPS = ['rcp45', 'rcp85']


def flow_to_energy(df_cfs, head):
    # df comes in as cfs...
    # MWh = Q[cms] * head[m] * eta * g[m/s^s] * rho[kg/m^3] * hours in day / 1e6
    return df_cfs / 35.31 * head * 0.9 * 9.81 * 1000 * 24 / 1e6


def get_plot_kwargs(source):
    return dict(
        mode='lines',
        opacity=0.7,
        # line_color=source_color[source]
    )


df_obs_storage = pd.read_csv(
    opath.format(basin=basin.replace('_', ' ').title() + ' River', attr='storage'),
    index_col=[0],
    parse_dates=True
) * MCM_TO_TAF

# df_obs_streamflow = pd.read_csv(
#     opath.format(basin=basin.replace('_', ' ').title() + ' River', attr='streamflow'),
#     index_col=[0],
#     parse_dates=True
# ).loc[df_hydropower.index].ffill() * MCM_TO_CFS  # mcm to cfs

df_obs_streamflow = pd.read_csv(
    opath.format(basin=basin.replace('_', ' ').title() + ' River', attr='streamflow_cfs'),
    index_col=[0],
    parse_dates=True
).ffill()  # already cfs, no need to concert

gauge_lookup = pd.read_csv('gauges.csv', index_col=[0], squeeze=True, dtype=(str)).to_dict()
gauge_number_to_name = {}
for gauge in df_obs_streamflow.columns:
    if 'USGS' in gauge:
        gauge_number_to_name[gauge.split(' ')[1]] = gauge
for loc, gauge in gauge_lookup.items():
    if gauge in gauge_number_to_name:
        gauge_lookup[loc] = gauge_number_to_name[gauge]


def root_mean_square_error(predictions, targets):
    return np.sqrt(((predictions - targets) ** 2).mean())


def nash_sutcliffe_efficiency(predictions, targets):
    if not predictions.any() or not targets.any():
        return -1
    slope, intercept, r_value, p_value, std_err = stats.linregress(predictions, targets)
    return r_value ** 2


def percent_bias(predictions, targets):
    return predictions.mean() / targets.mean() - 1


def load_timeseries(basin, scenarios, res_type, res_attr, tpl='mcm', multiplier=1.0):
    path_tpl = PATH_TEMPLATES[tpl]
    collection = []
    for scenario in scenarios:
        df = pd.read_csv(
            path_tpl.format(basin=basin, scenario=scenario, res_type=res_type, res_attr=res_attr),
            index_col=[0],
            parse_dates=True,
        ) * multiplier
        df.name = scenario
        collection.append(df)
    return pd.concat(collection, axis=1, keys=scenarios)


def consolidate_dataframe(df, resample):
    if not resample:
        fmt = '%j'
    else:
        fmt = '%m'
    new_index = [(date.strftime(fmt), str(date.year)) for date in df.index]

    df.index = pd.MultiIndex.from_tuples(new_index)
    df = df.unstack(level=-1)
    return df


percentile_colors = {
    'simulated': 'blue',
    'observed': 'grey'
}


def percentile_graphs(df, name, percentiles, color='black'):
    percentiles = percentiles[1:]
    pcts = []

    if 'median' in percentiles:
        if len(percentiles) == 1:
            pcts = [0.5]
        elif len(percentiles) == 2:
            if 'quartiles' in percentiles:
                pcts = [0.25, 0.5, 0.75]
            else:
                pcts = [0.0, 0.5, 1.0]
        else:
            pcts = [0.0, 0.25, 0.5, 0.75, 1.0]
    elif 'quartiles' in percentiles:
        if len(percentiles) == 1:
            pcts = [0.25, 0.75]
        else:
            pcts = [0.0, 0.25, 0.75, 1.0]
    elif 'range' in percentiles:
        pcts = [0.0, 1.0]

    lines = []
    for i, q in enumerate(pcts):
        opacity = 0.1
        fill = None
        width = 2
        if len(pcts) > 1 and i in [0, len(pcts) - 1]:
            width = 0
        if 0.25 < q < 0.75:
            opacity = 0.75
        if q > pcts[0]:
            fill = 'tonexty'
        lines.append(
            go.Scatter(
                x=df.index,
                y=df.quantile(q, axis=1),
                showlegend=i == 0,
                mode='lines',
                fill=fill,
                opacity=opacity,
                text='{}{}'.format(name, q),
                name=name,
                line=dict(color=color, width=width)
            )
        )

    return lines


def indicator(id, label, value, color):
    return html.Div(
        [
            label + ': ', value,
            daq.Indicator(
                color=color,
                value=True
            )
        ],
        id=id,
        style={'display': 'inline-block'}
    )


def timeseries_component(attr, res_name, all_sim_vals, df_obs, **kwargs):
    res_name_id = res_name.lower().replace(' ', '_')
    ts_data = []
    fd_data = []

    resample = kwargs.get('resample')
    percentiles = kwargs.get('percentiles')
    consolidate = 'consolidate' in percentiles
    calibration = kwargs.get('calibration')
    head = kwargs.get('head')

    for scenario in set(all_sim_vals.columns.get_level_values(0)):
        parts = scenario.split('_')
        if len(parts) == 2:
            gcm, priceyear = parts
        else:
            gcm, rcp, priceyear = parts

        sim_color = sns.color_palette(PALETTES[priceyear]).as_hex()[GCMS.index(gcm)]
        sim_vals = all_sim_vals[scenario, res_name]
        if gcm == 'Livneh':
            sim_vals = sim_vals[sim_vals.index.year < 2020]
        else:
            sim_vals = sim_vals[sim_vals.index.year >= 2020]
        if head is not None:
            sim_vals = flow_to_energy(sim_vals, head)
        if resample:
            sim_resampled = sim_vals.resample(resample).mean()
        else:
            sim_resampled = sim_vals

        plot_max = False
        max_reqt = kwargs.get('max_reqt')
        if max_reqt is not None and res_name in max_reqt:
            plot_max = True

        # Minimum flow requirement
        min_reqt = kwargs.get('min_reqt')
        if not consolidate and min_reqt is not None and res_name in min_reqt:
            ts_data.append(
                go.Scatter(
                    x=min_reqt.index,
                    y=min_reqt[res_name],
                    text='Min Requirement',
                    mode='lines',
                    opacity=0.7,
                    # opacity=0.7 if not plot_max else 0.0,
                    name='Min Requirement',
                    line_color='red'
                )
            )

        # Maximum flow requirement
        if not consolidate and plot_max:
            ts_data.append(
                go.Scatter(
                    x=max_reqt.index,
                    y=max_reqt[res_name],
                    text='Max Requirement',
                    mode='lines',
                    fill='tonexty',
                    opacity=0.7,
                    name='Max Requirement',
                    line_color='lightblue',
                    line=dict(width=0.5)
                )
            )

        if consolidate:
            sim_cons = consolidate_dataframe(sim_resampled, resample)
            sim_vals = sim_cons.quantile(0.5, axis=1)
            sim_data = percentile_graphs(sim_cons, scenario, percentiles, color=sim_color)
            ts_data.extend(sim_data)

        else:
            ts_data.append(
                go.Scatter(
                    x=sim_resampled.index,
                    y=sim_resampled,
                    text=scenario,
                    mode='lines',
                    opacity=0.7,
                    name=scenario,
                    line=dict(color=sim_color)
                )
            )

        N = len(sim_resampled)
        fd_data.append(
            go.Scatter(
                x=sorted(sim_resampled.values),
                y=np.arange(0, N) / N * 100,
                name=scenario,
                text=scenario,
                line=dict(color=sim_color),
                mode='lines',
                opacity=0.7,
            )
        )

    gauges = []
    gauge_name = gauge_lookup.get(res_name, res_name)
    pbias = 100
    nse = -1

    if calibration and gauge_name in df_obs:
        obs_vals = df_obs[gauge_name]

        head = kwargs.get('head')
        if head:
            obs_vals = flow_to_energy(obs_vals, head)

        if not consolidate:  # percentiles values will use the whole record
            obs_vals = obs_vals.loc[sim_vals.index]

        if resample:
            obs_resampled = obs_vals.resample(resample, axis=0).mean()
        else:
            obs_resampled = obs_vals

        if consolidate:  # use original values
            obs_cons = consolidate_dataframe(obs_resampled, resample)
            obs_vals = obs_cons.quantile(0.5, axis=1)  # for use in flow-duration curve

        # flow-duration curve
        N = len(obs_vals)
        fd_data.append(
            go.Scatter(
                x=sorted(obs_vals.values),
                y=np.arange(0, N) / N * 100,
                **get_plot_kwargs('observed')
            )
        )

        if consolidate:
            predictions = sim_resampled.values
            targets = obs_resampled.loc[sim_resampled.index].values
        else:
            predictions = sim_vals.values
            targets = obs_vals.loc[sim_vals.index].values

        pbias = percent_bias(predictions, targets) * 100
        # rmse = root_mean_square_error(predictions, targets)
        nse = nash_sutcliffe_efficiency(predictions, targets)

        if consolidate:
            obs_data = percentile_graphs(obs_cons, 'observed', percentiles, color='lightgrey')
            ts_data.extend(obs_data)
        else:
            obs_graph = go.Scatter(
                x=obs_resampled.index,
                y=obs_resampled,
                **get_plot_kwargs('observed')
            )
            ts_data.insert(0, obs_graph)

    if calibration:
        if nse <= 0:
            nse_color = 'red'
        elif nse <= 0.5:
            nse_color = 'orange'
        else:
            nse_color = 'green'

        GAUGE_SIZE = 80

        nse_gauge = daq.Gauge(
            id='nse-gauge-' + res_name_id,
            label='NSE',
            size=GAUGE_SIZE,
            min=-1.0,
            value=nse,
            max=1.0,
            color=nse_color,
        )
        # nse_gauge = indicator(
        #     id='nse-gauge-' + res_name_id,
        #     label='NSE',
        #     value=round(nse, 2),
        #     color=nse_color,
        # )

        if abs(pbias) >= 20:
            pbias_color = 'red'
        elif abs(pbias) >= 10:
            pbias_color = 'orange'
        else:
            pbias_color = 'green'

        pbias_gauge = daq.Gauge(
            id='pbias-gauge-' + res_name_id,
            label='% bias',
            size=GAUGE_SIZE,
            min=min(pbias, -100.0),
            value=pbias,
            max=max(pbias, 100.0),
            color=pbias_color
        )
        # pbias_gauge = indicator(
        #     id='pbias-gauge-' + res_name_id,
        #     label='% bias',
        #     value=round(pbias, 2),
        #     color=pbias_color
        # )

        gauges = html.Div(
            [nse_gauge, pbias_gauge]
        )

    ylabel = AXIS_LABELS.get(attr, 'unknown')

    timeseries_graph = dcc.Graph(
        id='timeseries-' + res_name_id,
        className='timeseries-chart',
        config=PLOTLY_CONFIG,
        figure={
            'data': ts_data,
            'layout': go.Layout(
                title='Timeseries',
                xaxis={'title': AXIS_LABELS.get(resample, "Date")},
                yaxis={'title': ylabel, 'rangemode': 'tozero'},
                margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest',
                yaxis_type=kwargs.get('transform', 'linear'),
            ),
        },

    )

    flow_duration_graph = dcc.Graph(
        id='flow-duration-' + res_name_id,
        className='flow-duration-chart',
        config=PLOTLY_CONFIG,
        figure={
            'data': fd_data,
            'layout': go.Layout(
                title='{}-duration'.format(attr.title()),
                yaxis={'title': 'Duration (%)'},
                xaxis={'title': ylabel},
                margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest',
                xaxis_type=kwargs.get('transform', 'linear')
            )
        },
    )

    children = [timeseries_graph, flow_duration_graph]

    div = html.Div(
        children=[
            html.H5(res_name),
            html.Div(
                children=children,
                className="timeseries-metrics-data",
            )
        ],
        className="timeseries-metrics-box"
    )

    return div


def gauges_content(**kwargs):
    gauges = []
    ts_data = []
    for gauge in gauges:
        ts_data.append(
            go.Scatter(
                x=df_obs_streamflow.index,
                y=df_obs_streamflow[gauge],
                text=gauge,
                mode='lines',
                opacity=0.7,
                name=gauge,
                # line=go.scatter.Line(color=source_color[source])
            )
        )
    timeseries_graph = dcc.Graph(
        id='gauges-all',
        className='timeseries-chart',
        config=PLOTLY_CONFIG,
        figure={
            'data': ts_data,
            'layout': go.Layout(
                title='Timeseries',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Flow', 'rangemode': 'tozero'},
                margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest',
                yaxis_type=kwargs.get('transform', 'linear')
            )
        }
    )

    return html.Div(
        [timeseries_graph]
    )


navbar = dbc.NavbarSimple(
    children=[
        # dbc.NavItem(dbc.NavLink("Link", href="#")),
        # dbc.DropdownMenu(
        #     nav=True,
        #     in_navbar=True,
        #     label="Menu",
        #     children=[
        #         dbc.DropdownMenuItem("Entry 1"),
        #         dbc.DropdownMenuItem("Entry 2"),
        #         dbc.DropdownMenuItem(divider=True),
        #         dbc.DropdownMenuItem("Entry 3"),
        #     ],
        # ),
    ],
    brand="San Joaquin Dashboard",
    brand_href="#",
    # sticky="top",
)

transform_radio = dbc.FormGroup(
    [
        dbc.Label("Transform", html_for="radio-transform", width=2),
        dbc.RadioItems(
            id="radio-transform",
            options=[
                {"label": "Linear", "value": 'linear'},
                {"label": "Log", "value": 'log'},
            ],
            value='linear',
            # inline=True
        ),
    ],
)

resample_radio = dbc.FormGroup(
    [
        dbc.Label("Resampling", html_for="radio-resample", width=2),
        dbc.RadioItems(
            id="radio-resample",
            options=[
                {"label": "None", "value": None},
                {"label": "Monthly", "value": 'M'},
                {"label": "Annual", "value": 'Y'},
            ],
            value="M",
            # inline=True
        ),
    ],
)

consolidation_checklist = dbc.FormGroup(
    [
        dbc.Checklist(
            id="percentiles-checklist",
            options=[
                {"id": "percentiles-checkbox", "label": "Percentiles", "value": "consolidate"}
            ],
            value=["consolidate", "median", "quartiles"],
        ),
    ],

)

select_climate = dcc.Dropdown(
    className="select-climate",
    id="select-climate",
    options=[
        {"label": "Livneh", "value": "Livneh"},
        {"label": "HadGEM2-ES", "value": "HadGEM2-ES"},
        {"label": "MIROC5", "value": "MIROC5"},
    ],
    multi=True,
    value=[]
)

select_price_year = dcc.Dropdown(
    id="select-price-year",
    className="select-price-year",
    options=[
        {"label": "PY2009", "value": "2009"},
        {"label": "PY2030", "value": "2030"},
        {"label": "PY2060", "value": "2060"},
    ],
    multi=True,
    value=[]
)

selections = dbc.Form([
    dbc.FormGroup([
        select_climate, select_price_year
    ])
], inline=True, style={"margin-bottom": "10px"})

controls = dbc.Form(
    [transform_radio, resample_radio, consolidation_checklist],
    inline=False
)


def diagnostics_content(purpose):
    return dbc.Row([
        dbc.Col([
            html.Div(children=[
                selections if purpose != 'diagnostics' else None,
                dbc.Tabs(id="diagnostics-tabs", active_tab='system', children=[
                    dbc.Tab(label='System', tab_id='system'),
                    dbc.Tab(label='Reservoir storage', tab_id='reservoir-storage'),
                    dbc.Tab(label='PH flow', tab_id='hydropower-flow'),
                    dbc.Tab(label='PH generation', tab_id='hydropower-generation'),
                    dbc.Tab(label='IFR flow (min)', tab_id='ifr-flow'),
                    dbc.Tab(label='IFR flow (range)', tab_id='ifr-range-flow'),
                    dbc.Tab(label='Outflow', tab_id='outflow')
                ]),
                html.Div(
                    id='{}-tabs-content'.format(purpose),
                    style={'padding': '10px'},
                )
            ])],
            width=11
        ),
        dbc.Col([
            html.Div([
                controls
            ])
        ], width=1)
    ])


def render_timeseries_collection(tab, **kwargs):
    children = []

    consolidate = "consolidate" in kwargs.get('percentiles', [])
    resample = kwargs.get('resample')

    climates = kwargs.get('climates')
    priceyears = kwargs.get('priceyears')
    calibration = climates is None
    kwargs['calibration'] = calibration

    if calibration:
        scenarios = ['Livneh_P2009']
    else:
        rcp = 'rcp85'
        scenarios = list(product(climates, priceyears))
        scenario_names = []
        for climate, py in scenarios:
            if climate == 'Livneh':
                scenario_name = '{}_P{}'.format(climate, py)
            else:
                scenario_name = '{}_{}_P{}'.format(climate, rcp, py)
            scenario_names.append(scenario_name)
        if not scenarios:
            return "Please select at least one climate and price year"
        else:
            scenarios = scenario_names

    if consolidate and resample == 'Y':
        return 'Sorry, you cannot consolidate annually resampled data.'

    if tab == 'reservoir-storage':
        attr = 'storage'
        df_storage = load_timeseries(basin, scenarios, 'Storage', 'Storage', multiplier=MCM_TO_TAF)
        kwargs.pop('transform', None)
        if resample:
            obs = df_obs_storage.resample(resample).mean()
        else:
            obs = df_obs_storage
        for res in set(df_storage.columns.get_level_values(1)):
            component = timeseries_component(attr, res, df_storage, obs, **kwargs)
            children.append(component)

    else:
        # df_obs = df_obs_streamflow.loc[df_hydropower.index]
        if resample:
            obs = df_obs_streamflow.resample(resample).mean()
        else:
            obs = df_obs_streamflow

    if tab in ['hydropower-generation', 'hydropower-flow', 'system']:
        df_hp1 = load_timeseries(basin, scenarios, 'PiecewiseHydropower', 'Flow')
        df_hp2 = load_timeseries(basin, scenarios, 'Hydropower', 'Flow')
        df_hp_flow = pd.concat([df_hp1, df_hp2], axis=1) * MCM_TO_CFS

    if tab in ['hydropower-generation', 'system']:
        fixed_head = pd.read_csv('../data/{} River/fixed_head.csv'.format(basin.title()), index_col=0,
                                 squeeze=True).to_dict()

    if tab == 'hydropower-flow':
        attr = 'flow'
        for res in set(df_hp_flow.columns.get_level_values(1)):
            component = timeseries_component(attr, res, df_hp_flow, obs, **kwargs)
            children.append(component)

    elif tab == 'hydropower-generation':
        attr = 'generation'
        for res in set(df_hp_flow.columns.get_level_values(1)):
            if res not in fixed_head:
                continue
            head = fixed_head[res]
            component = timeseries_component(attr, res, df_hp_flow, obs, head=head, **kwargs)
            children.append(component)

    elif tab == 'outflow':
        attr = 'flow'
        df = load_timeseries(basin, scenarios, 'Output', 'Outflow', multiplier=MCM_TO_CFS)
        for res in set(df.columns.get_level_values(1)):
            component = timeseries_component(attr, res, df, obs, **kwargs)
            children.append(component)

    elif tab == 'ifr-flow':
        attr = 'flow'
        df = load_timeseries(basin, scenarios, 'InstreamFlowRequirement', 'Flow', multiplier=MCM_TO_CFS)
        reqt = load_timeseries(basin, scenarios, 'InstreamFlowRequirement', 'Requirement', multiplier=MCM_TO_CFS)
        for res in set(df.columns.get_level_values(1)):
            component = timeseries_component(attr, res, df, obs, min_reqt=reqt, **kwargs)
            children.append(component)

    elif tab == 'ifr-range-flow':
        attr = 'flow'
        df = load_timeseries(basin, scenarios, 'PiecewiseInstreamFlowRequirement', 'Flow', multiplier=MCM_TO_CFS)
        df_pw_min_ifr_reqt = load_timeseries(
            basin, scenarios, 'PiecewiseInstreamFlowRequirement', 'Min Requirement',
            multiplier=MCM_TO_CFS
        )
        df_pw_ifr_range_reqt = load_timeseries(
            basin, scenarios, 'PiecewiseInstreamFlowRequirement', 'Max Requirement',
            multiplier=MCM_TO_CFS
        )

        df_pw_max_ifr_reqt = df_pw_min_ifr_reqt[df_pw_ifr_range_reqt.columns] + df_pw_ifr_range_reqt

        for res in set(df.columns.get_level_values(1)):
            component = timeseries_component(
                attr, res, df, obs,
                min_reqt=df_pw_min_ifr_reqt,
                max_reqt=df_pw_max_ifr_reqt,
                **kwargs
            )
            children.append(component)

    elif tab == 'system':

        # System generation
        system_res = 'System generation'
        gauged_hp = [c for c in df_hp_flow.columns if gauge_lookup.get(c) in obs]
        gauge_lookup[system_res] = system_res

        df_sim_scenarios = []
        df_obs = []
        for i, scenario in enumerate(scenarios):
            dfs_sim = []
            for res in set(df_hp_flow.columns.get_level_values(1)):
                head = fixed_head.get(res)
                hp_gauge = gauge_lookup.get(res)
                if not head or not hp_gauge:
                    continue
                sim_energy = flow_to_energy(df_hp_flow[scenario, res], head)
                dfs_sim.append(sim_energy)
                if i == 0:
                    obs_energy = flow_to_energy(obs[hp_gauge], head)
                    df_obs.append(obs_energy)
            df_sim_scenarios.append(pd.concat(dfs_sim, axis=1).sum(axis=1))
        df_sim_system = pd.concat(df_sim_scenarios, axis=1, keys=scenarios)
        df_sim_system.columns = pd.MultiIndex.from_product([scenarios, (system_res,)])
        df_obs_system = pd.concat(df_obs, axis=1).sum(axis=1).to_frame(system_res)
        hp_component = timeseries_component('generation', system_res, df_sim_system, df_obs_system, **kwargs)
        children.append(hp_component)

    return html.Div(
        children=children,
        className="timeseries-collection"
    )


BODY_STYLE = {
    'display': 'flex'
}

SIDEBAR_STYLE = {
    # "position": "fixed",
    # "top": 50,
    # "left": 0,
    # "bottom": 0,
    "width": "10rem",
    "padding": "2rem 1rem",
    # "background-color": "#f8f9fa",
}

CONTENT_STYLE = {
    # "margin-left": "5rem",
    # "margin-right": "2rem",
    "padding": "2rem 1rem",
}

body = html.Div(
    id='app-body',
    style=BODY_STYLE,
    children=[
        dbc.Nav(
            id="sidebar-tabs",
            className="sidebar-content",
            vertical=True,
            pills=True,
            style=SIDEBAR_STYLE,
            children=[
                dbc.NavItem(dbc.NavLink('Diagnostics', href='/diagnostics', id='diagnostics-tab')),
                # dbc.NavItem(dbc.NavLink('Gauges', href='/gauges', id='gauges-tab')),
                dbc.NavItem(dbc.NavLink('Analysis', href='/analysis', id='analysis-tab')),
            ]),
        html.Div(
            className='main-content',
            id='main-content',
            style=CONTENT_STYLE
        )
    ])

app.title = 'SJ Dashboard'
app.layout = html.Div(id="root", children=[dcc.Location(id="url"), navbar, body])


@app.callback(Output("main-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == '/':
        return dbc.Jumbotron(
            [
                html.H1("Welcome!"),
                html.Hr(),
                html.P("Select a tab..."),
            ]
        )
    elif pathname == "/diagnostics":
        return diagnostics_content('diagnostics')
    elif pathname == "/gauges":
        return gauges_content()
    elif pathname == '/analysis':
        return diagnostics_content('analysis')
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


@app.callback(Output('percentiles-checklist', 'options'), [
    Input('percentiles-checklist', 'value')
])
def toggle_percentile_checkboxes(values):
    disabled = 'consolidate' not in values
    return [
        {"id": "percentiles-checkbox", "label": "Percentiles", "value": "consolidate"},
        {"id": "percentiles-median", "label": "Median", "value": "median", "disabled": disabled},
        {"id": "percentiles-quartiles", "label": "Quartiles", "value": "quartiles", "disabled": disabled},
        {"id": "percentiles-range", "label": "Range", "value": "range", "disabled": disabled}
    ]


@app.callback(Output('diagnostics-tabs-content', 'children'),
              [
                  Input('diagnostics-tabs', 'active_tab'),
                  Input('radio-transform', 'value'),
                  Input('radio-resample', 'value'),
                  Input('percentiles-checklist', 'value'),
              ])
def render_diagnostics_content(tab, transform, resample, percentiles):
    kwargs = dict(
        transform=transform,
        resample=resample,
        percentiles=percentiles
    )
    return render_timeseries_collection(tab, **kwargs)


@app.callback(Output('analysis-tabs-content', 'children'),
              [
                  Input('diagnostics-tabs', 'active_tab'),
                  Input('radio-transform', 'value'),
                  Input('radio-resample', 'value'),
                  Input('percentiles-checklist', 'value'),
                  Input('select-climate', 'value'),
                  Input('select-price-year', 'value')
              ])
def render_diagnostics_content(tab, transform, resample, percentiles, climates, priceyears):
    kwargs = dict(
        climates=climates,
        priceyears=priceyears,
        transform=transform,
        resample=resample,
        percentiles=percentiles
    )
    return render_timeseries_collection(tab, **kwargs)


if __name__ == '__main__':
    app.run_server(debug=False)
