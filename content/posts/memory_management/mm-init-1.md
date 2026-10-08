---
title: "内存初始化（上）"
date: 2016-10-13T12:05:52+08:00
url: "/memory_management/mm-init-1.html"
gid: "341"
emlog_type: "blog"
summary: "一直以来，我都非常着迷于两种电影拍摄手法：一种是慢镜头，将每一个细节全方位的展现给观众。另外一种就是快镜头，多半是反应一个时代的变迁，从非常长的时间段中，截取几个典型的snapshot，合成在十几秒的镜头中，可以让观众很快的了解一个事物的发展脉络。对应到技术层面，慢镜头有点类似情景分析，把每一行代码都详细的进行解析，了解技术的细节。快镜头类似数据流分析，勾勒一个过程中，数据结构的演化。本文采用了快"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["初始化", "内存管理"]
views: 44446
comment_count: 43
aliases:
  - "/memory_management/341.html"
  - "/341.html"
---

一、前言

一直以来，我都非常着迷于两种电影拍摄手法：一种是慢镜头，将每一个细节全方位的展现给观众。另外一种就是快镜头，多半是反应一个时代的变迁，从非常长的时间段中，截取几个典型的snapshot，合成在十几秒的镜头中，可以让观众很快的了解一个事物的发展脉络。对应到技术层面，慢镜头有点类似情景分析，把每一行代码都详细的进行解析，了解技术的细节。快镜头类似数据流分析，勾勒一个过程中，数据结构的演化。本文采用了快镜头的方法，对内存初始化部分进行描述，不纠缠于具体函数的代码实现，只是希望能给大家一个概略性的印象（有兴趣的同学可以自行研究代码）。BTW，在本文中我们都是基于ARM64来描述体系结构相关的内容。

二、启动之前

在详细描述linux kernel对内存的初始化过程之前，我们必须首先了解kernel在执行第一条语句之前所面临的处境。这时候的内存状况可以参考下图：

![](/content/uploadfile/201610/46d41476331680.gif)

bootloader有自己的方法来了解系统中memory的布局，然后，它会将绿色的kernel image和蓝色dtb image copy到了指定的内存位置上。kernel image最好是位于main memory起始地址偏移TEXT\_OFFSET的位置，当然，TEXT\_OFFSET需要和kernel协商好。kernel image是否一定位于起始的main memory（memory address最低）呢？也不一定，但是对于kernel而言，低于kernel image的内存，kernel是不会纳入到自己的内存管理系统中的。对于dtb image的位置，linux并没有特别的要求。由于这时候MMU是turn off的，因此CPU只能看到物理地址空间。对于cache的要求也比较简单，只有一条：kernel image对应的cache必须clean to PoC，即系统中所有的observer在访问kernel image对应内存地址的时候是一致性的。

三、汇编时代

一旦跳转到linux kernel执行，内核则完全掌控了内存系统的控制权，它需要做的事情首先就是要打开MMU，而为了打开MMU，必须要创建linux kernel正常运行需要的页表，这就是本节的主要内容。

在体系结构相关的汇编初始化阶段，我们会准备二段地址的页表：一段是identity mapping，其实就是把地址等于物理地址的那些虚拟地址mapping到物理地址上去，打开MMU相关的代码需要这样的mapping（别的CPU不知道，但是ARM ARCH强烈推荐这么做的）。第二段是kernel image mapping，内核代码欢快的执行当然需要将kernel running需要的地址（kernel txt、rodata、data、bss等等）进行映射了。具体的映射情况可以参考下图：

![](/content/uploadfile/201610/95491476331682.gif)

turn on MMU相关的代码被放入到一个特别的section，名字是.idmap.text，实际上对应上图中物理地址空间的IDMAP\_TEXT这个block。这个区域的代码被mapping了两次，做为kernel image的一部分，它被映射到了\_\_idmap\_text\_start开始的虚拟地址上去，此外，假设IDMAP\_TEXT block的物理地址是A地址，那么它还被映射到了A地址开始的虚拟地址上去。虽然上图中表示的A地址似乎要大于PAGE\_OFFSET，不过实际上不一定需要这样的关系，这和具体处理器的实现有关。

编译器感知的是kernel image的虚拟地址（左侧），在内核的链接脚本中定义了若干的符号，都是虚拟地址。但是在内核刚开始，没有打开MMU之前，这些代码实际上是运行在物理地址上的，因此，内核起始刚开始的汇编代码基本上是PIC的，首先需要定位到页表的位置，然后在页表中填入kernel image mapping和identity mapping的页表项。页表的起始位置比较好定（bss段之后），但是具体的size还是需要思考一下的。我们要选择一个合适的size，确保能够覆盖kernel image mapping和identity mapping的地址段，然后又不会太浪费。我们以kernel image mapping为例，描述确定Tranlation table size的思考过程。假设48 bit的虚拟地址配置，4k的page size，这时候需要4级映射，地址被分成9（level 0 or PGD） ＋ 9（level 1 or PUD） ＋ 9（level 2 or PMD） ＋ 9（level 3 or PTE） ＋ 12（page offset），假设我们分配4个page分别保存Level 0到level 3的translation table，那么可以建立的最大的地址映射范围是512（level 3中有512个entry） X 4k ＝ 2M。2M这个size当然不理想，无法容纳kernel image的地址区域，怎么办？使用section mapping，让PMD执行block descriptor，这样使用3个page就可以mapping 512 X 2M ＝ 1G的地址空间范围。当然，这种方法有一点副作用就是：PAGE\_OFFSET必须2M对齐。对于16K或者64K的page size，使用section mapping就有点不合适了，因为这时候对齐的要求太高了，对于16K page size，需要32M对齐，对于64K page size，需要512M对齐。不过，这也没有什么，毕竟这时候page size也变大了，不使用section mapping也能覆盖很大区域。例如，对于16K page size，一个16K page size中可以保存2K个entry，因此能够覆盖2K X 16K ＝ 32M的地址范围。对于64K page size，一个64K page size中可以保存8K个entry，因此能够覆盖8K X 64K ＝ 512M的地址范围。32M和512M基本是可以满足需求的。最后的结论：swapper进程（内核空间）需要预留页表的size是和page table level相关，如果使用了section mapping，那么需要预留PGTABLE\_LEVELS - 1个page。如果不使用section mapping，那么需要预留PGTABLE\_LEVELS 个page。

上面的结论起始是适合大部分情况下的identity mapping，但是还是有特例（需要考虑的点主要和其物理地址的位置相关）。我们假设这样的一个配置：虚拟地址配置为39bit，而物理地址是48个bit，同时，IDMAP\_TEXT这个block的地址位于高端地址（大于39 bit能表示的范围）。在这种情况下，上面的结论失效了，因为PGTABLE\_LEVELS 是和虚拟地址的bit数、PAGE\_SIZE的定义相关，而是和物理地址的配置无关。linux kernel使用了巧妙的方法解决了这个问题，大家可以自己看代码理解，这里就不多说了。

一旦设定完了页表，那么打开MMU之后，kernel正式就会进入虚拟地址空间的世界，美中不足的是内核的虚拟世界没有那么大。原来拥有的整个物理地址空间都消失了，能看到的仅仅剩下kernel image mapping和identity mapping这两段地址空间是可见的。不过没有关系，这只是刚开始，内存初始化之路还很长。

四、看见DTB

虽然可以通过kernel image mapping和identity mapping来窥探物理地址空间，但终究是管中窥豹，不了解全局，那么内核是如何了解对端的物理世界呢？答案就是DTB，但是问题来了，这时候，内核还没有为DTB这段内存创建映射，因此，打开MMU之后的kernel还不能直接访问，需要先创建dtb mapping，而要创建address mapping，就需要分配页表内存，而这时候，还没有了解内存布局，内存管理模块还没有初始化，如何来分配内存呢？

下面这张图片给出了解决方案：

![](/content/uploadfile/201610/d2921476331683.gif)

整个虚拟地址空间那么大，可以被平均分成两半，上半部分的虚拟地址空间主要各种特定的功能，而下半部分主要用于物理内存的直接映射。对于DTB而言，我们借用了fixed-mapped address这个概念。fixed map是被linux kernel用来解决一类问题的机制，这类问题的共同特点是：（1）在很早期的阶段需要进行地址映射，而此时，由于内存管理模块还没有完成初始化，不能动态分配内存，也就是无法动态分配创建映射需要的页表内存空间。（2）物理地址是固定的，或者是在运行时就可以确定的。对于这类问题，内核定义了一段固定映射的虚拟地址，让使用fix map机制的各个模块可以在系统启动的早期就可以创建地址映射，当然，这种机制不是那么灵活，因为虚拟地址都是编译时固定分配的。

好，我们可以考虑创建第三段地址映射了，当然，要创建地址映射就要创建各个level中描述符。对于fixed-mapped address这段虚拟地址空间，由于也是位于内核空间，因此PGD当然就是复用swapper进程的PGD了（其实整个系统就一个PGD），而其他level的Translation table则是静态定义的（arch/arm64/mm/mmu.c），位于内核bss段，由于所有的Translation table都在kernel image mapping的范围内，因此内核可以毫无压力的访问，并创建fixed-mapped address这段虚拟地址空间对应的PUD、PMD和PTE的entry。所有中间level的Translation table都是在early\_fixmap\_init函数中完成初始化的，最后一个level则是在各个具体的模块进行的，对于DTB而言，这发生在fixmap\_remap\_fdt函数中。

系统对dtb的size有要求，不能大于2M，这个要求主要是要确保在创建地址映射（create\_mapping）的时候不能分配其他的translation table page，也就是说，所有的translation table都必须静态定义。为什么呢？因为这时候内存管理模块还没有初始化，即便是memblock模块（初始化阶段分配内存的模块）都尚未初始化（没有内存布局的信息），不能动态分配内存。

五、early ioremap

除了DTB，在启动阶段，还有其他的模块也想要创建地址映射，当然，对于这些需求，内核统一采用了fixmap的机制来应对，fixmap的具体信息如下图所示：

![](/content/uploadfile/201610/5c8f1476331684.gif)

从上面这个图片可以看出fix-mapped虚拟地址分成两段，一段是permanent fix map，一段是temporary fixmap。所谓permanent表示映射关系永远都是存在的，例如FDT区域，一旦完成地址映射，内核可以访问DTB之后，这个映射关系一直都是存在的。而temporary fixmap则不然，一般而言，某个模块使用了这部分的虚拟地址之后，需要尽快释放这段虚拟地址，以便给其他模块使用。

你可能会很奇怪，因为传统的驱动模块中，大家通常使用ioremap函数来完成地址映射，为了还有一个early IO remap呢？其实ioremap函数的使用需要一定的前提条件的，在地址映射过程中，如果某个level的Translation tabe不存在，那么该函数需要调用伙伴系统模块的接口来分配一个page size的内存来创建某个level的Translation table，但是在启动阶段，内存管理的伙伴系统还没有ready，其实这时候，内核连系统中有多少内存都不知道的。而early io remap则在early\_ioremap\_init之后就可以被使用了。更具体的信息请参考mm/early\_ioremap.c文件。

结论：如果想要在伙伴系统初始化之前进行设备寄存器的访问，那么可以考虑early IO remap机制。

六、内存布局

完成DTB的映射之后，内核可以访问这一段的内存了，通过解析DTB中的内容，内核可以勾勒出整个内存布局的情况，为后续内存管理初始化奠定基础。收集内存布局的信息主要来自下面几条途径：

（1）choosen node。该节点有一个bootargs属性，该属性定义了内核的启动参数，而在启动参数中，可能包括了mem=nn[KMG]这样的参数项。initrd-start和initrd-end参数定义了initial ramdisk image的物理地址范围。

（2）memory node。这个节点主要定义了系统中的物理内存布局。主要的布局信息是通过reg属性来定义的，该属性定义了若干的起始地址和size条目。

（3）DTB header中的memreserve域。对于dts而言，这个域是定义在root node之外的一行字符串，例如：/memreserve/ 0x05e00000 0x00100000;，memreserve之后的两个值分别定义了起始地址和size。对于dtb而言，memreserve这个字符串被DTC解析并称为DTB header中的一部分。更具体的信息可以参考[device tree基础](/device_model/dt_basic_concept.html)文档，了解DTB的结构。

（4）reserved-memory node。这个节点及其子节点定义了系统中保留的内存地址区域。保留内存有两种，一种是静态定义的，用reg属性定义的address和size。另外一种是动态定义的，只是通过size属性定义了保留内存区域的长度，或者通过alignment属性定义对齐属性，动态定义类型的子节点的属性不能精准的定义出保留内存区域的起始地址和长度。在建立地址映射方面，可以通过no-map属性来控制保留内存区域的地址映射关系的建立。更具体的信息可以阅读参考文献[1]。

通过对DTB中上述信息的解析，其实内核已经基本对内存布局有数了，但是如何来管理这些信息呢？这也就是著名的memblock模块，主要负责在初始化阶段用来管理物理内存。一个参考性的示意图如下：

![](/content/uploadfile/201610/47b01476331686.gif)

内核在收集了若干和memory相关的信息后，会调用memblock模块的接口API（例如：memblock\_add、memblock\_reserve、memblock\_remove等）来管理这些内存布局的信息。内核需要动态管理起来的内存资源被保存在memblock的memory type的数组中（上图中的绿色block，按照地址的大小顺序排列），而那些需要预留的，不需要内核管理的内存被保存在memblock的reserved type的数组中（上图中的青色block，也是按照地址的大小顺序排列）。要想了解进一步的信息，请参考内核代码中的setup\_machine\_fdt和arm64\_memblock\_init这两个函数的实现。

七、看到内存

了解到了当前的物理内存的布局，但是内核仍然只是能够访问部分内存（kernel image mapping和DTB那两段内存，上图中黄色block），大部分的内存仍然处于黑暗中，等待光明的到来，也就是说需要创建这些内存的地址映射。

在这个时间点上，创建内存的地址映射有一个悖论：创建地址映射需要分配内存，但是这时候伙伴系统没有ready，无法动态分配。也许你会说，memblock不是已经ready了吗，不可以调用memblock\_alloc进行物理内存的分配吗？当然可以，memblock\_alloc分配的物理内存仍然需要通过虚拟地址访问，而这些内存都还没有创建地址映射，因此内核一旦访问memblock\_alloc分配的物理内存，悲剧就会发生了。

怎么办呢？内核采用了一个巧妙的办法：那就是控制创建地址映射，memblock\_alloc分配页表内存的顺序。也就是说刚开始的时候创建的地址映射不需要页表内存的分配，当内核需要调用memblock\_alloc进行页表物理地址分配的时候，很多已经创建映射的内存已经ready了，这样，在调用create\_mapping的时候不需要分配页表内存。更具体的解释参考下面的图片：

![](/content/uploadfile/201610/634b1476331687.gif)

我们知道，在内核编译的时候，在BSS段之后分配了几个page用于swapper进程地址空间（内核空间）的映射，当然，由于kernel image不需要mapping那么多的地址，因此swapper进程translation table的最后一个level中的entry不会全部的填充完毕。换句话说：swapper进程页表可以支持远远大于kernel image mapping那一段的地址区域，实际上，它可以支持的地址段的size是SWAPPER\_INIT\_MAP\_SIZE。为（PAGE\_OFFSET，PAGE\_OFFSET＋SWAPPER\_INIT\_MAP\_SIZE）这段虚拟内存创建地址映射，mapping到（PHYS\_OFFSET，PHYS\_OFFSET＋SWAPPER\_INIT\_MAP\_SIZE）这段物理内存的时候，调用create\_mapping不会发生内存分配，因为所有的页表都已经存在了，不需要动态分配。

一旦完成了（PHYS\_OFFSET，PHYS\_OFFSET＋SWAPPER\_INIT\_MAP\_SIZE）这段物理内存的地址映射，这时候，终于可以自由使用memblock\_alloc进行内存分配了，当然，要进行限制，确保分配的内存位于（PHYS\_OFFSET，PHYS\_OFFSET＋SWAPPER\_INIT\_MAP\_SIZE）这段物理内存中。完成所有memory type类型的memory region的地址映射之后，可以解除限制，任意分配memory了。而这时候，所有memory type的地址区域（上上图中绿色block）都已经可见，而这些宝贵的内存资源就是内存管理模块需要管理的对象。具体代码请参考paging\_init--->map\_mem函数的实现。

八、结束语

目前为止，所有为内存管理做的准备工作已经完成：收集了整个内存布局的信息，memblock模块中已经保存了所有需要管理memory region的信息，同时，系统也为所有的内存（reserved除外）创建了地址映射。虽然整个内存管理系统没有ready，但是通过memblock模块已经可以在随后的初始化过程中进行动态内存的分配。 有了这些基础，随后就是真正的内存管理系统的初始化了，我们下回分解。

参考文献：

1、Documentation/devicetree/bindings/reserved-memory/reserved-memory.txt

2、linux4.4.6内核代码
