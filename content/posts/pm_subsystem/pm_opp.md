---
title: "Linux电源管理(15)_PM OPP Interface"
date: 2015-06-04T21:54:14+08:00
url: "/pm_subsystem/pm_opp.html"
gid: "192"
emlog_type: "blog"
summary: "本文是分析cpufreq framework之前的一篇前置文章，用于介绍Linux电源管理中的Operating Performance Point (OPP)接口。 OPP是一个单纯的软件library，用于归纳、管理各个硬件模块的、可工作的｛频率｝/ ｛电压｝组合。它不涉及任何硬件，也没有复杂的逻辑，再加上Kernel document（Documentation/power/opp.txt "
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "Power", "opp"]
views: 24655
comment_count: 12
aliases:
  - "/pm_subsystem/192.html"
  - "/192.html"
---

#### 1. 前言

本文是分析cpufreq framework之前的一篇前置文章，用于介绍Linux电源管理中的Operating Performance Point (OPP)接口。

OPP是一个单纯的软件library，用于归纳、管理各个硬件模块的、可工作的｛频率｝/ ｛电压｝组合。它不涉及任何硬件，也没有复杂的逻辑，再加上Kernel document（Documentation/power/opp.txt ）描述的非常清晰，因此本文只是简单的从功能和API两个方便介绍OPP，不再分析其source code及内部实现逻辑。

#### 2. 功能说明

**2.1 什么是OPP**

“Documentation/power/opp.txt ”中解释OPP的原话（我翻译了一下）是：

> 当前复杂的SoCs都包括多个协同工作的子模块。根据具体的应用场景，很多子模块（蜗蜗注：典型的例子是CPU）并不需要一直工作在最高的频率上。因此SoC中的子模块划分为不同的domains，允许一些domains在较低的电压/频率下工作，而另一些在较高的电压/频率下工作。
>
> domain中的设备支持的所有频率和电压的组合，称作Operating Performance Points，简称为OPPs。

注1：为什么一定是频率和电压的组合？因为频率高低决定器件的工作性能，降低性能的目的是节省功耗。但频率对功耗的影响是有限的，而电压对功耗的影响却相当可观。那频率和电压有什么关系呢？通常情况下，当频率降低之后，器件的工作电压也是可以降低的（回忆一下数字电路）。因此不同的“频率/电压”组合，就组成了器件在性能和功耗之间的跷跷板，我们需要做的，就是根据实际场景，选择一个合适的组合。

**2.2 使用场景**

对具备多个OPP的设备而言，相关的使用场景包括：

1）需要一个三维数组，保存所有的OPPs。

2）可以方便的更改OPP条目。

3）当需要改变设备的OPP时，可以方便的查询设备支持哪些OPP。

4）可以通过一定的条件查询OPP信息，例如以频率值查询、以电压值查询、以频率或者电压范围查询等等。

5）其它需求。

其实蛮简单的，但考虑到这些需求对所有设备（应该也不是很多）都是相同，kernel就抽象出来一个library--就是OPP library，实现上述功能。具体可参考后续的描述。

**2.3 实现思路**

试下OPP library的主要思路，就是以设备为单位，管理OPP信息。如下（摘录自Documentation/power/opp.txt ）：

> \*   
> \* Internal data structure organization with the OPP layer library is as   
> \* follows:   
> \* dev\_opp\_list (root)   
> \* |- device 1 (represents voltage domain 1)   
> \* | |- opp 1 (availability, freq, voltage)   
> \* | |- opp 2 ..   
> \* ... ...   
> \* | `- opp n ..   
> \* |- device 2 (represents the next voltage domain)   
> \* ...   
> \* `- device m (represents mth voltage domain)   
> \* device 1, 2.. are represented by dev\_opp structure while each opp   
> \* is represented by the opp structure.   
> \*/

按理说，可以在设备指针（struct device）中，添加一个字段，用于保存该设备的OPP列表。但OPP人微言轻，无法打入设备模型的内部，只好自己处理了。就是上面的结构：

在OPP内部（drivers/base/power/opp.c）维护一个list，用于保存每个设备的OPP信息（由struct device\_opp抽象），每个设备下面，维护了所有的OPP列表（由struct dev\_pm\_opp结构抽象）。所有的OPP操作，都会从root list开始遍历，直到找到合适的地方为止。

struct device\_opp和struct dev\_pm\_opp只在OPP library的内部使用，不会把细节呈现给调用者，因为本文不会过多涉及OPP library的内部实现（比较简单），所以后面就不再描述这些结构了。

#### 3. 接口说明

OPP library的source code位于drivers/base/power/opp.c中，header位于include/linux/pm\_opp.h中，提供的接口包括（本文基于linux-3.18-rc4，其它版本的文件名或者接口名可能会有些不同）：

```
   1: int dev_pm_opp_add(struct device *dev, unsigned long freq,
```

```
   2:                    unsigned long u_volt);
```

> 向指定的设备添加一个频率/电压组合，OPP library会在内部处理好所有事情。这里频率和电压的单位分别是Hz和uV，后面都是这个单位。

```
   1: int dev_pm_opp_enable(struct device *dev, unsigned long freq);
```

```
   2:  
```

```
   3: int dev_pm_opp_disable(struct device *dev, unsigned long freq);
```

> 虽然设备支持某些OPP，但driver有可能觉得比较危险，不想使用，则可以调用dev\_pm\_opp\_disable接口，禁止该OPP。这是后面很多查询结构（除了dev\_pm\_opp\_find\_freq\_exact）都无法查到该OPP。
>
> 相反，dev\_pm\_opp\_enable用于使能指定的OPP。
>
> 注：调用dev\_pm\_opp\_add添加进去的OPP，默认是enable的。

```
   1: int dev_pm_opp_get_opp_count(struct device *dev);
```

```
   2:  
```

```
   3: struct dev_pm_opp *dev_pm_opp_find_freq_exact(struct device *dev,
```

```
   4:                                               unsigned long freq,
```

```
   5:                                               bool available);
```

```
   6:  
```

```
   7: struct dev_pm_opp *dev_pm_opp_find_freq_floor(struct device *dev,
```

```
   8:                                               unsigned long *freq);
```

```
   9:  
```

```
  10: struct dev_pm_opp *dev_pm_opp_find_freq_ceil(struct device *dev,
```

```
  11:                                              unsigned long *freq);
```

> OPP的查询接口，返回相应的dev\_pm\_opp指针（当作一个句柄使用），包括：
>
> dev\_pm\_opp\_find\_freq\_floor，查询小于或者等于指定freq的OPP，在返回OPP的同时，从freq指针中返回实际的freq值；
>
> dev\_pm\_opp\_find\_freq\_ceil，查询大于或者等于指定freq的OPP，在返回OPP的同时，从freq指针中返回实际的freq值；
>
> dev\_pm\_opp\_find\_freq\_exact，精确查找指定freq的OPP，同时通过available变量，可以控制是否查找处于disable状态的OPP。上面两个查找接口，是不查找处于disable状态的OPP的。

```
   1: unsigned long dev_pm_opp_get_voltage(struct dev_pm_opp *opp);
```

```
   2:  
```

```
   3: unsigned long dev_pm_opp_get_freq(struct dev_pm_opp *opp);
```

> 从指定的OPP句柄中，获得频率或者电压值。

```
   1: #if defined(CONFIG_PM_OPP) && defined(CONFIG_OF)
```

```
   2: int of_init_opp_table(struct device *dev);
```

```
   3: #else
```

```
   4: static inline int of_init_opp_table(struct device *dev)
```

```
   5: {
```

```
   6:         return -EINVAL;
```

```
   7: }
```

```
   8: #endif
```

> 从DTS中，解析并初始化一个设备的opp table。DTS的格式如下（参考arch/arm/boot/dts/omap34xx.dtsi）：
>
> cpus {
>   
>  cpu@0 {
>   
>  /\* OMAP343x/OMAP35xx variants OPP1-5 \*/
>   
>  operating-points = <
>   
>  /\* kHz uV \*/
>   
>  125000 975000
>   
>  250000 1075000
>   
>  500000 1200000
>   
>  550000 1270000
>   
>  600000 1350000
>   
>  >;
>   
>  clock-latency = <300000>; /\* From legacy driver \*/
>   
>  };
>   
> };
>
> 以“operating-points”为名称，指定频率和电压组合，单位分别为kHz和uV。具体解析过程不再描述。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/pm_opp.html)。
