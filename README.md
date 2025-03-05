# SUSE Edge Components Versions

This tool retrieves version information for Helm charts, pods, and nodes in a SUSE Edge Kubernetes cluster.

## Features

* Retrieves Helm chart versions, namespaces, revisions, and resources.
* Retrieves pod versions (container images) for each Helm chart.
* Retrieves node information (architecture, kernel version, kubelet version, operating system, OS image).
* Outputs the information in JSON or table format.

## Usage

0.  **Prerequisites:**

    * python3
    * helm

    Ideally a virtualenv should be created:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

1.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the script:**

    ```bash
    python suse-edge-components-versions.py -k <kubeconfig_path> -c <chart_names> -o <output_format>
    ```

    * `-k`: Path to the kubeconfig file (optional). If not provided, defaults to `/kubeconfig`
    * `-c`: Comma-separated list of Helm chart names (optional). If not provided, defaults to `metallb, endpoint-copier-operator, 
                  rancher, longhorn, cdi,
                  kubevirt, neuvector, elemental-operator,
                  sriov-network-operator, akri, metal3 & rancher-turtles`.
    * `-o`: Output format: `json` (default) or `table`.
    * `--show-resources`: Include resources created by the helm chart in the output.
    * `-h`: Show help.

**Example:**

```bash
python suse-edge-components-versions.py -k /path/to/kubeconfig -c cert-manager,metallb -o table
```

## Container

A Dockerfile is provided to build a containerized version of the tool.

**Build the image:**

```bash
podman build -t suse-edge-components-versions .
```

**Run the container:**

```bash
podman run -v /path/to/your/kubeconfig:/kubeconfig suse-edge-components-versions -c <chart_names>
```

*NOTE:* Just in case, there is a prebuilt image available at `ghcr.io/e-minguez/suse-edge-components-versions:main` (`linux/amd64` & `linux/arm64` compatible).

```bash
podman run -v /path/to/your/kubeconfig:/kubeconfig ghcr.io/e-minguez/suse-edge-components-versions:main -c <chart_names>
```

## Example output

* Json

```bash
{
  "helm_charts": {
    "endpoint-copier-operator": {
      "version": "302.0.0+up0.2.1",
      "namespace": "endpoint-copier-operator",
      "revision": 1,
      "pods": {
        "endpoint-copier-operator-7bf97b9d45-7v8fp": [
          "registry.suse.com/edge/3.2/endpoint-copier-operator:0.2.0"
        ],
        "endpoint-copier-operator-7bf97b9d45-p8m9k": [
          "registry.suse.com/edge/3.2/endpoint-copier-operator:0.2.0"
        ]
      }
    },
    "metallb": {
      "version": "302.0.0+up0.14.9",
      "namespace": "metallb-system",
      "revision": 1,
      "pods": {
        "metallb-controller-5756c8898-g2mgk": [
          "registry.suse.com/edge/3.2/metallb-controller:v0.14.8"
        ],
        "metallb-speaker-9ltj7": [
          "registry.suse.com/edge/3.2/metallb-speaker:v0.14.8"
        ]
      }
    }
  },
  "nodes": {
    "vm1": {
      "architecture": "arm64",
      "kernelVersion": "6.4.0-18-default",
      "kubeletVersion": "v1.31.3+rke2r1",
      "operatingSystem": "linux",
      "osImage": "SUSE Linux Micro 6.0"
    }
  }
}
```

* Table

```
Release: endpoint-copier-operator
+-----------+--------------------------+
| Version   | 302.0.0+up0.2.1          |
+-----------+--------------------------+
| Namespace | endpoint-copier-operator |
+-----------+--------------------------+
| Revision  | 1                        |
+-----------+--------------------------+

  Pods:
+-------------------------------------------+-----------------------------------------------------------+
| Pod Name                                  | Images                                                    |
+===========================================+===========================================================+
| endpoint-copier-operator-7bf97b9d45-7v8fp | registry.suse.com/edge/3.2/endpoint-copier-operator:0.2.0 |
+-------------------------------------------+-----------------------------------------------------------+
| endpoint-copier-operator-7bf97b9d45-p8m9k | registry.suse.com/edge/3.2/endpoint-copier-operator:0.2.0 |
+-------------------------------------------+-----------------------------------------------------------+

Release: metallb
+-----------+------------------+
| Version   | 302.0.0+up0.14.9 |
+-----------+------------------+
| Namespace | metallb-system   |
+-----------+------------------+
| Revision  | 1                |
+-----------+------------------+

  Pods:
+------------------------------------+-------------------------------------------------------+
| Pod Name                           | Images                                                |
+====================================+=======================================================+
| metallb-controller-5756c8898-g2mgk | registry.suse.com/edge/3.2/metallb-controller:v0.14.8 |
+------------------------------------+-------------------------------------------------------+
| metallb-speaker-9ltj7              | registry.suse.com/edge/3.2/metallb-speaker:v0.14.8    |
+------------------------------------+-------------------------------------------------------+

Node Information:
+--------+----------------+------------------+-------------------+--------------------+----------------------+
| Node   | Architecture   | Kernel Version   | Kubelet Version   | Operating System   | OS Image             |
+========+================+==================+===================+====================+======================+
| vm1    | arm64          | 6.4.0-18-default | v1.31.3+rke2r1    | linux              | SUSE Linux Micro 6.0 |
+--------+----------------+------------------+-------------------+--------------------+----------------------+
```

## GitHub Actions

A GitHub Actions workflow is included to automatically build and push the Docker image to the GitHub Container Registry on every push to the main branch.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for more details.