---
title: "页面回收的基本概念"
date: 2017-08-25T19:01:35+08:00
url: "/memory_management/page_reclaim_basic.html"
gid: "407"
emlog_type: "blog"
summary: "本文主要介绍了一些page reclaim机制中的基本概念。这份文档其实也可以看成阅读ULK第17章第一小节的一个读书笔记。虽然ULK已经读了很多遍，不过每一遍还是觉得有收获。Linux内核虽然不断在演进，但是页面回收的基本概念是不变的，所以ULK仍然值得内核发烧友仔细品味。"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["页面回收"]
views: 15314
comment_count: 1
aliases:
  - "/memory_management/407.html"
  - "/407.html"
---

本文主要介绍了一些page reclaim机制中的基本概念。这份文档其实也可以看成阅读ULK第17章第一小节的一个读书笔记。虽然ULK已经读了很多遍，不过每一遍还是觉得有收获。Linux内核虽然不断在演进，但是页面回收的基本概念是不变的，所以ULK仍然值得内核发烧友仔细品味。

一、什么是page frame reclaiming？

在用户进程的内存使用上，Linux内核并没有严格的限制，其实思路是：当系统负荷小的时候，内存都是位于各种cache中，以便提高性能。当系统负荷重（进程数目非常多）的时候，cache中的内存被收回，然后用于进程地址空间的创建和映射。在这样思路的指导下，一开始，内核大手大脚，一直从伙伴系统的free list上分配page frame给用户进程或者各种kernel cache使用，但是系统内存终归是有限的，当伙伴系统的空闲内存下降到一定的水位的时候，系统会从用户进程或者kernel cache中回收page frame到伙伴系统，以便满足新的内存分配的需求，这个过程就是page frame reclaiming。一言以蔽之，page frame reclaiming就是保证系统的空闲内存在一个指定的水位之上。

二、什么时候启动page frame reclaiming？

能不能等到空闲内存用尽之后才启动page frame reclaiming呢？不行，因为在page frame reclaiming的过程中也会消耗内存（例如在页面回收过程中，我们可能会将page frame的数据交换到磁盘，因此需要分配buffer head数据结构，完成IO操作），因此我们必须在伙伴系统中保持一定的水位，以便让page frame reclaiming机制正常工作，以便回收更多的内存，让系统运转下去，否则系统会crash掉。

三、哪些场景可以触发page frame reclaiming？

当分配内存失败的时候触发页面回收是最直观的想法，然而内核的场景没有那么简单，例如在中断上下文中分配内存，这时候我们不能触发page frame reclaiming，因为这时候我们不能阻塞当前进程。此外，有些内存分配的场景是发生在持锁之后（以便对某些资源进行排他性的访问），这时候，我们也不能激活IO操作，进行内存回收。

因此，总结起来，内核在内存回收的思路就是：系统在分配内存的时候就进行检查，如果有需要就唤醒kswapd，让系统的空闲内存的数量保持在一个水平之上，以免将自己逼入绝境。如果没有办法，的确进入了绝境（分配内存失败），那么就直接触发页面回收。具体的场景包括：

1、synchronous page reclaim，即当遭遇分配内存失败的时候，一言不合，然后直接调用page frame reclaiming进行回收。例如：在分配page buffer的时候（alloc\_page\_buffers），如果分配不成功，直接调用free\_more\_memory进行内存回收。或者在调用\_\_alloc\_pages的时候，如果分配不成功，直接调用try\_to\_free\_pages进行内存回收。当然，其实free\_more\_memory也是调用try\_to\_free\_pages来实现页面回收的。

2、Suspend to disk（Hibernation）的场景。系统hibernate的时候需要大量内存，这时候会调用shrink\_all\_memory来回收指定数目的page frame。

3、kswapd场景。Kswapd是一个专门用来进行页面回收的内核线程。

4、slab内存分配器会定时的queue work到system\_wq上去，从而会周期性的调用cache\_reap来回收slab上的空闲内存。

四、页面回收的策略为何？

首先我们需要对page frame进行分类，主要分成4类：

1、 没有办法回收的page frame。包括空闲页面（已经在free list上面，也就不需要劳驾page frame reclaim机制了）、保留页面（设定了PG\_reserved，例如内核正文段、数据段等等）、内核动态分配的page frame、用户进程的内核栈上的page frame、临时性的被锁定的page frame（即设定了PG\_locked flag，例如在进行磁盘IO的时候）、mlocked page frame（有VM\_LOCKED标识的VMA）

2、 可以交换到磁盘的page frame（swappable）。用户空间的匿名映射页面（用户进程堆和栈上的page frame）、tmpfs的page frame。

3、 可以同步到磁盘的page frame（syncable）。用户空间的文件映射（file mapped）页面，page cache中的page frame（其内容会对应到某个磁盘文件），block device的buffered cache、disk cache中的page frame（例如inode cache）

4、 可以直接释放的page frame。各种内存cache（例如 slab内存分配器）中还没有使用的那些page frame、没有使用的dentry cache。

上面的第二类和第三类有些类似， 其page frame都有后备文件或者磁盘，不过我们可以这么区分。Swappable的page frame，其数据的最终地点就是内存，其后备文件或者磁盘只是为了延伸内存的容量。Syncable的page frame，其数据的最终地点就是磁盘，内存只不过是为了加快速度而已。因此，当回收swappable的页面的时候，需要将page frame的数据保存到后备的磁盘或者文件。而当回收syncable页面的时候，要看page frame是否是dirty的，如果dirty，则需要磁盘操作，否则可以直接回收。

圈定进行页面回收的那些候选page frame很容易（即上面的2、3、4类型的page frame），但是怎么考虑页面回收的先后顺序呢？Linux内核设定的基本规则如下：

1、 尽量不要修改page table。例如回收各种没有使用的内核cache的时候，我们直接回收，根本不需要修改页表项。而用户空间进程的页面回收往往涉及将对应的pte条目修改为无效状态。

2、 除非调用mlock将page锁定，否则所有的用户空间对应的page frame都应该可以被回收。

3、 如果一个page frame被多个进程共享，那么我们需要清除所有的pte entry，之后才能回收该页面。

4、 不要回收那些最近使用（访问）过的page frame，或者说优先回收那些最近没有访问的page frame。

5、 尽量先回收那些不需要磁盘IO操作的page frame。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/memory_management/page_reclaim_basic.html)。
