# DeskOps

**A lightweight Linux system diagnostics desktop application.**

DeskOps is a desktop application designed to make system information and basic diagnostics accessible through a graphical interface.

Built with Python, PySide6, and psutil, the project aims to provide a straightforward way to monitor system resources and inspect running processes on Linux.

## Features

- **System Monitoring** — Overview of CPU and memory usage.
- **Process Monitoring** — View running processes and their resource usage.
- **System Diagnostics** — Run diagnostic checks through a graphical interface.
- **Desktop Integration** — Designed for Linux desktop environments.
- **Native Packaging** — Distributed as a Debian `.deb` package.

## Technology Stack

- Python
- PySide6 / Qt
- psutil
- Linux
- Debian packaging

## Installation

Download the latest `.deb` package from [GitHub Releases](https://github.com/carlosjuniorcj16-code/deskops/releases).

On Debian-based Linux distributions using the AMD64 architecture, install it with:

```bash
sudo apt install ./deskops_0.1.1_amd64.deb
```

Launch DeskOps from your application menu or run:

```bash
deskops
```

## Development

Clone the repository:

```bash
git clone https://github.com/carlosjuniorcj16-code/deskops.git
cd deskops
```

Create a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required dependencies and follow the project's development setup.

## Project Status

DeskOps is an early-stage project under active development. Features, interface elements, and diagnostic capabilities may change as development progresses.

Feedback, bug reports, and suggestions are welcome through GitHub Issues.

## Roadmap

- Customizable application settings
- More detailed diagnostic reports
- Improved system resource monitoring
- Interface and usability improvements
- Expanded Linux compatibility

## License

No open-source license has been declared yet. All rights reserved unless otherwise specified by the author.
