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
    * `-c`: Comma-separated list of Helm chart names (optional). If not provided, defaults to `metallb,endpoint-copier-operator`.
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

*NOTE:* Just in case, there is a prebuilt image available at `ghcr.io/e-minguez/suse-edge-components-versions:main`

```bash
podman run -v /path/to/your/kubeconfig:/kubeconfig ghcr.io/e-minguez/suse-edge-components-versions:main -c <chart_names>
```

## GitHub Actions

A GitHub Actions workflow is included to automatically build and push the Docker image to the GitHub Container Registry on every push to the main branch.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for more details.