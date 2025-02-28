#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
from argparse import ArgumentParser
from typing import Dict, List

from kubernetes import client, config
from pyhelm3 import Client, Command
from tabulate import tabulate

# Configure logging
logging.basicConfig(level=logging.WARN,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Default chart names
DEFAULT_CHARTS = ["metallb", "endpoint-copier-operator"]


async def get_helm_chart_info(kubeconfig_path: str,
                             chart_names: List[str]) -> Dict:
    """
    Retrieves specific Helm chart information using pyhelm3.

    Args:
        kubeconfig_path: Path to the kubeconfig file.
        chart_names: List of Helm chart names.

    Returns:
        A dictionary containing Helm chart information.
    """
    chart_info = {}
    try:
        helm = Client(kubeconfig=kubeconfig_path)
        releases = await helm.list_releases(all_namespaces=True)

        for release in releases:
            if release.name in chart_names:
                revision = await release.current_revision()
                chart_metadata = await revision.chart_metadata()
                chart_info[release.name] = {
                    "version": f"{chart_metadata.version}",
                    "namespace": release.namespace,
                    "revision": revision.revision,
                    "resources": [],
                    "pods": {}
                }
                # Create a Command object to get the resources
                command = Command(kubeconfig=kubeconfig_path)
                resources = await command.get_resources(
                    release_name=release.name, namespace=release.namespace)
                for resource in resources:
                    # Append resource as a dictionary
                    chart_info[release.name]["resources"].append({
                        "kind": resource['kind'],
                        "name": resource['metadata']['name']
                    })

                # Get pod versions for the current Helm chart
                label_selector = f"app.kubernetes.io/instance={release.name}"
                chart_info[release.name][
                    "pods"] = get_pod_versions_by_label(kubeconfig_path,
                                                       release.namespace,
                                                       label_selector)

        return chart_info

    except Exception as e:
        logging.error(f"Error retrieving Helm chart information: {e}")
        return {}


def get_pod_versions_by_label(kubeconfig_path: str,
                               namespace: str,
                               label_selector: str) -> Dict:
    """
    Retrieves pod image versions in a namespace based on a label selector.

    Args:
        kubeconfig_path: Path to the kubeconfig file.
        namespace: The namespace where the pods are located.
        label_selector: The label selector to filter pods.

    Returns:
        A dictionary containing pod names as keys and lists of image versions as values.
    """
    try:
        config.load_kube_config(config_file=kubeconfig_path)
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
        pod_versions = {}
        for pod in pods.items:
            pod_name = pod.metadata.name
            image_versions = []
            for container in pod.spec.containers:
                image_versions.append(container.image)
            pod_versions[pod_name] = image_versions
        return pod_versions

    except Exception as e:
        logging.error(f"Error retrieving pod versions: {e}")
        return {}


def get_node_info(kubeconfig_path: str) -> Dict:
    """
    Retrieves node information (architecture, kernelVersion, kubeletVersion, operatingSystem, osImage).

    Args:
        kubeconfig_path: Path to the kubeconfig file.

    Returns:
        A dictionary containing node names as keys and node information dictionaries as values.
    """
    try:
        config.load_kube_config(config_file=kubeconfig_path)
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        node_info = {}
        for node in nodes.items:
            node_info[node.metadata.name] = {
                "architecture": node.status.node_info.architecture,
                "kernelVersion": node.status.node_info.kernel_version,
                "kubeletVersion": node.status.node_info.kubelet_version,
                "operatingSystem": node.status.node_info.operating_system,
                "osImage": node.status.node_info.os_image,
            }
        return node_info

    except Exception as e:
        logging.error(f"Error retrieving node information: {e}")
        return {}


async def main():
    parser = ArgumentParser(description="Get Helm chart and pod versions.")
    parser.add_argument("-k",
                        "--kubeconfig",
                        help="Path to the kubeconfig file.")
    parser.add_argument("-c",
                        "--charts",
                        help="Comma-separated list of Helm chart names.")
    parser.add_argument(
        "-o",
        "--output",
        default="json",
        choices=["json", "table"],
        help="Output format: json (default) or table",
    )
    parser.add_argument("--show-resources",
                        action="store_true",
                        help="Include resources in the output")

    args = parser.parse_args()

    kubeconfig_path = args.kubeconfig if args.kubeconfig else "/kubeconfig"
    output_format = args.output
    show_resources = args.show_resources

    chart_names = [
        name.strip() for name in args.charts.split(",")
    ] if args.charts is not None else DEFAULT_CHARTS

    # Check if kubeconfig file exists
    if not os.path.exists(kubeconfig_path):
        logging.error(f"Error: Kubeconfig file not found at {kubeconfig_path}")
        sys.exit(1)

    helm_info = await get_helm_chart_info(kubeconfig_path, chart_names)
    node_info = get_node_info(kubeconfig_path)

    if output_format == "json":
        output_data = {"helm_charts": helm_info, "nodes": node_info}
        if not show_resources:
            for chart_data in output_data["helm_charts"].values():
                chart_data.pop("resources", None)
        print(json.dumps(output_data, indent=2))
    elif output_format == "table":
        print_table_output(helm_info, node_info, show_resources)


def print_table_output(helm_info: Dict, node_info: Dict, show_resources: bool):
    """
    Prints the cluster information in a table format.

    Args:
        helm_info: Dictionary containing Helm chart information.
        node_info: Dictionary containing node information.
        show_resources: Whether to include resources in the output.
    """

    # Helm chart information
    for release_name, info in helm_info.items():
        print(f"\nRelease: {release_name}")

        # Helm Chart Table
        chart_table_data = [
            ["Version", info['version']],
            ["Namespace", info['namespace']],
            ["Revision", info['revision']]
        ]
        print(tabulate(chart_table_data,
                      tablefmt="grid",
                      numalign="left",
                      stralign="left"))

        if show_resources:
            # Resources table
            print("\n  Resources:")
            resources_table_data = []
            for resource in info["resources"]:
                resources_table_data.append([resource["kind"], resource["name"]])
            print(
                tabulate(resources_table_data,
                          headers=["Kind", "Name"],
                          tablefmt="grid",
                          numalign="left",
                          stralign="left"))

        # Pods table
        print("\n  Pods:")
        pods_table_data = []
        for pod_name, images in info["pods"].items():
            pods_table_data.append([pod_name, ", ".join(images)])
        print(tabulate(pods_table_data,
                      headers=["Pod Name", "Images"],
                      tablefmt="grid",
                      numalign="left",
                      stralign="left"))

    # Node information
    print("\nNode Information:")
    node_table_data = []
    for node_name, info in node_info.items():
        node_table_data.append([
            node_name, info["architecture"], info["kernelVersion"],
            info["kubeletVersion"], info["operatingSystem"], info["osImage"]
        ])
    print(tabulate(node_table_data,
                  headers=[
                      "Node", "Architecture", "Kernel Version",
                      "Kubelet Version", "Operating System", "OS Image"
                  ],
                  tablefmt="grid",
                  numalign="left",
                  stralign="left"))


if __name__ == "__main__":
    asyncio.run(main())