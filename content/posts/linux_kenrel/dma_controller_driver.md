---
title: "Linux DMA Engine framework(3)_dma controller驱动"
date: 2017-05-18T21:56:34+08:00
url: "/linux_kenrel/dma_controller_driver.html"
gid: "393"
emlog_type: "blog"
summary: "本文将从provider的角度，介绍怎样在linux kernel dmaengine的框架下，编写dma controller驱动。"
author: "wowo"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["driver", "controller", "framework", "dma", "engine"]
views: 25841
comment_count: 5
aliases:
  - "/linux_kenrel/393.html"
  - "/393.html"
---

## 1. 前言

本文将从provider的角度，介绍怎样在linux kernel dmaengine的框架下，编写dma controller驱动。

## 2. dma controller驱动的软件框架

设备驱动的本质是描述并抽象硬件，然后为consumer提供操作硬件的友好接口。dma controller驱动也不例外，它要做的事情无外乎是：

> 1）抽象并控制DMA控制器。
>
> 2）管理DMA channel（可以是物理channel，也可以是虚拟channel，具体可参考[1]中的介绍），并向client driver提供友好、易用的接口。
>
> 3）以DMA channel为操作对象，响应client driver（consumer）的传输请求，并控制DMA controller，执行传输。

当然，按照惯例，为了统一提供给consumer的API（参考[2]），并减少DMA controller driver的开发难度（从论述题变为填空题），dmaengine framework提供了一套controller driver的开发框架，主要思路是（参考图片1）：

[![dma驱动框架](/content/uploadfile/201705/8439a73ea45ce217d00b88f1bc1fd39c20170518135633.gif "dma驱动框架")](/content/uploadfile/201705/aedb6cf06c35b4fcd5577e8f3dd14d0a20170518135633.gif)

图片1 DMA驱动框架

> 1）使用struct dma\_device抽象DMA controller，controller driver只要填充该结构中必要的字段，就可以完成dma controller的驱动开发。
>
> 2）使用struct dma\_chan（图片1中的DCn）抽象物理的DMA channel（图片1中的CHn），物理channel和controller所能提供的通道数一一对应。
>
> 3）基于物理的DMA channel，使用struct virt\_dma\_cha抽象出虚拟的dma channel（图片1中的VCx）。多个虚拟channel可以共享一个物理channel，并在这个物理channel上进行分时传输。
>
> 4）基于这些数据结构，提供一些便于controller driver开发的API，供driver使用。

上面三个数据结构的描述，可参考第3章的介绍。然后，我们会在第4章介绍相关的API、controller driver的开发思路和步骤以及dmaengine中和controller driver有关的重要流程。

## 3. 主要数据结构描述

#### 3.1 struct dma\_device

用于抽象dma controller的struct dma\_device是一个庞杂的数据结构（具体可参考include/linux/dmaengine.h中的代码），不过真正需要dma controller driver关心的内容却不是很多，主要包括：

注1：为了加快对dmaengine framework的理解和掌握，这里只描述一些简单的应用场景，更复杂的场景，只有等到有需求的时候，再更深入的理解。

> channels，一个链表头，用于保存该controller支持的所有dma channel（struct dma\_chan，具体可参考3.2小节）。在初始化的时候，dma controller driver首先要调用INIT\_LIST\_HEAD初始化它，然后调用list\_add\_tail将所有的channel添加到该链表头中。
>
> cap\_mask，一个bitmap，用于指示该dma controller所具备的能力（可以进行什么样的DMA传输），例如（具体可参考enum dma\_transaction\_type的定义）：   
> DMA\_MEMCPY，可进行memory copy；   
> DMA\_MEMSET，可进行memory set；   
> DMA\_SG，可进行scatter list传输；   
> DMA\_CYCLIC，可进行cyclic类[2]的传输；   
> DMA\_INTERLEAVE，可进行交叉传输[2]；   
> 等等，等等（各种奇奇怪怪的传输类型，不看不知道，一看吓一跳！！）。   
> 另外，该bitmap的定义，需要和后面device\_prep\_dma\_xxx形式的回调函数对应（bitmap中支持某个传输类型，就必须提供该类型对应的回调函数）。
>
> src\_addr\_widths，一个bitmap，表示该controller支持哪些宽度的src类型，包括1、2、3、4、8、16、32、64（bytes）等（具体可参考enum dma\_slave\_buswidth 的定义）。   
> dst\_addr\_widths，一个bitmap，表示该controller支持哪些宽度的dst类型，包括1、2、3、4、8、16、32、64（bytes）等（具体可参考enum dma\_slave\_buswidth 的定义）。
>
> directions，一个bitmap，表示该controller支持哪些传输方向，包括DMA\_MEM\_TO\_MEM、DMA\_MEM\_TO\_DEV、DMA\_DEV\_TO\_MEM、DMA\_DEV\_TO\_DEV，具体可参考enum dma\_transfer\_direction的定义和注释，以及[2]中相关的说明。
>
> max\_burst，支持的最大的burst传输的size。有关burst传输的概念可参考[1]。
>
> descriptor\_reuse，指示该controller的传输描述可否可重复使用（client driver可只获取一次传输描述，然后进行多次传输）。
>
> device\_alloc\_chan\_resources/device\_free\_chan\_resources，client driver申请/释放[2] dma channel的时候，dmaengine会调用dma controller driver相应的alloc/free回调函数，以准备相应的资源。具体要准备哪些资源，则需要dma controller driver根据硬件的实际情况，自行决定（这就是dmaengine framework的流氓之处，呵呵~）。
>
> device\_prep\_dma\_xxx，同理，client driver通过dmaengine\_prep\_xxx API获取传输描述符的时候，damengine则会直接回调dma controller driver相应的device\_prep\_dma\_xxx接口。至于要在这些回调函数中做什么事情，dma controller driver自己决定就是了（真懒啊！）。
>
> device\_config，client driver调用dmaengine\_slave\_config[2]配置dma channel的时候，dmaengine会调用该回调函数，交给dma controller driver处理。
>
> device\_pause/device\_resume/device\_terminate\_all，同理，client driver调用dmaengine\_pause、dmaengine\_resume、dmaengine\_terminate\_xxx等API的时候，dmaengine会调用相应的回调函数。
>
> device\_issue\_pending，client driver调用dma\_async\_issue\_pending启动传输的时候，会调用调用该回调函数。

总结：dmaengine对dma controller的抽象和封装，只是薄薄的一层：仅封装出来一些回调函数，由dma controller driver实现，被client driver调用，dmaengine本身没有太多的操作逻辑。

#### 3.2 struct dma\_chan

struct dma\_chan用于抽象dma channel，其内容为：

|  |
| --- |
| struct dma\_chan {    struct dma\_device \*device;    dma\_cookie\_t cookie;    dma\_cookie\_t completed\_cookie;  /\* sysfs \*/    int chan\_id;    struct dma\_chan\_dev \*dev;  struct list\_head device\_node;    struct dma\_chan\_percpu \_\_percpu \*local;    int client\_count;    int table\_count;  /\* DMA router \*/    struct dma\_router \*router;    void \*route\_data;  void \*private;    }; |

需要dma controller driver关心的字段包括：

> device，指向该channel所在的dma controller。
>
> cookie，client driver以该channel为操作对象获取传输描述符时，dma controller driver返回给client的最后一个cookie。
>
> completed\_cookie，在这个channel上最后一次完成的传输的cookie。dma controller driver可以在传输完成时调用辅助函数dma\_cookie\_complete设置它的value。
>
> device\_node，链表node，用于将该channel添加到dma\_device的channel列表中。
>
> router、route\_data，TODO。

#### 3.3 struct virt\_dma\_cha

struct virt\_dma\_chan用于抽象一个虚拟的dma channel，多个虚拟channel可以共用一个物理channel，并由软件调度多个传输请求，将多个虚拟channel的传输串行地在物理channel上完成。该数据结构的定义如下：

|  |
| --- |
| /\* drivers/dma/virt-dma.h \*/        struct virt\_dma\_desc {    struct dma\_async\_tx\_descriptor tx;    /\* protected by vc.lock \*/    struct list\_head node;    };  struct virt\_dma\_chan {    struct dma\_chan chan;    struct tasklet\_struct task;    void (\*desc\_free)(struct virt\_dma\_desc \*);  spinlock\_t lock;  /\* protected by vc.lock \*/    struct list\_head desc\_allocated;    struct list\_head desc\_submitted;    struct list\_head desc\_issued;    struct list\_head desc\_completed;  struct virt\_dma\_desc \*cyclic; }; |

> chan，一个struct dma\_chan类型的变量，用于和client driver打交道（屏蔽物理channel和虚拟channel的差异）。
>
> task，一个tasklet，用于等待该虚拟channel上传输的完成（由于是虚拟channel，传输完成与否只能由软件判断）。
>
> desc\_allocated、desc\_submitted、desc\_issued、desc\_completed，四个链表头，用于保存不同状态的虚拟channel描述符（struct virt\_dma\_desc，仅仅对struct dma\_async\_tx\_descriptor[2]做了一个简单的封装）。

## 4. dmaengine向dma controller driver提供的API汇整

damengine直接向dma controller driver提供的API并不多（大部分的逻辑交互都位于struct dma\_device结构的回调函数中），主要包括：

1）struct dma\_device变量的注册和注销接口

|  |
| --- |
| /\* include/linux/dmaengine.h \*/    int dma\_async\_device\_register(struct dma\_device \*device);    void dma\_async\_device\_unregister(struct dma\_device \*device); |

> dma controller driver准备好struct dma\_device变量后，可以调用dma\_async\_device\_register将它（controller）注册到kernel中。该接口会对device指针进行一系列的检查，然后对其做进一步的初始化，最后会放在一个名称为dma\_device\_list的全局链表上，以便后面使用。
>
> dma\_async\_device\_unregister，注销接口。

2）cookie有关的辅助接口，位于“drivers/dma/dmaengine.h”中，包括

|  |
| --- |
| static inline void dma\_cookie\_init(struct dma\_chan \*chan)    static inline dma\_cookie\_t dma\_cookie\_assign(struct dma\_async\_tx\_descriptor \*tx)    static inline void dma\_cookie\_complete(struct dma\_async\_tx\_descriptor \*tx)    static inline enum dma\_status dma\_cookie\_status(struct dma\_chan \*chan,    dma\_cookie\_t cookie, struct dma\_tx\_state \*state) |

> 由于cookie有关的操作，有很多共性，dmaengine就提供了一些通用实现：
>
> void dma\_cookie\_init，初始化dma channel中的cookie、completed\_cookie字段。
>
> dma\_cookie\_assign，为指针的传输描述（tx）分配一个cookie。
>
> dma\_cookie\_complete，当某一个传输（tx）完成的时候，可以调用该接口，更新该传输所对应channel的completed\_cookie字段。
>
> dma\_cookie\_status，获取指定channel（chan）上指定cookie的传输状态。

3）依赖处理接口

|  |
| --- |
| void dma\_run\_dependencies(struct dma\_async\_tx\_descriptor \*tx); |

> 由前面的描述可知，client可以同时提交多个具有依赖关系的dma传输。因此当某个传输结束的时候，dma controller driver需要检查是否有依赖该传输的传输，如果有，则传输之。这个检查并传输的过程，可以借助该接口进行（dma controller driver只需调用即可，省很多事）。

4）device tree有关的辅助接口

|  |
| --- |
| extern struct dma\_chan \*of\_dma\_simple\_xlate(struct of\_phandle\_args \*dma\_spec,    struct of\_dma \*ofdma);    extern struct dma\_chan \*of\_dma\_xlate\_by\_chan\_id(struct of\_phandle\_args \*dma\_spec,    struct of\_dma \*ofdma); |

> 上面两个接口可用于将client device node中有关dma的字段解析出来，并获取对应的dma channel。后面实际开发的时候会举例说明。

5）虚拟dma channel有关的API

后面会有专门的文章介绍虚拟dma，这里不再介绍。

## 5. 编写一个dma controller driver的方法和步骤

上面啰嗦了这么多，相信大家还是似懂非懂（很正常，我也是，dmaengine framework特点就是框架简单，细节复杂）。到底怎么在dmaengine的框架下编写dma controller驱动呢？现在看来，只靠这篇文章，可能达不到目的了，这里先罗列一下基本步骤，后续我们会结合实际的开发过程，进一步的理解和掌握。

编写一个dma controller driver的基本步骤包括（不考虑虚拟channel的情况）：

1）定义一个struct dma\_device变量，并根据实际的硬件情况，填充其中的关键字段。

2）根据controller支持的channel个数，为每个channel定义一个struct dma\_chan变量，进行必要的初始化后，将每个channel都添加到struct dma\_device变量的channels链表中。

3）根据硬件特性，实现struct dma\_device变量中必要的回调函数（device\_alloc\_chan\_resources/device\_free\_chan\_resources、device\_prep\_dma\_xxx、device\_config、device\_issue\_pending等等）。

4）调用dma\_async\_device\_register将struct dma\_device变量注册到kernel中。

5）当client driver申请dma channel时（例如通过device tree中的dma节点获取），dmaengine core会调用dma controller driver的device\_alloc\_chan\_resources函数，controller driver需要在这个接口中奖该channel的资源准备好。

6）当client driver配置某个dma channel时，dmaengine core会调用dma controller driver的device\_config函数，controller driver需要在这个函数中将client想配置的内容准备好，以便进行后续的传输。

7）client driver开始一个传输之前，会把传输的信息通过dmaengine\_prep\_slave\_xxx接口交给controller driver，controller driver需要在对应的device\_prep\_dma\_xxx回调中，将这些要传输的内容准备好，并返回给client driver一个传输描述符。

8）然后，client driver会调用dmaengine\_submit将该传输提交给controller driver，此时dmaengine会调用controller driver为每个传输描述符所提供的tx\_submit回调函数，controller driver需要在这个函数中将描述符挂到该channel对应的传输队列中。

9）client driver开始传输时，会调用dma\_async\_issue\_pending，controller driver需要在对应的回调函数（device\_issue\_pending）中，依次将队列上所有的传输请求提交给硬件。

10）等等。

## 6. 参考文档

[1] [Linux DMA Engine framework(1)\_概述](/linux_kenrel/dma_engine_overview.html)

[2] [Linux DMA Engine framework(2)\_功能介绍及解接口分析](/linux_kenrel/dma_engine_api.html)

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/linux_kenrel/dma_controller_driver.html)。
