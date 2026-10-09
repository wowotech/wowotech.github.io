---
title: "Linux PM QoS framework(3)_per-device PM QoS"
date: 2015-02-26T22:44:26+08:00
url: "/pm_subsystem/per_device_pm_qos.html"
gid: "148"
emlog_type: "blog"
summary: "per-device PM QoS是针对指定设备的QoS framework，背后的思考如下： 1）resume_latency 在 Runtime PM 的框架下，当device的引用计数减为0的时候，RPM会suspend该device。不过，device进入suspend状态以及从suspend状态resume是需要消耗时间的（相关信息保存在 pm domain 中），而系统其它实体（如用户"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "Kernel", "pm_qos", "per-device"]
views: 17158
comment_count: 9
aliases:
  - "/pm_subsystem/148.html"
  - "/148.html"
---

#### 1. 前言

per-device PM QoS是针对指定设备的QoS framework，背后的思考如下：

1）resume\_latency

在[Runtime PM](/tag/rpm)的框架下，当device的引用计数减为0的时候，RPM会suspend该device。不过，device进入suspend状态以及从suspend状态resume是需要消耗时间的（相关信息保存在[pm domain](/pm_subsystem/pm_domain_overview.html)中），而系统其它实体（如用户空间程序）可能对该设备的响应时间有要求，这就是一种形式的QoS request，称作resume\_latency。

per-device PM QoS framework会提供相应的接口，收集指定设备的resume\_latency request，并提供给Runtime PM，它在suspend设备时，会考虑这种需求，并决定是否suspend设备。

2）latency\_tolerance

一些复杂的设备，在运行状态（active）时，为了节省功耗，也有可能自行进入某些省电状态，相应的，设备的响应速度可能降低。如果该设备足够智能，可能会提供一个回调函数（.set\_latency\_tolerance，位于dev\_pm\_info结构中），以便设置最大的延迟容忍时间。这称作latency\_tolerance。

对per-device PM QoS来说，需要提供一种机制，收集所有的、针对某个设备的latency\_tolerance需求，并汇整出可以满足所有需求的latency\_tolerance，通过设备的回调函数告知设备。

3）no power off/remote wakeup

在[Runtime PM](/tag/rpm)的框架下，设备suspend之后，还可以进一步通过[pm domain](/pm_subsystem/pm_domain_overview.html)关闭该设备的供电，以节省功耗。但关闭供电时，除了要考虑对设备resume\_latency的需求之外，还要考虑该设备是否允许关闭供电，以及该设备是否需要作为一个唤醒源（remote wakeup）。

这是另一种形式的QoS request，称作per-device PM QoS flag，表示系统其它实体对该设备的一些特定行为的需求。当前的flag有两种：

PM\_QOS\_FLAG\_NO\_POWER\_OFF，表示不允许设备断电   
PM\_QOS\_FLAG\_REMOTE\_WAKEUP，表示设备应具备唤醒功能

这两个flag可以通过或操作，同时生效。

因此，per-device PM QoS framework的功能，就是抽象上面两类需求，包括：向requestor提供QoS request的add、update、remove等API，包括内核空间API和用户空间API；汇整、整理这些request；向电源管理有关的service（主要是[pm domain framework](/pm_subsystem/pm_domain_overview.html)）提供汇整后的request信息，以便这些service可以做出正确的决定。

下面将会结合source code(位于drivers/base/power/qos.c中），介绍上面的实现逻辑。

#### 2. API汇整

**2.1 struct dev\_pm\_qos数据结构**

每个设备的per-device pm qos信息，都保存在设备的qos指针中，即：

```
   1: struct device {
```

```
   2:         ...
```

```
   3:         struct dev_pm_info      power;
```

```
   4:         ...
```

```
   5: }
```

```
   6:  
```

```
   7: struct dev_pm_info {
```

```
   8:         ...
```

```
   9:         struct dev_pm_qos       *qos;
```

```
  10:         ...
```

```
  11: }
```

该指针的数据类型struct dev\_pm\_qos是per-device pm qos的核心数据结构，定义如下：

```
   1: struct dev_pm_qos {
```

```
   2:         struct pm_qos_constraints resume_latency;
```

```
   3:         struct pm_qos_constraints latency_tolerance;
```

```
   4:         struct pm_qos_flags flags;
```

```
   5:         struct dev_pm_qos_request *resume_latency_req;
```

```
   6:         struct dev_pm_qos_request *latency_tolerance_req;
```

```
   7:         struct dev_pm_qos_request *flags_req;
```

```
   8: };
```

> resume\_latency，为第一种QoS request，表示其它实体对该设备从suspend状态返回的延迟的要求。struct pm\_qos\_constraints为pm qos要求的具体抽象，可参考“[Linux PM QoS framework(2)\_PM QoS class](/pm_subsystem/pm_qos_class.html)”中的描述；
>
> latency\_tolerance，为第二种QoS request，和resume\_latency类似；
>
> flags，为第三种QoS request，主要包括一个链表头，用于保存具体的flag要求，以及汇整后的、当前所有有效的flags；
>
> resume\_latency\_req、latency\_tolerance\_req、flags\_req，三个不同类型的request指针，用于保存用户空间对设备pm QoS的request请求。struct dev\_pm\_qos\_request结构类似[上一篇文章](/pm_subsystem/pm_qos_class.html)所描述的struct pm\_qos\_request结构，用于抽象一个具体的request。

```
   1: struct dev_pm_qos_request {
```

```
   2:         enum dev_pm_qos_req_type type;
```

```
   3:         union {
```

```
   4:                 struct plist_node pnode;
```

```
   5:                 struct pm_qos_flags_request flr;
```

```
   6:         } data;
```

```
   7:         struct device *dev;
```

```
   8: };
```

> type，request的类型，当前共三类，包括在前言部分所描述的三种request（DEV\_PM\_QOS\_RESUME\_LATENCY、DEV\_PM\_QOS\_LATENCY\_TOLERANCE、DEV\_PM\_QOS\_FLAGS）；
>
> data，不同类型的request，有不同的数据，因此这里是一个联合体。当为DEV\_PM\_QOS\_RESUME\_LATENCY、DEV\_PM\_QOS\_LATENCY\_TOLERANCE时，为一个plist\_node，类似PM QoS class。为DEV\_PM\_QOS\_FLAGS时，为struct pm\_qos\_flags\_request类型的变量；
>
> dev，保存了设备指针。

**2.2 向kernel其它driver提供的，用于提出per-device PM QoS需求的API**

> int dev\_pm\_qos\_add\_request(struct device \*dev, struct dev\_pm\_qos\_request \*req,
>   
>  enum dev\_pm\_qos\_req\_type type, s32 value);
>   
> int dev\_pm\_qos\_update\_request(struct dev\_pm\_qos\_request \*req, s32 new\_value);
>   
> int dev\_pm\_qos\_remove\_request(struct dev\_pm\_qos\_request \*req);

类似PM QoS class中的pm\_qos\_\*接口，不过操作对象为设备，因而需要提供相应的设备指针。

**2.3 向kernel PM有关的service（例如PM domain）提供的，用于获取、跟踪指定PM QoS需求的API**

> enum pm\_qos\_flags\_status dev\_pm\_qos\_flags(struct device \*dev, s32 mask);
>   
> s32 dev\_pm\_qos\_read\_value(struct device \*dev);
>   
>   
> int dev\_pm\_qos\_add\_notifier(struct device \*dev,
>   
>  struct notifier\_block \*notifier);
>   
> int dev\_pm\_qos\_remove\_notifier(struct device \*dev,
>   
>  struct notifier\_block \*notifier);
>   
> int dev\_pm\_qos\_add\_global\_notifier(struct notifier\_block \*notifier);
>   
> int dev\_pm\_qos\_remove\_global\_notifier(struct notifier\_block \*notifier);

由于DEV\_PM\_QOS\_FLAGS特殊性，kernel提供了单独的API，以获取相应的flags。对于其它两个类型的QoS，和PM QoS class中的pm\_qos\_\*接口类似。

**2.4 向用户空间process提供的，用于提出per-device PM QoS需求的API**

通过sysfs文件，kernel允许用户空间程序对某个设备提出QoS需求，这些sysfs文件位于各个设备的sysf目录下，默认情况下，PM QoS framework不会创建这些文件，除非具体设备驱动调用dev\_pm\_qos\_expose\_\*系列接口，主动创建。具体可参考代码，这里不再详细说明。

#### 3. 实现思路和内部逻辑

和PM QoS class类似，不再描述。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/per_device_pm_qos.html)。
