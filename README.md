# Unikraft-Eval

## Unikraft
Unikraft is a fast, secure and open-source Unikernel Development Kit which enables you to build custom, minimal, immutable ultra-lightweight unikernel virtual machines quickly and easily.


## Kraft and Unikraft
### What is Kraft?
Kraft Unikraft is an open-source Unikernel Development Kit, not a food product. It's a tool for building custom, lightweight virtual machines (unikernels) tailored for cloud-native applications. Unikernels are designed to be faster and more secure than traditional virtual machines or containers. 

### Setting up your environment for using the companion tool Kraft.
After installing kraft, you need to make sure you have also Docker installed and running on your machine in order to use Kraftkit, because Kraft utilizes Docker    
and BuildKit to generate the root filesystem needed for the unikernel.The kraft command-line tool relies on the Docker/OCI container environment to build and package the unikernel, making Docker a core requirement. 

To not encounter issues when KraftKit tries to access a running BuildKit instance in the process of building the root filesystem do:

        1. docker run --rm -d --name buildkit --privileged moby/buildkit:v0.20.0
Then export the environment variable so kraft knows where to find it:

        2. export KRAFTKIT_BUILDKIT_HOST=docker-container://buildkit

## Directory Structure
```text
|--------liux_scripts\
|                     |----fibonacci\
|                     |              |---fibonacci.c
|                     |----memcached\
|                     |             |---benchmark.py
|                     |             |---benchmarks.bash
|                     |             |---memcached.py
|                     |             |---qemu.bash
|                     |-------nginx\
|                                   |---benchmark.py
|                                   |---nginx.py
|                                   |---qemu.bash                                  |
|-------nginx_manual\
|                    |----nginx.zip
|                    |----.config   
|                    |----Makefile
|                    |----qemu-x64_64-9pfs
|                    |----start_nginx.sh  
|
|-------results-----\
|                    |----fibonacci\
|                    |              |...
|                    |----memcached\
|                    |              |...
|                    |----nginx\
|                    |              |...
|                    |----nginx_manual\
|                    |              |...
|                    |----plotting_scripts\
|                    |              |...
|
|-------ubuntu_minimal_cloud_image\
|                                  |----meta-data
|                                  |----seed_iso_cloud_image.bash
|                                  |----user_data
|
|-------Unikraft_scripts\
|                        |----fibonacci\
|                        |              |...
|                        |----memcached\
|                        |              |...
|                        |----nginx\
|                        |          |...
|-------kraft_run.bash
|-------READMNE.md

```


## Evaluation Goals

The goal of this project is to investigate the performance of applications running on the Unikraft unikernel. The project involves selecting applications of varying code complexities and functionalities (e.g., web servers, machine learning inference models, or network utilities), adapt them to run on the Unikraft unikernel, and evaluate their performance and the usability of Unikraft compared to traditional operating system environments.The performance metrics should include startup time, memory footprint, and execution speed for each application. For usability analysis, emphasis should be on handling system calls, I/O, and network communication and the porting effort. In addition, any challenges encountered during this analysis are documented along with resolution strategies.

## Aimed apps for testing
    1- Nginx  natively build and with kraft
    2- C/C++ application
    3- Memcached

## Setting up environment for running benchmarks on Linux
### Memcached (If memtier_benchmark is not available by default on your Linux distribution)
        1- sudo apt update
        2- sudo apt install build-essential autoconf automake libtool pkg-config libevent-dev git
        3- git clone https://github.com/RedisLabs/memtier_benchmark.git
        4- cd memtier_benchmark
        5- autoreconf -ivf
        6- ./configure
        7- make
        8- sudo make install
