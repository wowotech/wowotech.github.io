---
title: "Linux CPU core的电源管理(2)_cpu topology"
date: 2015-05-30T21:58:55+08:00
url: "/pm_subsystem/cpu_topology.html"
gid: "191"
emlog_type: "blog"
summary: "在“ Linux CPU core的电源管理(1)_概述 ”中，我们多次提到SMP、CPU core等概念，虽然硬着头皮写下去了，但是蜗蜗对这些概念总有些似懂非懂的感觉。它们和CPU的进化过程息息相关，最终会体现在CPU topology（拓扑结构）上。因此本文将以CPU topology为主线，介绍CPU有关（主要以ARM CPU为例）的知识。 另外，CPU topology除了描述CPU的组成"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["SMP", "cpu", "topology", "SMT", "NUMA"]
views: 39500
comment_count: 23
aliases:
  - "/pm_subsystem/191.html"
  - "/191.html"
---

#### 1. 前言

在“[Linux CPU core的电源管理(1)\_概述](/pm_subsystem/cpu_core_pm_overview.html)”中，我们多次提到SMP、CPU core等概念，虽然硬着头皮写下去了，但是蜗蜗对这些概念总有些似懂非懂的感觉。它们和CPU的进化过程息息相关，最终会体现在CPU topology（拓扑结构）上。因此本文将以CPU topology为主线，介绍CPU有关（主要以ARM CPU为例）的知识。

另外，CPU topology除了描述CPU的组成之外，其主要功能，是向kernel调度器提供必要的信息，以便让它合理地分配任务，最终达到性能和功耗之间的平衡。这也是我将“cpu topology”归类为“[电源管理子系统](/sort/pm_subsystem)”的原因。

#### 2. CPU topology

**2.1 一个例子**

开始之前，先看一个例子，下面是蜗蜗所使用的编译服务器的CPU architecture信息：

> [xxx@cs ~]# lscpu
>
> Architecture: x86\_64   
> CPU op-mode(s): 32-bit, 64-bit   
> Byte Order: Little Endian   
> CPU(s): 24  
> On-line CPU(s) list: 0-23   
> Thread(s) per core: 2   
> Core(s) per socket: 6   
> Socket(s): 2   
> NUMA node(s): 2   
> Vendor ID: GenuineIntel   
> CPU family: 6   
> Model: 62   
> Stepping: 4   
> CPU MHz: 2100.118   
> BogoMIPS: 4199.92   
> Virtualization: VT-x   
> L1d cache: 32K   
> L1i cache: 32K   
> L2 cache: 256K   
> L3 cache: 15360K   
> NUMA node0 CPU(s): 0,2,4,6,8,10,12,14,16,18,20,22   
> NUMA node1 CPU(s): 1,3,5,7,9,11,13,15,17,19,21,23

注意其中蓝色字体部分，该服务器有24个CPU，组成方式是：2个sockets，每个socket有6个core，每个core有2个thread。另外，这些CPU可以划分为2个NUMA node。晕吧，知道我在说什么吗？不知道就对了，让我做进一步的解释。

**2.2 单核和多核**

在英文里面，单核（single-core）和多核（multi-core）多称作uniprocessor和multiprocessor，这里先对这些概念做一个说明：

> 这里所说的core（或processor），是一个泛指，是从使用者（或消费者）的角度看计算机系统。因此，core，或者processor，或者处理器（CPU），都是逻辑概念，指的是一个可以独立运算、处理的核心。
>
> 而这个核心，可以以任何形式存在，例如：单独的一个chip（如通常意义上的单核处理器）；一个chip上集成多个核心（如SMP，symmetric multiprocessing）；一个核心上实现多个hardware context，以支持多线程（如SMT，Simultaneous multithreading）；等等。这是从硬件实现的角度看的。
>
> 最后，从操作系统进程调度的角度，又会统一看待这些不同硬件实现的核心，例如2.1中所提及的CPU（24个CPUs），因为它们都有一个共同的特点：执行进程（或线程）。

在传统的单核时代，提升处理器性能的唯一手段就是提高频率。但受限于物理工艺，频率不能无限提高（例如散热问题等）。对多核处理器来说，可利用的空间增多，散热问题就比较容易解决。这就是multiprocessor诞生的背景。

另外，现实中的多任务需求，也是multiprocessor得以发展的基础，例如智能手机中，可以使用一个processor处理通信协议，另一个processor处理UI交互、多媒体等，这可以让用户在享受“智能”的同时，确保不miss基础的通信需求。

**2.3 SMP、SMT、NUMA等概念**

比较常见的multiprocessor实现，是将多个功能完全相同的processor集成在一起（可以在一个chip上，也可以在多个chip），它们共享总线、memory等系统资源，这称作SMP（Symmetric Multi-Processing），如下面图片中的CORE000、CORE001…。从Linux kernel的角度，通常称这些功能独立的process为Core。

另外，基于制程、扩充性等考虑，芯片厂商会把多个Core封装在一个chip上，这也称作Socket。Socket的概念在X86架构上使用尤其多，可以理解为插槽。假设一个插槽有两个Core，那么我在主板上插2个插槽，就是4核系统，插4个插槽，就是8核系统。不过Socket在ARM体系结构上使用却比较少，后面我们会介绍另外一个类似概念（Cluster）。

大多数操作系统（如Windows、Linux），有进程和线程的概念。进程是程序的运行实例，可以包括很多线程。线程是调度的最小单位。因此有些处理器（Core），可以通过复制硬件寄存器状态等手段，同时执行多个线程，这叫做SMT（Simultanous Multi-Thread）。

下面图片以及2.1中的例子，反映了多核系统的简单topology。

[![mc_support](/content/uploadfile/201505/12de6758c818a304c3552dba6b3ddced20150530135850.gif "mc_support")](/content/uploadfile/201505/8b44b18608d5f29ebb7b151da6cebde420150530135848.gif)

前面讲过，Core之间会共享总线、memory等资源。如果Core的数量较少，则没什么问题，但随着Core的增多，对总线以及memory带宽的需求就会显著增大，最终总线和memory会成为系统性能的瓶颈。解决方法是：

> 某些Core之间，独享总线和memory，称作Node。正常情况下，Core只访问Node内的memory，因此可以减轻对总线和memory的带宽需求。但是，有些场景下，Core会不可避免的访问其它Node的memory，这会造成很大的访问延迟。
>
> 因此，这种技术称作NUMA（Non-uniform Memory Access），以内存访问的不一致性为代价，减轻对总线和memory的带宽需求。这种结构对进程调度算法的要求较高，尽量减少跨Node的内存访问次数，以提升系统性能。

**2.4 ARM HMP（Heterogeneous Multi-Processing）**

前面提到的拓扑结构，大多存在于X86架构的PC、服务器上，唯一目标就是提升CPU的处理性能（不在乎功耗）。但在移动市场（大多是ARM的天下），事情就复杂多了。

随着智能设备的普及，用户对移动设备的性能需求越来越高，相应的就更多有的power消耗，这对设备的电源管理以及散热处理提出了更高的要求。与此同时，电池技术却没有随着CPU拓扑结构的进化而进化，这就导致上述的拓扑结构不太适合对功耗特别敏感的移动设备，这就是ARM的HMP技术提出的背景。

Heterogeneous的中文意思是“异形的、多种多样的”，从字面意思理解，就是其内部的多个Core有着不同的实现（相对于SMP）。它的产生基于下面两个事实：

> 1）在处理同等事务的情况下，处理器的性能越高，其能量损耗就越大。这是由物理工艺决定的。
>
> 2）以智能手机为例，必须由高性能CPU来完成的事务，在所有事物里的比重是非常小的，如大型游戏、高清视频播放等。甚至很多用户从来都没有用过。

因此，ARM提出类似下面架构的HMP架构，在一个chip中，封装两类ARM Core，一类为高性能Core（如Cortex-A15，也称作big core），一类为低性能Core（如Cortex-A7，也称作little core），因此HMP也称作big·little架构。其中：

> big core的处理性能高，但功耗较大；
>
> little core的功耗低；
>
> 因此软件（如OS的调度器）可以根据需求，将任务分配到big core或者little上，以满足性能和功耗的平衡。

[![HMP](/content/uploadfile/201505/9aeaf0ed2b87c03143e610ab28d3b40d20150530135853.gif "HMP")](/content/uploadfile/201505/1c1cdc8b0b7132a4591e2b9a74ecfb4220150530135852.gif)

在ARM的术语中，所有big core或者所有little core组合，称作cluster（可以类比为2.3中所描述的Socket，但意义完全不同），因此在多数的ARM处理器中（不排除后续ARM服务器又不同实现），CPU topology如下：

> Cluster-->Core-->Threads

在软件模型上，基本和2.3中描述的“Socket—>Core-->Threads”拓扑兼容。

#### 3. Linux kernel CPU topology driver

弄明白CPU topology的物理基础之后，再来看Linux kernel的CPU topology driver就简单多了，其软件层次如下：

> --------------------------------------------- --------------------------------------------   
> | CPU topology driver | | Task Scheduler etc. |   
> --------------------------------------------- -------------------------------------------
>
> ----------------------------------------------------------------------------------------------   
> | Kernel general CPU topology |   
> ----------------------------------------------------------------------------------------------
>
> ----------------------------------------------------------------------------------------------   
> | arch-dependent CPU topology |   
> ----------------------------------------------------------------------------------------------

Kernel general CPU topology位于"include/linux/topology.h”中，定义了获取系统CPU topology信息的标准接口。底层的arch-dependent CPU topology会根据平台的特性，实现kernel定义的那些接口。

CPU topology信息有两个重要的使用场景：一是向用户提供当前的CPU信息（2.1中的lscpu），这是由CPU topology driver实现的；二是向调度器提供CPU core的信息，以便合理的调度任务。

下面将重点介绍Kernel general CPU topology、arch-dependent CPU topology和CPU topology driver，其中arch-dependent CPU topology会以ARM64平台为例。至于如何知道任务调度，则比较复杂，会放到其它文章中介绍。

**3.1 Kernel general CPU topology**

Kernel general CPU topology主要以“#ifndef ... #define”类型的宏定义的形式提供API，其目的是：底层的arch-dependent CPU topology可以重新定义这些宏，只要底层有定义，则优先使用底层的，否则就使用Kernel general CPU topology中的默认API，主要包括：

```
   1: /* include/linux/topology.h */
```

```
   2:  
```

```
   3: #ifndef topology_physical_package_id
```

```
   4: #define topology_physical_package_id(cpu)       ((void)(cpu), -1)
```

```
   5: #endif
```

```
   6: #ifndef topology_core_id
```

```
   7: #define topology_core_id(cpu)                   ((void)(cpu), 0)
```

```
   8: #endif
```

```
   9: #ifndef topology_thread_cpumask
```

```
  10: #define topology_thread_cpumask(cpu)            cpumask_of(cpu)
```

```
  11: #endif
```

```
  12: #ifndef topology_core_cpumask
```

```
  13: #define topology_core_cpumask(cpu)              cpumask_of(cpu)
```

```
  14: #endif
```

```
  15:  
```

```
  16: #ifdef CONFIG_SCHED_SMT
```

```
  17: static inline const struct cpumask *cpu_smt_mask(int cpu)
```

```
  18: {
```

```
  19:         return topology_thread_cpumask(cpu);
```

```
  20: }
```

```
  21: #endif
```

```
  22:  
```

```
  23: static inline const struct cpumask *cpu_cpu_mask(int cpu)
```

```
  24: {
```

```
  25:         return cpumask_of_node(cpu_to_node(cpu));
```

```
  26: }
```

> topology\_physical\_package\_id用于获取某个CPU的package ID，即第2章所描述的socket或者cluster，具体意义依赖于具体平台的实现；
>
> topology\_core\_id用于或者某个CPU的core ID。即第二章所描述的core，具体意义依赖于具体的平台实现；
>
> topology\_thread\_cpumask，获取和该CPU属于同一个core的所有CPU，通俗的讲，就是姐妹Thread；
>
> topology\_core\_cpumask，获取和该CPU属于同一个packet（socket）的所有CPU；
>
> cpu\_cpu\_mask，获取该CPU属于同一个Node的所有CPU；
>
> cpu\_smt\_mask，用于SMT调度（CONFIG\_SCHED\_SMT）的一个封装，意义同topology\_thread\_cpumask。

另外，"include/linux/topology.h”提供一个NUMA有关的API，由于当前ARM使用NUMA技术的可能性不大，我们暂不过多涉及。

**3.2 arch-dependent CPU topology**

对ARM64而言，arch-dependent CPU topology位于“arch/arm64/include/asm/topology.h”和“arch/arm64/kernel/topology.c”中，主要负责ARM64平台相关的topology转换，包括：

1）定义一个数据结构，以及基于该数据结构的变量，用于存储系统的CPU topology

```
   1: /* arch/arm64/include/asm/topology.h */
```

```
   2:  
```

```
   3: struct cpu_topology {
```

```
   4:         int thread_id;
```

```
   5:         int core_id;
```

```
   6:         int cluster_id;
```

```
   7:         cpumask_t thread_sibling;
```

```
   8:         cpumask_t core_sibling;
```

```
   9: };
```

```
  10:  
```

```
  11: extern struct cpu_topology cpu_topology[NR_CPUS];
```

> cluster\_id、core\_id、thead\_id分别对应2.3、2.4章节所描述的拓扑结构的三个层次，其中由于ARM架构的特殊性，以cluster代替了socket；
>
> thread\_sibling和core\_sibling为cpumask\_t类型的变量，保存了和该CPU位于相同级别（同一个core和同一个cluster）的所有姐妹CPU；
>
> 系统中每个CPU（个数由NR\_CPUS指定，是从OS的角度看的），都有一个struct cpu\_topology变量，用于描述该CPU在整个topology中的地位。这些变量以数组的形式（cpu\_topology）维护。

2）重定义CPU topology有关的宏定义

```
   1: /* arch/arm64/include/asm/topology.h */
```

```
   2:  
```

```
   3: #define topology_physical_package_id(cpu)       (cpu_topology[cpu].cluster_id)
```

```
   4: #define topology_core_id(cpu)           (cpu_topology[cpu].core_id)
```

```
   5: #define topology_core_cpumask(cpu)      (&cpu_topology[cpu].core_sibling)
```

```
   6: #define topology_thread_cpumask(cpu)    (&cpu_topology[cpu].thread_sibling)
```

> 实现比较简单，从该CPU对应的struct cpu\_topology变量中取出指定的字段即可。

3）提供初始化并构建CPU topology的方法，以便在系统启动时调用

```
   1: /* arch/arm64/include/asm/topology.h */
```

```
   2:  
```

```
   3: void init_cpu_topology(void);
```

```
   4: void store_cpu_topology(unsigned int cpuid);
```

init\_cpu\_topology的调用路径是：kernel\_init-->smp\_prepare\_cpus-->init\_cpu\_topology，主要完成如下任务：

> 初始化所有可能的CPU的struct cpu\_topology变量;
>
> 尝试从DTS中解析CPU topolog配置，配置的格式如下：
>
> cpus {
>   
>  cpu-map {   
>  cluster0 {
>   
>  core0 {
>   
>  thread0 {
>   
>  cpu = <&big0>;
>   
>  }；
>   
>  thread1 {
>   
>  cpu = <&big1>;
>   
>  }；
>   
>  };
>   
>  core1 {
>   
>  …
>   
>  }
>   
>  …
>   
>  };
>   
>  …
>   
>  };
>
> big0: cpu@0 {
>   
>  device\_type = "cpu";
>   
>  compatible = "arm,cortex-a15";
>   
>  reg = <0x0>;
>   
>  };
>   
>  …
>   
> };
>
> 具体可参考“Documentation/devicetree/bindings/arm/topology.txt”中的描述。

store\_cpu\_topology的调用路径是：kernel\_init-->smp\_prepare\_cpus-->store\_cpu\_topology，在没有从DTS中成功获取CPU topology的情况下，从ARM64的MPIDR寄存器中读取topology信息，具体可参考相应的代码，不再详细描述。

**3.3 CPU topology driver**

CPU topology driver位于“drivers\base\topology.c”中，基于“include/linux/topology.h”所提供的API，以sysfs的形式，向用户空间提供获取CPU topology信息的接口，lscpu应用，就是基于该接口实现的。

具体的实现比较简单，sysfs的格式可参考“Documentation\cputopology.txt”，这里不再详细说明。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpu_topology.html)。
