# olympus

Detector simulation suite

## Getting Started

This section tells you how to set up the package and be able to run with it.

### Prerequisites

This package has been optimised for python 3.10.

### Usage Installation

The package can be installed without prior steps using your package manager.

```console
foo@bar:project/$ poetry add git+https://github.com/pone-software/olympus.git@main
foo@bar:project/$ pip install git+https://github.com/pone-software/olympus.git@main
```

### Development Installation

This package is built and updated using [Poetry](https://python-poetry.org/).
Please install it and make yourself familiar if you never heard of it.

To develop the package, clone the repository first. Then install the virtual environment
of the package by calling the following console command.

```console
foo@bar:olympus/$ poetry install
```

You can afterwards enter the environment by 

```console
foo@bar:olympus/$ poetry shell
```

### Using Jax and Torch

As we do not know whether you have a gpu or which cuda/python version you have, you
should install jax and torch manually. To do that enter your environment. And then 
install jax and torch as given on the homepages:

* [JAX](https://jax.readthedocs.io/en/latest/installation.html)
* [PyTorch](https://pytorch.org/)

### Installing Proposal

Usually proposal should come preinstalled once you install the package. If there is
an error building the wheel, make sure you got `python3-dev` or your python versions
equivalent installed.

## Getting data

For some functions of the olympus package some predefined data is necessary. I, Janik,
created some sample data to get started. 
You can find them in the [Drive Folder](https://drive.google.com/drive/folders/1Wbf_uwZp3rscFjIf_L4ohwKoE-GEHV07?usp=share_link).

### Simulating Bioluminescence

To simulate bioluminescence you need the sample data for single modules generated by
Christian Haacks bioluminescence simulation in Julia.

* Raw Bioluminescense Files → biolumi_sims.tar.gz

### Using the Normal Flow Photon Propagation

This propagation only works for each module and not for individual PMTs. It uses
the `norm_flow_shape_model.pickle` and `norm_flow_counts_model.pickle` calculated by
Christian Haack.

* norm_flow_shape_model.pickle
* norm_flow_counts_model.pickle

### Simulation Data

With this framework there have been different datasets generated. Some of them can be
found in the `event_data` sub-folder:

* 30000 Cascades (incl. statistics)
* 100000 Bioluminescence intervals (incl. statistics)
* 100000 Electrical noise intervals (incl. statistics)
* Combined dataset featuring only cascades within 5-sigma of the noise counts

All the datasets have been generated for a single line detector.