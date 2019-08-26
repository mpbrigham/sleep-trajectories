import os
import numpy as np
import ipywidgets as widgets
import pandas as pd
import qgrid
from natsort import natsorted
from IPython.display import display

import plotly
import plotly.graph_objs as go

import mod_common_utils


def figures_in_path(my_path, figures=None, ext='.jpg'):

    if figures is None:
        figures = {}

    for item in os.listdir(my_path):
        file_path = os.path.join(my_path, item)
        if (
            os.path.isfile(file_path)
            and os.path.splitext(item)[1] == ext
        ):
            figure_id = tuple(os.path.splitext(item)[0].split('_'))
            figures[figure_id] = file_path

    return figures


class FiguresViewer:

    def __init__(self, session):

        self.session = session

        self.figure_selection = [] 

        if isinstance(self.session['paths'], (tuple, list)):
            paths = self.session['paths']
        else:
            paths = [self.session['paths']]

        self.figures = {}
        for my_path in paths:
            self.figures = figures_in_path(my_path, figures=self.figures)

        keys_all = np.array(list(self.figures.keys()))

        self.fs_max_all = sorted(set(keys_all[:, 0]))
        self.norm_all = natsorted(set(keys_all[:, 1]))
        self.fft_bin_size_all = sorted(set(keys_all[:, 2]))
        self.psd_method_all = natsorted(set(keys_all[:, 3]))
        self.normf_all = natsorted(set(keys_all[:, 4]))

        self.norm_all = self.none_first(self.norm_all)
        self.normf_all = self.none_first(self.normf_all)

        self.panel_setup()
        self.panel_refresh()

    def none_first(self, my_sort):
        if 'none' in my_sort:
            my_sort.remove('none')
            my_sort = ['none'] + my_sort
        return my_sort

    def panel_setup(self):

        self.fs_max_select = widgets.RadioButtons(
            options=self.fs_max_all,
            value=self.fs_max_all[0],
            description='Fs max'
        )

        self.norm_select = widgets.RadioButtons(
            options=self.norm_all,
            value=self.norm_all[0],
            description='Norm time'
        )

        self.fft_bin_size_select = widgets.RadioButtons(
            options=self.fft_bin_size_all,
            value=self.fft_bin_size_all[0],
            description='FFT bin size'
        )

        self.psd_method_select = widgets.RadioButtons(
            options=self.psd_method_all,
            value=self.psd_method_all[0],
            description='PSD method'
        )

        self.normf_select = widgets.RadioButtons(
            options=self.normf_all,
            value=self.normf_all[0],
            description='Norm freq'
        )

        self.panel_height_select = widgets.IntSlider(
            min=100,
            max=2000,
            step=50,
            value=800,
            description='Panel height'
        )

        self.scale_select = widgets.IntSlider(
            min=10,
            max=100,
            step=10,
            value=100,
            description='Fig size'
        )

        self.params_hbox = widgets.HBox([
                self.fs_max_select,
                self.norm_select, 
                self.fft_bin_size_select, 
                self.psd_method_select, 
                self.normf_select
        ])

        self.params_images_hbox = widgets.HBox([
            self.scale_select,self.panel_height_select
        ])

        self.images_vbox = widgets.VBox()

        display(widgets.VBox([
            self.params_hbox,
            self.params_images_hbox,
            self.images_vbox 
        ]))

        self.fs_max_select.observe(self.panel_refresh, names='value')
        self.norm_select.observe(self.panel_refresh, names='value')
        self.fft_bin_size_select.observe(self.panel_refresh, names='value')
        self.psd_method_select.observe(self.panel_refresh, names='value')
        self.normf_select.observe(self.panel_refresh, names='value')
        self.panel_height_select.observe(self.panel_refresh, names='value')
        self.scale_select.observe(self.panel_refresh, names='value')

    def panel_refresh(self, *pargs):

        select_name = '_'.join([
            self.fs_max_select.value, 
            self.norm_select.value, 
            self.fft_bin_size_select.value, 
            self.psd_method_select.value, 
            self.normf_select.value
        ])

        figure_selection = natsorted([
            self.figures[item] for item in self.figures
            if select_name in self.figures[item]
        ])
        
        image_width = int(1350*self.scale_select.value/100)
        panel_height = self.panel_height_select.value

        images = []
        for figure_path in figure_selection:
            with open(figure_path, 'rb') as f:
                images += [widgets.Image(
                    value=f.read(),
                    layout={ 'width': str(image_width)+'px' }
                )]

        self.images_vbox.children=images
        self.images_vbox.layout={
            'height': str(panel_height)+'px',
        }


def selections_labels_get(my_stats_m):
    selections_ref = [
        ['fs_max', 0, sorted],
        ['norm', 1, natsorted],
        ['fft_bin_size', 2, sorted],
        ['psd_method', 3, natsorted],
        ['normf', 4, natsorted],
    ]

    stats_tuples = np.array([key.split('_') for key in my_stats_m])

    selections = {}
    labels = {}
    for key, idx, fn in selections_ref:

        selections[key] = {
            value: ['_'.join(key) for key in stats_tuples[stats_tuples[:, idx] == value]
            ]
            for value in set(stats_tuples[:, idx])
        }
        
        my_sort = fn(set(stats_tuples[:, idx]))
        if 'none' in my_sort:
            my_sort.remove('none')
            my_sort = ['none'] + my_sort
            
        labels[key] = my_sort
        
    return selections, labels


class TableViewer:

    def __init__(self, stats_m):

        self.stats_m = stats_m
        self.selections, _ = selections_labels_get(self.stats_m)

        self.psd_method_select = widgets.ToggleButtons(
            options=[
                ('All', ''),
                ('Welch', 'welch'),
                ('Multitaper', 'multitaper')
            ],
            value='',
            description='PSD method',
        )

        self.grid = qgrid.show_grid(self.df_get(), precision=4)

        display(widgets.VBox([self.psd_method_select, self.grid]))
        self.psd_method_select.observe(self.grid_refresh, names='value')  

    def df_get(self):

        my_value = self.psd_method_select.value
        
        if my_value=='':
            stats_list = list(self.stats_m)
        else:
            stats_list = self.selections['psd_method'][my_value]
        
        stats_list = natsorted(stats_list)

        df = pd.DataFrame({
            'name': stats_list,
            'calinski_harabasz': [
                self.stats_m[item]['val_calinski_harabasz'] for item in stats_list
            ],
            'davies_bouldin': [
                self.stats_m[item]['val_davies_bouldin'] for item in stats_list
            ],
            'silhouette': [
                self.stats_m[item]['val_silhouette'] for item in stats_list
            ]
        })
        
        df.set_index('name', inplace=True)
        
        return df

    def grid_refresh(self, change):
        self.grid.df = self.df_get()


def rgb_to_rgba(color, alpha=1):

    return 'rgba'+color[3:-1]+', '+str(alpha)+')'


class MetricsViewer:

    def __init__(self, stats_m, figures_folder=None):

        self.stats_m = stats_m
        self.figures_folder = figures_folder
        self.selections, self.labels = selections_labels_get(self.stats_m)

        self.colors_ref = plotly.colors.DEFAULT_PLOTLY_COLORS

        self.my_metrics_ref = {
            'silhouette': 'Silhouette coefficient (higher better)',
            'val_silhouette': 'Silhouette coefficient (higher better) Validation',
            'calinski_harabasz': 'Calinski Harabasz index (higher better)',
            'val_calinski_harabasz': 'Calinski Harabasz index (higher better) Validation',
            'davies_bouldin': 'Davies Bouldin index (lower better)',
            'val_davies_bouldin': 'Davies Bouldin index (lower better) Validation'
        }

        self.my_metrics = [
            'silhouette',
            'val_silhouette',
            'calinski_harabasz',
            'val_calinski_harabasz',
            'davies_bouldin',
            'val_davies_bouldin'
        ]

        self.my_metrics_multi = [
            ['calinski_harabasz', 'davies_bouldin'],
            ['val_calinski_harabasz', 'val_davies_bouldin'],
            ['silhouette', 'davies_bouldin'],
            ['val_silhouette', 'val_davies_bouldin'],
            ['calinski_harabasz', 'silhouette'],
            ['val_calinski_harabasz', 'val_silhouette']
        ]

        self.params_select = widgets.ToggleButtons(
            options=[
                ('All', ''), 
                ('PSD method', 'psd_method'),         
                ('Fs max', 'fs_max'), 
                ('Norm time', 'norm'), 
                ('FFT bin size', 'fft_bin_size'), 
                ('Norm freq', 'normf')
            ],
            value='',
            description='Selection',
        )

        self.filter_select = widgets.ToggleButtons(
            options=[
                ('All', ''),
                ('Welch', 'welch'),
                ('Multitaper', 'multitaper')
            ],
            value='',
            description='Filter',
        )
        
        self.data = self.data_select()
        self.data_multi = self.data_select(multi=True)
        self.fig_widgets = self.plot_setup()
        self.fig_widgets_multi = self.plot_setup(multi=True)

        self.image_layout = {'width': str(850)+'px' }

        self.fig_widgets_combo = []
        self.fig_widgets_multi_combo = []
        for fig_widgets, fig_widgets_combo in [
            [self.fig_widgets, self.fig_widgets_combo],
            [self.fig_widgets_multi, self.fig_widgets_multi_combo]
        ]:
            for row_idx in range(int(len(fig_widgets)/2)):

                fig_widgets_combo += [
                    widgets.HBox(
                        [
                            fig_widgets[2*row_idx],
                            fig_widgets[2*row_idx+1],
                            # widgets.Image(
                            #     disabled=True,
                            #     layout=self.image_layout
                            # )
                        ], 
                        layout={'flex_flow':'row wrap'}
                    )
                ]

        display(widgets.VBox([self.params_select, self.filter_select]))
        display(widgets.VBox(self.fig_widgets_combo))
        display(widgets.VBox(self.fig_widgets_multi_combo))        
        self.params_select.observe(self.plot_refresh, names='value')
        self.filter_select.observe(self.plot_refresh, names='value')

    def plot_setup(self, multi=False):
        
        if multi:
            data = self.data_multi
        else:
            data = self.data

        plot_widgets = []
        for idx_data, (my_name, my_data) in enumerate(data):

            trace = []
            for my_idx, (my_label, my_x, my_y, my_text) in enumerate(my_data):

                color = rgb_to_rgba(self.colors_ref[my_idx], 0.5)
                trace += [go.Scatter(
                    x=my_x,
                    y=my_y,
                    mode='markers',
                    text=my_text,
                    marker={
                        'color': color,
                        'size': 10
                    },
                    name=my_label
                )]

            if multi:
                my_title = my_name[0].split(' (')[0] + ' vs ' + my_name[1].split(' (')[0]
                if 'Validation' in my_name[0]:
                    my_title += ' (Validation)'
                my_metric_x, my_metric_y = self.my_metrics_multi[idx_data]
                my_title_x = self.my_metrics_ref[my_metric_x].split(' Validation')[0]
                my_title_y = self.my_metrics_ref[my_metric_y].split(' Validation')[0]

            else:
                my_title = my_name.split(' (')[0]
                if 'Validation' in my_name:
                    my_title += ' (Validation)'
                my_title_x = 'Sorted params'
                my_title_y = my_name.split(' Validation')[0]

            layout = {
                'title': my_title,
                'hovermode': 'closest',
                'xaxis': {'title': my_title_x},
                'yaxis': {'title': my_title_y},
                'width': 500,
                'showlegend': True
            }

            plot_widgets += [go.FigureWidget(data=trace, layout=layout)]

        return plot_widgets

    def plot_refresh(self, change):
        
        self.data = self.data_select()
        self.data_multi = self.data_select(multi=True)

        for fig_widgets, data in [
            [self.fig_widgets, self.data],
            [self.fig_widgets_multi, self.data_multi]
        ]:
            for my_data_idx, (_, my_data) in enumerate(data):
                
                fig_widgets[my_data_idx].data = []
                for my_idx, (my_label, my_x, my_y, my_text) in enumerate(my_data):
                    
                    color = rgb_to_rgba(self.colors_ref[my_idx], 0.5)
                    fig_widgets[my_data_idx].add_trace(go.Scatter(
                        x=my_x,
                        y=my_y,
                        mode='markers',
                        text=my_text,
                        marker={
                            'color': color,
                            'size': 10
                        },
                        name=my_label
                    ))

    def data_filter(self):

        my_stats_list = list(self.stats_m)
        
        if self.params_select.value=='':
            my_stats_keys = {'All': my_stats_list}
            my_labels = ['All']
        else:
            my_stats_keys = self.selections[self.params_select.value].copy()
            my_labels = self.labels[self.params_select.value]
                
        if self.filter_select.value!='':
            for label in my_stats_keys:
                my_stats_keys[label] = [
                    key for key in my_stats_keys[label]
                    if key in self.selections['psd_method'][self.filter_select.value]
                ]
        return my_stats_list, my_stats_keys, my_labels

    def data_select(self, multi=False):
    
        my_stats_list, my_stats_keys, my_labels = self.data_filter()

        data = []
        if multi:

            for my_metric_x, my_metric_y in self.my_metrics_multi:

                my_name_x = self.my_metrics_ref[my_metric_x]
                my_name_y = self.my_metrics_ref[my_metric_y]
                my_name = (my_name_x, my_name_y)

                my_data = []
                for my_label in my_labels:

                    my_stats_label = [
                        key for key in my_stats_list 
                        if key in my_stats_keys[my_label]
                    ]

                    my_x = [
                        self.stats_m[key][my_metric_x] for key in my_stats_label 
                    ]
                    my_y = [
                        self.stats_m[key][my_metric_y] for key in my_stats_label 
                    ]
                    my_text = [key for key in my_stats_label]

                    my_data += [[my_label, my_x, my_y, my_text]]
                    
                data  += [[my_name, my_data]]

        else:

            for my_metric in self.my_metrics:

                my_name = self.my_metrics_ref[my_metric]

                idx_sort = np.argsort([
                    self.stats_m[key][my_metric] for key in my_stats_list
                ])
                if my_metric in ['davies_bouldin', 'val_davies_bouldin']:
                    idx_sort = idx_sort[::-1]

                my_stats_sorted = [my_stats_list[idx] for idx in idx_sort]
            
                my_data = []
                for my_label in my_labels:

                    my_x = [
                        idx_key for idx_key, key in enumerate(my_stats_sorted) 
                        if key in my_stats_keys[my_label]
                    ]
                    my_y = [
                        self.stats_m[key][my_metric] for key in my_stats_sorted 
                        if key in my_stats_keys[my_label]
                    ]
                    my_text = [
                        key for key in my_stats_sorted
                        if key in my_stats_keys[my_label]
                    ]

                    my_data += [[my_label, my_x, my_y, my_text]]
                    
                data  += [[my_name, my_data]]

        return data


class CacheLoader:

    def __init__(self, base_path):

        self.base_path = base_path
        self.stats_m = {}

        self.sources = {}
        for item in os.listdir(self.base_path):
            path = os.path.join(self.base_path, item)
            if os.path.isdir(path):

                files = mod_common_utils.list_cache(path)
                if files:
                    self.sources[path] = files

        self.source_select = widgets.Dropdown(
                options=['']+natsorted(self.sources),
                value='',
                description='Source'
            )
        self.source_out = widgets.Output()

        display(widgets.HBox([
            self.source_select, 
            self.source_out
        ]))
        self.source_select.observe(self.load_source, names='value')

        self.widgets = ([self.source_select])
            
    def load_source(self, change):
        
        if self.source_select.value!='':

            path = self.source_select.value
            self.stats_m = {}

            self.source_out.clear_output()
            with self.source_out:
                print('Loading...')
            
            for name in self.sources[path]:
                my_stats = mod_common_utils.from_cache(name, path)

                for key in my_stats:
                    self.stats_m[key] = my_stats[key]

            self.stats_m = mod_common_utils.stats_eval(self.stats_m)

            self.source_out.clear_output()
            with self.source_out:
                print('Loaded data from', path)