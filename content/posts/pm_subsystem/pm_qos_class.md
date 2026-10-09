---
title: "Linux PM QoS framework(2)_PM QoS class"
date: 2015-02-10T23:09:56+08:00
url: "/pm_subsystem/pm_qos_class.html"
gid: "144"
emlog_type: "blog"
summary: "回顾上一篇文章（ Linux PM QoS framework(1)_概述和软件架构 ），PM QoS framework抽象出4个系统级别的QoS constraint（统称为PM QoS class），分别是cpu&dma latency、network latency、network throughput和memory bandwidth。并提供一系列的接口，动态的搜集、整理系统对这些con"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "Kernel", "pm_qos", "qos"]
views: 33698
comment_count: 7
aliases:
  - "/pm_subsystem/144.html"
  - "/144.html"
---

#### 1. 前言

回顾上一篇文章（[Linux PM QoS framework(1)\_概述和软件架构](/pm_subsystem/pm_qos_overview.html)），PM QoS framework抽象出4个系统级别的QoS constraint（统称为PM QoS class），分别是cpu&dma latency、network latency、network throughput和memory bandwidth。并提供一系列的接口，动态的搜集、整理系统对这些constraint的需求情况。

#### 2. API汇整

PM QoS class framework提供的API有2类：一类是以函数调用的形式，为kernel space的driver、service等提供的；另一类是以misc设备的形式，为用户空间进程提供的。

**2.1 向kernel其它driver提供的，用于提出PM QoS需求的API**

> void pm\_qos\_add\_request(struct pm\_qos\_request \*req, int pm\_qos\_class,   
>  s32 value);   
> void pm\_qos\_update\_request(struct pm\_qos\_request \*req,   
>  s32 new\_value);   
> void pm\_qos\_update\_request\_timeout(struct pm\_qos\_request \*req,   
>  s32 new\_value, unsigned long timeout\_us);   
> void pm\_qos\_remove\_request(struct pm\_qos\_request \*req);
>
> int pm\_qos\_request\_active(struct pm\_qos\_request \*req);

1）pm\_qos\_add\_request

该接口用于向PM QoS framework添加一个QoS请求，pm\_qos\_class为QoS请求的类型（kernel称作pm qos class），value为期望的QoS值，不同的class有不同的含义。pm qos class的定义如下：

```
   1: /* include/linux/pm_qos.h */
```

```
   2: enum {
```

```
   3:         PM_QOS_RESERVED = 0,
```

```
   4:         PM_QOS_CPU_DMA_LATENCY,
```

```
   5:         PM_QOS_NETWORK_LATENCY,
```

```
   6:         PM_QOS_NETWORK_THROUGHPUT,
```

```
   7:         PM_QOS_MEMORY_BANDWIDTH,
```

```
   8:  
```

```
   9:         /* insert new class ID */
```

```
  10:         PM_QOS_NUM_CLASSES,
```

```
  11: };
```

> PM\_QOS\_CPU\_DMA\_LATENCY，CPU和DMA的延迟（单位为us），它的实际意义是，当产生一个事件之后（如一个中断），CPU或DMA的响应延迟。例如有些CPU的串口控制器，只有几个byte的FIFO，当接收数据时，CPU或DMA必须在FIFO填满前，将数据读走，否则就可能丢失数据或者降低数据的传输速率。
>
> 后面几个class，不再详细说明。

以PM\_QOS\_CPU\_DMA\_LATENCY为例，pm\_qos\_add\_request的逻辑可以总结为：我要求CPU&DMA的latency不大于‘value’个us。

另外，为了便于对已添加请求的维护（修改、移除等），framework会将该请求保存在一个句柄中，就是第一个参数--struct pm\_qos\_request指针。调用者不需要知道该结构的具体内容，只要定义一个变量，并把指针传给pm\_qos\_add\_request接口，以后使用该指针进行修改、移除等操作。

2）pm\_qos\_update\_request/pm\_qos\_update\_request\_timeout

如果应用场景改变（如串口波特率变大，相应的响应延迟就要变小），可以通过该接口更新QoS请求。req为句柄指针，new\_value为新的value。

pm\_qos\_update\_request\_timeout多了一个timeout参数，用于需要在一段时间（timeout时间）内修改QoS value的场景。framework会在timeout后，自动将QoS value修改为一个默认值（一般为无效值，代表不再对该QoS有要求）。

3）pm\_qos\_remove\_request

如果对该pm qos class不再有要求，则可以调用该接口将请求移除。

4）pm\_qos\_request\_active

该接口可以获取某一个QoS请求的active状态。

**2.2 向kernel PM有关的service提供的，用于获取、跟踪指定PM QoS需求的API**

> int pm\_qos\_request(int pm\_qos\_class);
>   
> int pm\_qos\_add\_notifier(int pm\_qos\_class, struct notifier\_block \*notifier);
>   
> int pm\_qos\_remove\_notifier(int pm\_qos\_class, struct notifier\_block \*notifier);

每当有新的QoS请求时。framework都会根据该QoS class的含义，计算出满足所有请求的一个极值（如最大值、最小值等等）。该值可以通过pm\_qos\_request接口获得。例如cpuidle framework在选择C state时，会通过该接口获得系统对CPU&DMA latency的需求，并保证从C state返回时的延迟小于该value。

另外，如果某个实体在意某一个class的QoS value变化，可以通过pm\_qos\_add\_notifier接口添加一个notifier，这样当value变化时，framework便会通过notifier的回调函数，通知该实体。

同理，pm\_qos\_remove\_notifier用于删除notifier。

**2.3 向per-device PM QoS framework提供，low level的PM QoS操作API**

> int pm\_qos\_update\_target(struct pm\_qos\_constraints \*c, struct plist\_node \*node,
>   
>  enum pm\_qos\_req\_action action, int value);
>   
> bool pm\_qos\_update\_flags(struct pm\_qos\_flags \*pqf,
>   
>  struct pm\_qos\_flags\_request \*req,
>   
>  enum pm\_qos\_req\_action action, s32 val);
>
> s32 pm\_qos\_read\_value(struct pm\_qos\_constraints \*c);

QoS class和per-device PM QoS都是基于底层的pm qos constraint封装而来的。对QoS class的使用者而言，可以不用关心这些底层细节。对per-device PM QoS framework而言，则需要利用它们实现自身的功能。

这些接口就是提供给per-device PM QoS framework的low level接口，后面再详细介绍。

**2.4 向用户空间process提供的，用于提出QoS需求的API**

根据不同的PM QoS class，包括(cpu&dma latency、network latency等等)：

> /dev/cpu\_dma\_latency
>   
> /dev/network\_latency
>   
> /dev/network\_throughput
>   
> /dev/memory\_bandwidth

打开文件，将会使用默认值向PM QoS framework添加一个QoS请求；关闭文件，会移除相应的请求；写入value，更改请求的值；读取文件，将会获取QoS的极值。

具体和2.1中的各个接口类似，不再详细说明了。

#### 3. 实现思路和内部逻辑

**3.1 主要数据结构**

1）struct pm\_qos\_request，pm qos request句柄，用于request的add、update、remove等操作

```
   1: struct pm_qos_request {
```

```
   2:         struct plist_node node;
```

```
   3:         int pm_qos_class;
```

```
   4:         struct delayed_work work; /* for pm_qos_update_request_timeout */
```

```
   5: };
```

> node，一个struct plist\_node类型的节点，在保存request的value值（node.prio）的同时，可以将request按照一定的顺序，保存在一个全局的链表中；
>
> pm\_qos\_class，该request对应的qos class，可以为PM\_QOS\_CPU\_DMA\_LATENCY、PM\_QOS\_NETWORK\_LATENCY、PM\_QOS\_NETWORK\_THROUGHPUT、PM\_QOS\_MEMORY\_BANDWIDTH中的一种；
>
> 一个delay work，用于实现pm\_qos\_update\_request\_timeout接口。

struct plist\_node是一个按照优先级（prio）降序排列的双向链表（Descending-priority-sorted double-linked），除了常规链表所具备的head和tail之外，有一个prio字段，刚好可以应用在PM QoS class的场景中。

2）struct pm\_qos\_constraints，pm qos的内部抽象，用于抽象某一特定的PM QoS class

```
   1: struct pm_qos_constraints {
```

```
   2:         struct plist_head list;
```

```
   3:         s32 target_value;       /* Do not change to 64 bit */
```

```
   4:         s32 default_value;
```

```
   5:         s32 no_constraint_value;
```

```
   6:         enum pm_qos_type type;
```

```
   7:         struct blocking_notifier_head *notifiers;
```

```
   8: };
```

> list，链表头，所有该class的request，都会挂到该list上；
>
> target\_value，该constraint的目标值，即可以满足所有该class的request那个value。通常情况下，根据request的类型（enum pm\_qos\_type），可以是所有request中的最大值，所有request中的最小值，或者所有request的和；
>
> default\_value，该constraint的默认值，通常为0，表示没有限制（或没有要求）；
>
> no\_constraint\_value，当该class的qos不存在请求时，pm\_qos\_get\_value返回的值，通常为默认值，表示没有限制（或没有要求）；
>
> type，该constraint的类型，具体请参考下面的描述；
>
> notifiers，用于constraint value改变时通知其它driver。

enum pm\_qos\_type包括PM\_QOS\_MAX、PM\_QOS\_MIN和PM\_QOS\_SUM。PM\_QOS\_MAX表示在所有的request中取最大值，即可满足所有的request，如network\_throughput；PM\_QOS\_MIN表示在所有的request中取最小值，即可满足所有的request，如cpu\_dma\_latency；PM\_QOS\_SUM表示在所有的request中取和，才能满足所有的request，如memory\_bandwidth。

当调用pm\_qos\_get\_value接口时，framework会更具qos type，从list head中，取最小值、最大值或者所有值的和。

**3.2 实现逻辑**

QoS class framework为每个class定义了一个全局的struct pm\_qos\_constraints变量，用于保存所有该class的request。同时为每个class定义一个misc device变量，用于向用户空间提供接口。最终，将这些信息组织在一个内部的数据结构中（struct pm\_qos\_object），如下（具体内容可参考kernel/power/qos.c，这里不再详细介绍）：

```
   1: struct pm_qos_object {
```

```
   2:         struct pm_qos_constraints *constraints;
```

```
   3:         struct miscdevice pm_qos_power_miscdev;
```

```
   4:         char *name;
```

```
   5: };
```

```
   6:  
```

```
   7: ...
```

```
   8:  
```

```
   9: static struct pm_qos_object *pm_qos_array[] = {
```

```
  10:         &null_pm_qos,
```

```
  11:         &cpu_dma_pm_qos,
```

```
  12:         &network_lat_pm_qos,
```

```
  13:         &network_throughput_pm_qos,
```

```
  14:         &memory_bandwidth_pm_qos,
```

```
  15: };
```

1）pm\_qos\_add\_request

request add接口会以qos class为index，从qos array中取出constraint指针（pm\_qos\_array[pm\_qos\_class]->constraints），并指针和request的value为参数，调用pm\_qos\_update\_target接口。

pm\_qos\_update\_target会将该request添加到constraint的list中，并根据qos type，计算处该class qos的target value。

pm\_qos\_update\_request/pm\_qos\_update\_request\_timeout的逻辑类似，不再详细描述。

2）pm\_qos\_request

直接从该class对应的constraint变量中，获取target value（已经在新的request被add之后更新）。

3）misc设备注册

当kernel会在QoS class framework的初始化接口（pm\_qos\_power\_init）中，调用misc\_register，将各个class的miscdevice变量，注册到kernel中。misc设备提供了open、release、read、write等接口（pm\_qos\_power\_fops，具体可参考源文件），用于qos的request、update和remove。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/pm_qos_class.html)。
