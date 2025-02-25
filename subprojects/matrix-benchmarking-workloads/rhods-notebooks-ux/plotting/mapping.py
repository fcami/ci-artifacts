from collections import defaultdict
import re

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    MappingTimeline("Pod/Node timeline: Test Pods", is_notebook=False)
    MappingTimeline("Pod/Node timeline: Notebooks", is_notebook=True)

    MappingDistribution("Pod/Node distribution: Test Pods", is_notebook=False)
    MappingDistribution("Pod/Node distribution: Notebooks", is_notebook=True)

def generate_data(entry, cfg, is_notebook, force_order_by_user_idx=False):
    test_nodes = {}
    entry_results = entry.results

    if is_notebook:
        hostnames = entry_results.notebook_hostnames
        pods = entry_results.notebook_pods
    else:
        hostnames = entry_results.testpod_hostnames
        pods = entry_results.test_pods

    hostnames_index = list(hostnames.values()).index

    data = []

    if force_order_by_user_idx:
        for user_idx in range(entry.results.user_count):
            data.append(dict(
                UserIndex = f"User #{user_idx:03d}",
                UserIdx = user_idx,
                PodStart = entry_results.tester_job.creation_time,
                PodFinish = entry_results.tester_job.creation_time,
                NodeIndex = f"Not mapped",
                NodeName = f"Not mapped",
                Count=0,
            ))

    for pod_name in pods:
        if is_notebook:
            user_idx = int(re.findall(r'[:letter:]*(\d+)$', pod_name)[0])
        else:
            user_idx = int(pod_name.split("-")[2])

        try: pod_times = entry_results.pod_times[pod_name]
        except KeyError: continue

        try:
            hostname = hostnames[pod_name]
        except KeyError:
            data.append(dict(
                UserIndex = f"User #{user_idx:03d}",
                UserIdx = user_idx,
                PodStart = entry_results.tester_job.creation_time,
                PodFinish = entry_results.tester_job.completion_time,
                NodeIndex = f"No node",
                NodeName = f"No node",
                Count=1,
            ))
            continue

        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "")
        try:
            finish = pod_times.container_finished
        except AttributeError:
            finish = entry_results.tester_job.completion_time

        try:
            instance_type = entry.results.nodes_info[hostname].instance_type
        except AttributeError:
            instance_type = ""

        data.append(dict(
            UserIndex = f"User #{user_idx:03d}",
            UserIdx = user_idx,
            PodStart = pod_times.start_time,
            PodFinish = finish,
            NodeIndex = f"Node {hostnames_index(hostname)}",
            NodeName = f"Node {hostnames_index(hostname)}<br>{shortname}<br>{instance_type}",
            Count=1,
        ))

    return data

class MappingTimeline():
    def __init__(self, name, is_notebook):
        self.name = name
        self.id_name = name
        self.is_notebook = is_notebook

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if sum(1 for _ in common.Matrix.all_records(settings, setting_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__force_order_by_user_idx = cfg.get("force_order_by_user_idx", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg, self.is_notebook,
                                            force_order_by_user_idx=cfg__force_order_by_user_idx))

        if df.empty:
            return None, "Not data available ..."

        fig = px.timeline(df, x_start="PodStart", x_end="PodFinish", y="UserIndex", color="NodeIndex")
        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Mapping of the {'Notebook' if self.is_notebook else 'Test'} Pods on the nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""

class MappingDistribution():
    def __init__(self, name, is_notebook):
        self.name = name
        self.id_name = name
        self.is_notebook = is_notebook

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if sum(1 for _ in common.Matrix.all_records(settings, setting_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg, self.is_notebook))

        if df.empty:
            return None, "Nothing to plot (no data)"

        # sort by UserIndex to improve readability
        df = df.sort_values(by=["UserIndex"])

        fig = px.bar(df, x="NodeName", y="Count", color="UserIdx",
                     title=f"Distribution of the {'Notebook' if self.is_notebook else 'Test'} Pods on the nodes")

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Pod count")
        fig.update_yaxes(tick0=0, dtick=1)
        return fig, ""
