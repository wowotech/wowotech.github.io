---
title: "/proc/meminfo分析（一）"
date: 2017-08-17T19:27:06+08:00
url: "/memory_management/meminfo_1.html"
gid: "406"
emlog_type: "blog"
summary: "本文主要分析/proc/meminfo文件的各种输出信息的具体含义。"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["meminfo"]
views: 31627
comment_count: 18
aliases:
  - "/memory_management/406.html"
  - "/406.html"
---

本文主要分析/proc/meminfo文件的各种输出信息的具体含义。

一、MemTotal

MemTotal对应当前系统中可以使用的物理内存。

这个域实际是对应内核中的totalram\_pages这个全局变量的，定义如下：

> unsigned long totalram\_pages \_\_read\_mostly;

该变量表示当前系统中Linux内核可以管理的所有的page frame的数量。注意：这个值并不是系统配置的内存总数，而是指操作系统可以管理的内存总数。

内核是如何得到totalram\_pages这个值的呢？是在初始化的过程中得到的，具体如下：我们知道，在内核初始化的时候，我们可以通过memblock模块来管理内存布局，从而得到了memory type和reserved type的内存列表信息。在初始化阶段如果有内存分配的需求，那么也可以通过memblock来完成，直到伙伴系统初始化完成，而在这个过程中，memory type的那些page frame被一个个的注入到各个zone的free list中，同时用totalram\_pages 来记录那个时间点中空闲的page frame数量。这个点也就是伙伴系统的一个初始内存数量的起点。

举一个实际的例子：我的T450的计算机，配置的内存是8G，也就是8388608KB。但是MemTotal没有那么多，毕竟OS本身（正文段、数据段等等）就会占用不少内存，此外还有系统各种保留的内存，把这些都去掉，Linux能管理的Total memory是7873756KB。看来OS内存管理的开销也不小啊。

二、MemFree

启动的时候，系统确定了MemTotal的数目，但是随着系统启动过程，内核会动态申请内存，此外，用户空间也会不断创建进程，也会不断的消耗内存，因此MemTotal可以简单分成两个部分：正在使用的和空闲的。MemFree表示的就是当前空闲的内存数目，这些空闲的page应该是挂在各个node的各个zone的buddy系统中。

具体free memory的计算如下：

> freeram = global\_page\_state(NR\_FREE\_PAGES);

也就是把整个系统中在当前时间点上空闲的内存数目统计出来。

三、MemAvailable

所谓memory available，其实就是不引起swapping操作的情况下，我们能使用多少的内存。即便是free的，也不是每一个page都可以用于内存分配。例如buddy system会设定一个水位，一旦free memory低于这个水位，系统就会启动page reclaim，从而可能引起swapping操作。因此，我们需要从MemFree这个数值中去掉各个节点、各个zone的预留的内存（WMARK\_LOW）数目。当然，也是不是说那些不是空闲的页面我们就不能使用，例如page cache，虽然不是空闲的，但是它也不过是为了加快性能而使用，其实也可以回收使用。当然，也不是所有的page cache都可以计算进入MemAvailable，有些page cache在回收的时候会引起swapping，这些page cache就不能算数了。此外，reclaimable slab中也有一些可以使用的内存，MemAvailable也会考虑这部分内存的情况。

总而言之，MemAvailable就是不需要额外磁盘操作（开销较大）就可以使用的空闲内存的数量。

四、Buffers

其实新的内核已经没有buffer cache了，一切都统一到了page cache的框架下了。因此，所谓的buffer cache就是块设备的page cache。具体的统计过程是通过nr\_blockdev\_pages函数完成，代码如下：

> long nr\_blockdev\_pages(void)   
> {   
> struct block\_device \*bdev;   
> long ret = 0;   
> spin\_lock(&bdev\_lock);   
> list\_for\_each\_entry(bdev, &all\_bdevs, bd\_list) {   
> ret += bdev->bd\_inode->i\_mapping->nrpages;   
> }   
> spin\_unlock(&bdev\_lock);   
> return ret;   
> }

我们知道，内核是通过address\_space来管理page cache的，那么块设备的address\_space在哪里呢？这个稍微复杂一点，涉及多个inode，假设/dev/aaa和/dev/bbb都是指向同一个物理块设备，那么open/dev/aaa和/dev/bbb会分别产生两个inode，我们称之inode\_aaa和inode\_bbb，但是最后一个块设备的page cache还是需要统一管理起来，不可能分别在inode\_aaa和inode\_bbb中管理。因此，Linux构造了一个bdev文件系统，保存了系统所有块设备的inode，我们假设该物理块设备在bdev文件系统中的inode是inode\_bdev。上面讲了这么多的inode，其实块设备的page cache就是在inode\_bdev中管理的。

一般来说，buffers的数量不多，因为产生buffer的操作包括：

1、打开该block device的设备节点，直接进行读写操作（例如dd一个块设备）

2、mount文件系统的时候，需要从相应的block device上直接把块设备上的特定文件系统的super block相关信息读取出来，这些super block的raw data会保存在该block device的page cache中

3、文件操作的时候，和文件元数据相关的操作（例如读取磁盘上的inode相关的信息）也是通过buffer cache进行访问。

Linux中最多处理的是2和3的操作，1的操作很少有。

五、Cached

读写普通文件的时候，我们并不会直接操作磁盘，而是通过page cache来加速文件IO的性能。Cached域描述的就是用于普通文件IO的page cache的数量，具体计算过程如下：

> cached = global\_page\_state(NR\_FILE\_PAGES) -   
> total\_swapcache\_pages() - i.bufferram;

系统中所有的page cache都会被记录在一个全局的状态中，通过global\_page\_state(NR\_FILE\_PAGES)可以知道这个数据，这个数据包括：

1、普通文件的page cache

2、block device 的page cache。参考上一节的描述。

3、swap cache。下一节会进一步描述。

对于Cached这个域，我们只关心普通文件的page cache，因此要从page cache的total number中减去buffer cache和swap cache。

六、SwapCached

其实上一节已经提及swap cache了，也归属于page cache中，具体计算如下：

> unsigned long total\_swapcache\_pages(void)   
> {   
> int i;   
> unsigned long ret = 0;
>
> for (i = 0; i < MAX\_SWAPFILES; i++)   
> ret += swapper\_spaces[i].nrpages;   
> return ret;   
> }

和其他的page cache不一样，swap cache并不是为了加快磁盘IO的性能，它是为了解决page frame和swap area之间的同步问题而引入的。例如：一个进程准备swap in一个page的时候，内核的内存回收模块可能同时也在试图将这个page swap out。为了解决这些这些同步问题，内核引入了swap cache这个概念，在任何模块进行swap in或者swap out的时候，都必须首先去swap cache中去看看，而借助page descriptor的PG\_locked的标记，我们可以避免swap中的race condition。

swap cache在具体实现的时候，仍然借用了page cache的概念，每一个swap area都有一个address space，管理该swap device（或者swap file）的page cache。因此，一个swap device的所有swap cache仍然是保存在对应address space的radix tree中（仍然是熟悉的配方，仍然是熟悉的味道啊）。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/gpio_subsystem/pinctrl-and-gpio.html)。
