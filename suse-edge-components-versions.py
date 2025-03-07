#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
from argparse import ArgumentParser
from typing import Any, Dict, List

from kubernetes import client, config
from pyhelm3 import Client, Command
from tabulate import tabulate

# Configure logging
logging.basicConfig(level=logging.WARN,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Default chart names
DEFAULT_CHARTS = ["cdi",
                  "elemental-operator",
                  "endpoint-copier-operator",
                  "kubevirt",
                  "longhorn",
                  "metal3",
                  "metallb",
                  "neuvector",
                  "rancher",
                  "rancher-turtles",
                  "sriov-network-operator",
                  "system-upgrade-controller",
                  "upgrade-controller"]

CHARTS_AND_PRODUCTS = {"longhorn": ["SUSE Storage","Longhorn"],
                       "metal3": ["Metal3"],
                       "metallb": ["MetalLB"],
                       "endpoint-copier-operator": ["Endpoint Copier Operator"],
                       "elemental-operator": ["Elemental"],
                       "rancher": ["SUSE Rancher Prime","Rancher Prime"],
                       "cdi": ["Containerized Data Importer"],
                       "kubevirt": ["KubeVirt"],
                       "neuvector": ["SUSE Security","NeuVector"],
                       "sriov-network-operator": ["SR-IOV Network Operator"],
                       "akri": ["Akri (tech-preview)"],
                       "rancher-turtles": ["Rancher Turtles (CAPI)"],
                       "system-upgrade-controller": ["System Upgrade Controller"],
                       "upgrade-controller": ["Upgrade Controller"]}


async def get_helm_chart_info(kubeconfig_path: str,
                              chart_names: List[str],
                              get_resources: bool) -> Dict:
    """
    Retrieves specific Helm chart information using pyhelm3.
    """
    chart_info = {}
    try:
        helm = Client(kubeconfig=kubeconfig_path)
        releases = await helm.list_releases(all_namespaces=True)

        for release in releases:
            if release.name in chart_names:
                revision = await release.current_revision()
                if revision is not None:  # Check if revision is not None
                    chart_metadata = await revision.chart_metadata()
                    if chart_metadata is not None:  # Check if chart_metadata is not None
                        chart_info[release.name] = {
                            "version": f"{chart_metadata.version}",
                            "namespace": release.namespace,
                            "revision": revision.revision,
                            "resources": [],
                            "pods": {}
                        }
                        if get_resources:
                            command = Command(kubeconfig=kubeconfig_path)
                            resources = await command.get_resources(
                                release_name=release.name,
                                namespace=release.namespace)
                            if resources is not None:  # Check if resources is not None
                                for resource in resources:
                                    if resource is not None and isinstance(resource, dict) and 'kind' in resource and 'metadata' in resource and 'name' in resource['metadata']:
                                        chart_info[release.name]["resources"].append({
                                            "kind": resource['kind'],
                                            "name": resource['metadata']['name']
                                        })
                                    else:
                                        logging.warning(
                                            f"Skipping invalid resource: {resource}")

                        # Get pod names and versions on the target namespace of the helm chart
                        # This should match the pods deployed by the chart in most of the cases
                        pods_info = get_pod_versions_by_namespace(
                            kubeconfig_path, release.namespace)
                        if pods_info is not None:  # Check if pods_info is not None
                            chart_info[release.name]["pods"] = pods_info

        return chart_info

    except Exception as e:
        logging.error(f"Error retrieving Helm chart information: {e}")
        return {}


def get_pod_versions_by_namespace(kubeconfig_path: str,
                                  namespace: str) -> Dict:
    """
    Retrieves pod image versions in a namespace.

    Args:
        kubeconfig_path: Path to the kubeconfig file.
        namespace: The namespace where the pods are located.

    Returns:
        A dictionary containing pod names as keys and lists of image versions as values.
    """
    try:
        config.load_kube_config(config_file=kubeconfig_path)
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace)
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
        choices=["json", "table", "none"],
        help="Output format: json (default), table or none",
    )
    parser.add_argument("--get-resources",
                        action="store_true",
                        help="Include resources in the output")

    args = parser.parse_args()

    kubeconfig_path = args.kubeconfig if args.kubeconfig else "/kubeconfig"
    output_format = args.output
    get_resources = args.get_resources

    chart_names = [
        name.strip() for name in args.charts.split(",")
    ] if args.charts is not None else DEFAULT_CHARTS

    # Check if kubeconfig file exists
    if not os.path.exists(kubeconfig_path):
        logging.error(f"Error: Kubeconfig file not found at {kubeconfig_path}")
        sys.exit(1)

    helm_info = await get_helm_chart_info(kubeconfig_path, chart_names, get_resources)
    node_info = get_node_info(kubeconfig_path)

    edge_version = check_edge_version(node_info, helm_info)

    if output_format == "json":
        output_data = {"helm_charts": helm_info,
                       "nodes": node_info, "detected_edge_version": edge_version}
        if not get_resources:
            for chart_data in output_data["helm_charts"].values():
                chart_data.pop("resources", None)
        print(json.dumps(output_data, indent=2))
    elif output_format == "table":
        print_table_output(helm_info, node_info, edge_version, get_resources)
    elif output_format == "none":
        print(f"SUSE Edge detected version: {edge_version}")


def print_table_output(helm_info: Dict, node_info: Dict, edge_version: Dict, get_resources: bool):
    """
    Prints the cluster information in a table format.

    Args:
        helm_info: Dictionary containing Helm chart information.
        node_info: Dictionary containing node information.
        edge_version: Dictionary with the detected SUSE Edge version
        get_resources: Whether to get (and print) resources.
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

        if get_resources:
            # Resources table
            print("\n  Resources:")
            resources_table_data = []
            for resource in info["resources"]:
                resources_table_data.append(
                    [resource["kind"], resource["name"]])
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

    # Edge version
    print(f"\nSUSE Edge detected version: {edge_version['release']}")

    if edge_version['items_matching'] != {}:
        matching = edge_version['items_matching']
        matching_table_data = []
        for k, v in matching.items():
            matching_table_data.append([k, v])
        print(f"\nSUSE Edge items matching:")
        print(tabulate(matching_table_data, headers=["Component", "Version"],
                       tablefmt="grid",
                       numalign="left",
                       stralign="left"))

    if edge_version['items_not_matching'] != {}:
        notmatching = edge_version['items_not_matching']
        notmatching_table_data = []
        for k, v in notmatching.items():
            notmatching_table_data.append([k, v])
        print(f"\nSUSE Edge items NOT matching:")
        print(tabulate(notmatching_table_data, headers=["Component", "Version"],
                       tablefmt="grid",
                       numalign="left",
                       stralign="left"))


def check_edge_version(node_info, helm_info):
    # Check for same versions on all the hosts
    kubelet_versions = set(node["kubeletVersion"]
                           for node in node_info.values())
    # Get the first one of the set
    kubelet_version = list(kubelet_versions)[0]
    # If the set is >1
    if len(kubelet_versions) != 1:
        print(
            f"Kubelet Versions mismatch! {kubelet_versions}, using {kubelet_version} as reference")
    # Try to match the distro
    # kube_distro = re.search(r"\+(k3s|rke2)r\d+", kubelet_version).group(1)
    # And version
    kube_version = kubelet_version.split("+")[0].split("v")[1]

    # Do the same for osImage
    os_images = set(node["osImage"] for node in node_info.values())
    os_image = list(os_images)[0]
    if len(os_images) != 1:
        print(
            f"Node osImage mismatch! {os_images}, using {os_image} as reference")

    # And kernel version
    kernel_versions = set(node["kernelVersion"] for node in node_info.values())
    kernel_version = list(kernel_versions)[0]
    if len(kernel_versions) != 1:
        print(
            f"Node kernel mismatch! {kernel_versions}, using {kernel_version} as reference")

    # Make pylint happy
    edge_version: Dict[str, Any] = {}
    matches = {}
    notmatches = {}
    # Try to match the edge version with each one of the released versions
    for filename in os.listdir("edge-versions"):
        if filename.endswith(".json"):
            filepath = os.path.join("edge-versions", filename)
            try:
                with open(filepath, 'r') as f:
                    release_data = json.load(f)

                k3s_version = (release_data['Data']['K3s']['Version'])
                rke2_version = (release_data['Data']['RKE2']['Version'])

                if (k3s_version or rke2_version) == kube_version:
                    # Kube version matches
                    matches['kubeversion'] = kubelet_version
                    # Time to check the helm charts
                    for name, info in helm_info.items():
                        # This is required because chart name != product name
                        chart_name = sanitize_chart_name(name,release_data['Data'])
                        # Skip charts not found
                        if chart_name:
                            chart_version = info['version']
                            release_version = release_data['Data'][chart_name]['Helm Chart Version']
                            if release_version == chart_version:
                                matches[name] = chart_version
                            else:
                                notmatches[name] = chart_version
                    if notmatches == {}:
                        # Everything matches
                        edge_version = {"release":
                                        release_data['Version']}
                    elif matches == {}:
                        # Nothing matches
                        edge_version = {"relaese":
                                        "Unknown"}
                    else:
                        # Not everything matches
                        edge_version = {"release":
                                        f"Posible {release_data['Version']}"}

                    edge_version["items_matching"] = matches
                    edge_version["items_not_matching"] = notmatches
                    return edge_version

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in {filename}: {e}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    return {"release": "unknown"}


def sanitize_chart_name(chart_name,data):
    candidates=CHARTS_AND_PRODUCTS[chart_name]
    if len(candidates) > 1:
        for candidate in candidates:
            if candidate in data:
                return candidate
    else:
        return candidates[0]


if __name__ == "__main__":
    asyncio.run(main())
