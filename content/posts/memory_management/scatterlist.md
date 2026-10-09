---
title: "Linux kernel scatterlist API介绍"
date: 2017-10-13T22:20:34+08:00
url: "/memory_management/scatterlist.html"
gid: "413"
emlog_type: "blog"
summary: "我们在那些需要和用户空间交互大量数据的子系统（例如MMC [1] 、Video、Audio等）中，经常看到scatterlist的影子。对我们这些“非英语母语”的人来说，初见这个词汇，脑袋瞬间就蒙圈了。scatter可翻译成“散开、分散”，list是“列表”的意思，因而scatterlist可翻译为“散列表”。“散列表”又是什么？太抽象了！ 之所以抽象，是因为这个词省略了主语----物理内存（Ph"
author: "wowo"
category: "内存管理"
category_alias: "memory_management"
tags: ["Linux", "Kernel", "内核", "scatterlist", "sg_table"]
views: 41640
comment_count: 12
aliases:
  - "/memory_management/413.html"
  - "/413.html"
---

## 1. 前言

我们在那些需要和用户空间交互大量数据的子系统（例如MMC[1]、Video、Audio等）中，经常看到scatterlist的影子。对我们这些“非英语母语”的人来说，初见这个词汇，脑袋瞬间就蒙圈了。scatter可翻译成“散开、分散”，list是“列表”的意思，因而scatterlist可翻译为“散列表”。“散列表”又是什么？太抽象了！

之所以抽象，是因为这个词省略了主语----物理内存（Physical memory），加上后，就好理解了多了，既：物理内存的散列表。再通俗一些，就是把一些分散的物理内存，以列表的形式组织起来。那么，也许你会问，有什么用处呢？

当然有用，具体可参考本文后续的介绍。

## 2. scatterlist产生的背景

我没有去考究scatterlist API是在哪个kernel版本中引入的（年代太久远了），凭猜测，我觉得应该和MMU有关。因为在引入MMU之后，linux系统中的软件将不得不面对一个困扰（下文将以图片1中所示的系统架构为例进行说明）：

> 假设在一个系统中（参考下面图片1）有三个模块可以访问memory：CPU、DMA控制器和某个外设。CPU通过MMU以虚拟地址（VA）的形式访问memory；DMA直接以物理地址（PA）的形式访问memory；Device通过自己的IOMMU以设备地址（DA）的形式访问memory。
>
> 然后，某个“软件实体”分配并使用了一片存储空间（参考下面图片2）。该存储空间在CPU视角上（虚拟空间）是连续的，起始地址是va1（实际上，它映射到了3块不连续的物理内存上，我们以pa1,pa2,pa3表示）。
>
> 那么，如果该软件单纯的以CPU视角访问这块空间（操作va1），则完全没有问题，因为MMU实现了连续VA到非连续PA的映射。
>
> 不过，如果软件经过一系列操作后，要把该存储空间交给DMA控制器，最终由DMA控制器将其中的数据搬移给某个外设的时候，由于DMA控制器只能访问物理地址，只能以“不连续的物理内存块”为单位递交（而不是我们所熟悉的虚拟地址）。
>
> 此时，scatterlist就诞生了：为了方便，我们需要使用一个数据结构来描述这一个个“不连续的物理内存块”（起始地址、长度等信息），这个数据结构就是scatterlist（具体可参考下面第3章的说明）。而多个scatterlist组合在一起形成一个表（可以是一个struct scatterlist类型的数组，也可以是kernel帮忙抽象出来的struct sg\_table），就可以完整的描述这个虚拟地址了。
>
> 最后，从本质上说：scatterlist（数组）是各种不同地址映射空间（PA、VA、DA、等等）的媒介（因为物理地址是真实的、实在的存在，因而可以作为通用语言），借助它，这些映射空间才能相互转换（例如从VA转到DA）。

[![cpu_dma_device_memory](/content/uploadfile/201710/d568260d4a6a1127654074c114e84f1220171013142032.gif "cpu_dma_device_memory")](/content/uploadfile/201710/62ccc8c710eaa9b393e56c8d2746df4820171013142032.gif)

图片1 cpu\_dma\_device\_memory

[![cpu_view_memory](/content/uploadfile/201710/2392578dfe2c1f39048ea5ee8e7eb0c820171013142033.gif "cpu_view_memory")](/content/uploadfile/201710/a159a36c35bcec7617fd7684f92024fe20171013142033.gif)

图片2 cpu\_view\_memory

## 3. scatterlist API介绍

#### 3.1 struct scatterlist

struct scatterlist用于描述一个在物理地址上连续的内存块（以page为单位），它的定义位于“include/linux/scatterlist.h”中，如下：

|  |
| --- |
| struct scatterlist {    #ifdef CONFIG\_DEBUG\_SG    unsigned long sg\_magic;    #endif    unsigned long page\_link;    unsigned int offset;    unsigned int length;    dma\_addr\_t dma\_address;    #ifdef CONFIG\_NEED\_SG\_DMA\_LENGTH    unsigned int dma\_length;    #endif    }; |

> page\_link，指示该内存块所在的页面。bit0和bit1有特殊用途（可参考后面的介绍），因此要求page最低4字节对齐。   
> offset，指示该内存块在页面中的偏移（起始位置）。   
> length，该内存块的长度。
>
> dma\_address，该内存块实际的起始地址（PA，相比page更接近我们人类的语言）。   
> dma\_length，相应的长度信息。

#### 3.2 struct sg\_table

在实际的应用场景中，单个的scatterlist是没有多少意义的，我们需要多个scatterlist组成一个数组，以表示在物理上不连续的虚拟地址空间。通常情况下，使用scatterlist功能的模块，会自行维护这个数组（指针和长度），例如[2]中所提到的struct mmc\_data：

|  |
| --- |
| struct mmc\_data {    …     unsigned int sg\_len; /\* size of scatter list \*/    struct scatterlist \*sg; /\* I/O scatter list \*/   s32 host\_cookie; /\* host private data \*/    }; |

不过呢，为了使用者可以偷懒，kernel抽象出来了一个简单的数据结构：struct sg\_table，帮忙保存scatterlist的数组指针和长度：

|  |
| --- |
| struct sg\_table {    struct scatterlist \*sgl; /\* the list \*/    unsigned int nents; /\* number of mapped entries \*/    unsigned int orig\_nents; /\* original size of list \*/    }; |

其中sgl是内存块数组的首地址，orig\_nents是内存块数组的size，nents是有效的内存块个数（可能会小于orig\_nents）。

以上心思都比较直接，不过有一点，我们要仔细理解：

scatterlist数组中到底有多少有效内存块呢？这不是一个很直观的事情，主要有如下2个规则决定：

> 1）如果scatterlist数组中某个scatterlist的page\_link的bit0为1，表示该scatterlist不是一个有效的内存块，而是一个chain（铰链），指向另一个scatterlist数组。通过这种机制，可以将不同的scatterlist数组链在一起，因为scatterlist也称作chain scatterlist。
>
> 2）如果scatterlist数组中某个scatterlist的page\_link的bit1为1，表示该scatterlist是scatterlist数组中最后一个有效内存块（后面的就忽略不计了）。

#### 3.3 API介绍

理解了scatterlist的含义之后，再去看“include/linux/scatterlist.h”中的API，就容易多了，例如（简单介绍一下，不再详细分析）：

|  |
| --- |
| #define sg\_dma\_address(sg) ((sg)->dma\_address)  #ifdef CONFIG\_NEED\_SG\_DMA\_LENGTH    #define sg\_dma\_len(sg) ((sg)->dma\_length)    #else    #define sg\_dma\_len(sg) ((sg)->length)    #endif |

> sg\_dma\_address、sg\_dma\_len，获取某一个scatterlist的物理地址和长度。

|  |
| --- |
| #define sg\_is\_chain(sg) ((sg)->page\_link & 0x01)    #define sg\_is\_last(sg) ((sg)->page\_link & 0x02)    #define sg\_chain\_ptr(sg) \    ((struct scatterlist \*) ((sg)->page\_link & ~0x03)) |

> sg\_is\_chain可用来判断某个scatterlist是否为一个chain，sg\_is\_last可用来判断某个scatterlist是否是sg\_table中最后一个scatterlist。
>
> sg\_chain\_ptr可获取chain scatterlist指向的那个scatterlist。

|  |
| --- |
| static inline void sg\_assign\_page(struct scatterlist \*sg, struct page \*page)    static inline void sg\_set\_page(struct scatterlist \*sg, struct page \*page,    unsigned int len, unsigned int offset)    static inline struct page \*sg\_page(struct scatterlist \*sg)    static inline void sg\_set\_buf(struct scatterlist \*sg, const void \*buf,    unsigned int buflen)       #define for\_each\_sg(sglist, sg, nr, \_\_i) \    for (\_\_i = 0, sg = (sglist); \_\_i < (nr); \_\_i++, sg = sg\_next(sg))       static inline void sg\_chain(struct scatterlist \*prv, unsigned int prv\_nents,    struct scatterlist \*sgl)       static inline void sg\_mark\_end(struct scatterlist \*sg)    static inline void sg\_unmark\_end(struct scatterlist \*sg)       static inline dma\_addr\_t sg\_phys(struct scatterlist \*sg)    static inline void \*sg\_virt(struct scatterlist \*sg) |

> sg\_assign\_page，将page赋给指定的scatterlist（设置page\_link字段）。   
> sg\_set\_page，将page中指定offset、指定长度的内存赋给指定的scatterlist（设置page\_link、offset、len字段）。   
> sg\_page，获取scatterlist所对应的page指针。   
> sg\_set\_buf，将指定长度的buffer赋给scatterlist（从虚拟地址中获得page指针、在page中的offset之后，再调用sg\_set\_page）。
>
> for\_each\_sg，遍历一个scatterlist数组（sglist）中所有的有效scatterlist（考虑sg\_is\_chain和sg\_is\_last的情况）。
>
> sg\_chain，将两个scatterlist 数组捆绑在一起。
>
> sg\_mark\_end、sg\_unmark\_end，将某个scatterlist 标记（或者不标记）为the last one。
>
> sg\_phys、sg\_virt，获取某个scatterlist的物理或者虚拟地址。

等等（不再罗列了，感兴趣的同学直接去看代码就行了）。

## 4. 参考文档

[1] [Linux MMC framework(2)\_host controller driver](/comm/mmc_host_driver.html)

[2] The chained scatterlist API，[https://lwn.net/Articles/256368/](https://lwn.net/Articles/256368/ "https://lwn.net/Articles/256368/")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/memory_management/scatterlist.html)。
