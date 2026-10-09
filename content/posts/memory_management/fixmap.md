---
title: "Fix-Mapped Addresses"
date: 2016-09-09T12:44:03+08:00
url: "/memory_management/fixmap.html"
gid: "333"
emlog_type: "blog"
summary: "某天，wowo同学突然来了一句：如果要在start_kernel中点LED，ioremap在什么时间点才能调用呢？我想他应该是想通过点 LED灯来调试start_kernel之后的初始化的代码（例如DTB解析部分的代码）。那天，我们两个花了二十分钟的时间，讨论相关的问题，我觉得很 有意思，因此决定写fix mapped address这样的一份文档。 在汇编代码中，由于没有打开MMU，想怎么访问外"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["fixmap"]
views: 25059
comment_count: 9
aliases:
  - "/memory_management/333.html"
  - "/333.html"
---

一、前言

某天，wowo同学突然来了一句：如果要在start\_kernel中点LED，ioremap在什么时间点才能调用呢？我想他应该是想通过点LED灯来调试start\_kernel之后的初始化的代码（例如DTB解析部分的代码）。那天，我们两个花了二十分钟的时间，讨论相关的问题，我觉得很有意思，因此决定写fix mapped address这样的一份文档。

在汇编代码中，由于没有打开MMU，想怎么访问外设都很简单，直接使用物理地址即可，然而，进入start kernel之后（打开了MMU），想要访问硬件都是那么的不方便，至少需要通过ioremap获取了虚拟地址之后才可以访问。但是，实际上，在内核的启动的初始阶段，内存管理子系统还没有ready，ioremap还不能调用（在mm\_init之后可以正常使用）。

实际上，这个需求是和early ioremap模块相关，此外，还有一些其他的需求，内核合并了这些需求并提出了fix mapped address的概念。本文就是描述关于fix mapped address的方方面面，BTW，本文的代码来自4.4.6内核，体系结构相关的代码依然选择的是ARM64。

二、什么是fixmap？

Fix map中的fix指的是固定的意思，那么固定什么东西呢？其实就是虚拟地址是固定的，也就是说，有些虚拟地址在编译（compile-time）的时候就固定下来了，而这些虚拟地址对应的物理地址不是固定的，是在kernel启动过程中被确定的。为了方便大家理解fixmap，我们提供一个具体的例子：DTB image的处理。

实际上DTB的处理一开始并没有使用fixmap，而是放在了kernel image附近。更具体的要求是必须放在kernel image起始地址的512M内，8字节对齐，dtb image不能越过2M section size的边界。之所以这么要求，主要是想借用kernel image页表的“东风”，反正建立kernel image所需要的PGD/PUD/PMD页表都已经静态分配了，对dtb image的要求可以不需要建立新的页表，只是在原有的页表中增加一个entry而已，不过这样的设计存在下面的问题：

（1）对dtb image的位置有限制，不是很灵活（谁不想自由自在呢？bootload copy dtb img的时候当然想了无牵挂啊）。

（2）对dtb image的位置检查在head.S中，需要汇编实现（谁想写汇编啊，用c实现多买易懂啊，可维护性，可移植性多么好啊）。

现在，既然内核有了early fixmap的支持，那么上面的限制都可以放宽了。整个dtb image的处理过程如下：

（1）bootloader copy dtb image到memory的某个位置上。具体的位置随便，当然还是要满足8字节对齐，dtb image不能越过2M section size的边界的要求，毕竟我们也想一条section mapping就搞定dtb image。

（2）bootload通过寄存器x0传递dtb image的物理地址，dtb image的虚拟地址在编译kernel image的时候就确定了。

（3）汇编初始化阶段不对dtb image做任何处理

（4）在start kernel之后的初始化代码中（具体在setup\_arch--->setup\_machine\_fdt中），创建dtb image的相关Translation tables，之后就可以自由的访问dtb image了。

三、为何有fixmap这个概念？

动态分配虚拟地址以及建立地址映射是一个复杂的过程，在内核完全启动之后，内存管理可以提供各种丰富的API让内核的其他模块可以完成虚拟地址分配和建立地址映射的功能，但是，在内核的启动过程中，有些模块需要使用虚拟内存并mapping到指定的物理地址上，而且，这些模块也没有办法等待完整的内存管理模块初始化之后再进行地址映射。因此，linux kernel固定分配了一些fixmap的虚拟地址，这些地址有固定的用途，使用该地址的模块在初始化的时候，讲这些固定分配的地址mapping到指定的物理地址上去。

最直观的需求来自初始化代码的调试，想一想当我们来到start\_kernel的时候我们面临的处境：

（1）我们不能访问全部的内存，只能访问kernel image附近的memory。

（2）我们不能访问任何的硬件，所有的io memory还没有mapping

想要通过串口控制台输出错误信息？sorry，现在离console驱动的初始化还早着呢。想点个LED灯看看内核运行情况？sorry，ioremp函数需要kmalloc分配内存，但是伙伴系统还没有初始化呢。怎么办？一个最简洁的方法就是简化虚拟内存的分配和管理（ioremp中使用的管理虚拟内存地址的方法太重了），而最简单的方法就是fix virtual address。

四、fixmap的具体位置在那里？

fixmap的地址区域位于FIXADDR\_START和FIXADDR\_TOP之间，具体可以参考下图：

![](/content/uploadfile/201609/c0c81473396332.gif)

上图中，红色框的block就是fixmap address的具体位置。

五、fixmap具体应用在哪些场景？

fixmap的地址区域有被进一步细分，如下：

> enum fixed\_addresses {   
> FIX\_HOLE,   
> FIX\_FDT\_END,   
> FIX\_FDT = FIX\_FDT\_END + FIX\_FDT\_SIZE / PAGE\_SIZE - 1,
>
> FIX\_EARLYCON\_MEM\_BASE,   
> FIX\_TEXT\_POKE0,   
> \_\_end\_of\_permanent\_fixed\_addresses,
>
> FIX\_BTMAP\_END = \_\_end\_of\_permanent\_fixed\_addresses,   
> FIX\_BTMAP\_BEGIN = FIX\_BTMAP\_END + TOTAL\_FIX\_BTMAPS - 1,   
> \_\_end\_of\_fixed\_addresses   
> };

由定义可知，fixmap地址区域又分成了两个部分，一部分叫做permanent fixed address，是用于具体的某个内核模块的，使用关系是永久性的。另外一个叫做temporary fixed address，各个内核模块都可以使用，用完之后就释放，模块和虚拟地址之间是动态的关系。

permanent fixed address主要涉及的模块包括：

（1）dtb解析模块。

（2）early console模块。标准的串口控制台驱动的初始化在整个kernel初始化过程中是很靠后的事情了，如果能够在kernel启动阶段的初期就有一个console，能够输出各种debug信息是多买美妙的事情啊，early console就能满足你的这个愿望，这个模块是使用early param来初始化该模块的功能的，因此可以很早就投入使用，从而协助工程师了解内核的启动过程。

（3）动态打补丁的模块。正文段一般都被映射成read only的，该模块可以使用fix mapped address来映射RW的正文段，从动态修改程序正文段，从而完成动态打补丁的功能。

temporary fixed address主要用于early ioremap模块。linux kernel在fix map区域的虚拟地址空间中开了FIX\_BTMAPS\_SLOTS个的slot（每个slot的size是NR\_FIX\_BTMAPS），内核中的模块都能够通过early\_ioremap、early\_iounmap的接口来申请或者释放对某个slot 虚拟地址的使用。

*原创文章，转发请注明出处。蜗窝科技*
