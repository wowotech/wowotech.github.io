---
title: "内存初始化代码分析（一）：identity mapping和kernel image mapping"
date: 2016-11-10T19:07:31+08:00
url: "/memory_management/__create_page_tables_code_analysis.html"
gid: "352"
emlog_type: "blog"
summary: "\r\n\t本文没有什么框架性的东西，就是按照__create_page_tables代码的执行路径走读一遍，记录在初始化阶段，内核是如何创建内核运行需要的页表过程。想要了解一些概述性的、框架性的东西可以参考内存初始化文档。\r\n\r\n\r\n\t本文的代码来自ARM64，内核版本是4.4.6，此外，阅读本文最好熟悉ARMv8中翻译表描述符的格式。\r\n"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["__create_page_tables"]
views: 31792
comment_count: 11
aliases:
  - "/memory_management/352.html"
  - "/352.html"
---

一、前言

本文没有什么框架性的东西，就是按照\_\_create\_page\_tables代码的执行路径走读一遍，记录在初始化阶段，内核是如何创建内核运行需要的页表过程。想要了解一些概述性的、框架性的东西可以参考[内存初始化](/memory_management/mm-init-1.html)文档。

本文的代码来自ARM64，内核版本是4.4.6，此外，阅读本文最好熟悉ARMv8中翻译表描述符的格式。

二、create\_table\_entry

这个宏定义主要是用来创建一个中间level的translation table中的描述符。如果用linux的术语，就是创建PGD、PUD或者PMD的描述符。如果用ARM64术语，就是创建L0、L1或者L2的描述符。具体创建哪一个level的Translation table descriptor是由tbl参数指定的，tbl指向了该translation table的内存。virt参数给出了要创建地址映射的那个虚拟地址，shift参数以及ptrs参数是和具体在哪一个entry中写入描述符有关。我们知道，在定位页表描述的时候，我们需要截取虚拟地址中的一部分做为offset（index）来定位描述符，实际上，虚拟地址右移shift，然后截取ptrs大小的bit field就可以得到entry index了。tmp1和tmp2是临时变量。create\_table\_entry的代码如下：

> .macro create\_table\_entry, tbl, virt, shift, ptrs, tmp1, tmp2   
> lsr \tmp1, \virt, #\shift   
> and \tmp1, \tmp1, #\ptrs - 1 // table index－－－－－－－－－－－－－－－－－－－（1）   
> add \tmp2, \tbl, #PAGE\_SIZE－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> orr \tmp2, \tmp2, #PMD\_TYPE\_TABLE－－－－－－－－－－－－－－－－－－－－－（3）   
> str \tmp2, [\tbl, \tmp1, lsl #3]－－－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> add \tbl, \tbl, #PAGE\_SIZE－－－－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> .endm

（1）tmp1中保存virt地址对应在Translation table中的entry index。

（2）初始阶段的页表页表定义在链接脚本中，如下：

> BSS\_SECTION(0, 0, 0)
>
> . = ALIGN(PAGE\_SIZE);   
> idmap\_pg\_dir = .;   
> . += IDMAP\_DIR\_SIZE;   
> swapper\_pg\_dir = .;   
> . += SWAPPER\_DIR\_SIZE;

初始阶段的页表（PGD/PUD/PMD/PTE）都是排列在一起的，每一个占用一个page。也就是说，如果create\_table\_entry当前操作的是PGD，那么tmp2这时候保存了下一个level的页表，也就是PUD了。

（3）这一步是合成描述符的数值。光有下一级translation table的地址不行，还要告知该描述符是否有效（bit 0），该描述符的类型是哪一种类型（bit 1）。对于中间level的页表，该描述符不可能是block entry，只能是table type的描述符，因此该描述符的最低两位是0b11。

> #define PMD\_TYPE\_TABLE (\_AT(pmdval\_t, 3) << 0)

（4）这是最关键的一步，将描述符写入页表中。之所以有“lsl #3”操作，是因为一个描述符占据8个Byte。

（5）将translation table的地址移到next level，以便进行下一步设定。

三、create\_pgd\_entry

从字面上看，create\_pgd\_entry似乎是用来在PGD中创建一个描述符，但是，实际上该函数不仅仅创建PGD中的描述符，如果需要下一级的translation table，例如PUD、PMD，也需要同时建立，最终的要求是能够完成所有中间level的translation table的建立（其实每个table中都是只建立了一个描述符），仅仅留下PTE，由其他代码来完成。该函数需要四个参数：tbl是pgd translation table的地址，具体要创建哪一个地址的描述符由virt指定，tmp1和tmp2是临时变量，create\_pgd\_entry具体代码如下：

> .macro create\_pgd\_entry, tbl, virt, tmp1, tmp2   
> create\_table\_entry \tbl, \virt, PGDIR\_SHIFT, PTRS\_PER\_PGD, \tmp1, \tmp2－－－－－－－（1）   
> #if SWAPPER\_PGTABLE\_LEVELS > 3－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> create\_table\_entry \tbl, \virt, PUD\_SHIFT, PTRS\_PER\_PUD, \tmp1, \tmp2－－－－－－－－（3）   
> #endif   
> #if SWAPPER\_PGTABLE\_LEVELS > 2－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> create\_table\_entry \tbl, \virt, SWAPPER\_TABLE\_SHIFT, PTRS\_PER\_PTE, \tmp1, \tmp2   
> #endif   
> .endm

（1）create\_table\_entry 在上一节已经描述了，这里通过调用该函数在PGD中为虚拟地址virt创建一个table type的描述符。

（2）SWAPPER\_PGTABLE\_LEVELS这个宏定义和ARM64\_SWAPPER\_USES\_SECTION\_MAPS相关，而这个宏在蜗窝已经[有一篇文章](/armv8a_arch/create_page_tables.html)描述，这里就不说了。SWAPPER\_PGTABLE\_LEVELS其实定义了swapper进程地址空间的页表的级数，可能3，也可能是2，具体中间的Translation table有多少个level是和配置相关的，如果是section mapping，那么中间level包括PGD和PUD就OK了，PMD是最后一个level。如果是page mapping，那么需要PGD、PUD和PMD这三个中间level，PTE是最后一个level。当然，如果整个page level是3或者2的时候，也有可能不存在PUD或者PMD这个level。

（3）当SWAPPER\_PGTABLE\_LEVELS > 3的时候，需要创建PUD这一级的Translation table。

（4）当SWAPPER\_PGTABLE\_LEVELS > 2的时候，需要创建PMD这一级的Translation table。

上面太枯燥了，我们给出一些实例：

例子1：当虚拟地址是48个bit，4k page size，这时候page level等于4，映射关系是PGD（L0）--->PUD（L1）--->PMD（L2）--->Page table（L3）--->page，但是如果采用了section mapping（4k的page一定会采用section mapping），映射关系是PGD（L0）--->PUD（L1）--->PMD（L2）--->section。在create\_pgd\_entry函数中将创建PGD和PUD这两个中间level。

例子2：当虚拟地址是48个bit，16k page size（不能采用section mapping），这时候page level等于4，映射关系是PGD（L0）--->PUD（L1）--->PMD（L2）--->Page table（L3）--->page。在create\_pgd\_entry函数中将创建PGD、PUD和PMD这三个中间level。

例子3：当虚拟地址是39个bit，4k page size，这时候page level等于3，映射关系是PGD（L1）--->PMD（L2）--->Page table（L3）--->page。由于是4k page，因此采用section mapping，映射关系是PGD（L1）--->PMD（L2）--->section。在create\_pgd\_entry函数中将创建PGD这一个中间level。

四、create\_block\_map

create\_block\_map的名字起得不错，该函数就是在tbl指定的Translation table中建立block descriptor以便完成address mapping。具体mapping的内容是将start 到 end这一段VA mapping到phys开始的PA上去，代码如下：

> .macro create\_block\_map, tbl, flags, phys, start, end   
> lsr \phys, \phys, #SWAPPER\_BLOCK\_SHIFT   
> lsr \start, \start, #SWAPPER\_BLOCK\_SHIFT   
> and \start, \start, #PTRS\_PER\_PTE - 1 // table index   
> orr \phys, \flags, \phys, lsl #SWAPPER\_BLOCK\_SHIFT // table entry   
> lsr \end, \end, #SWAPPER\_BLOCK\_SHIFT   
> and \end, \end, #PTRS\_PER\_PTE - 1 // table end index   
> 9999: str \phys, [\tbl, \start, lsl #3] // store the entry   
> add \start, \start, #1 // next entry   
> add \phys, \phys, #SWAPPER\_BLOCK\_SIZE // next block   
> cmp \start, \end   
> b.ls 9999b   
> .endm

五、\_\_create\_page\_tables

1、准备阶段

> \_\_create\_page\_tables:   
> adrp x25, idmap\_pg\_dir－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> adrp x26, swapper\_pg\_dir   
> mov x27, lr
>
> mov x0, x25－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> add x1, x26, #SWAPPER\_DIR\_SIZE   
> bl \_\_inval\_cache\_range
>
> mov x0, x25－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> add x6, x26, #SWAPPER\_DIR\_SIZE   
> 1: stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> cmp x0, x6   
> b.lo 1b
>
> ldr x7, =SWAPPER\_MM\_MMUFLAGS－－－－－－－－－－－－－－－－－（4）

（1）取idmap\_pg\_dir这个符号的物理地址，保存到x25。取swapper\_pg\_dir这个符号的物理地址，保存到x26。这段代码没有什么特别要说明的，除了adrp这条指令。adrp是计算指定的符号地址到run time PC值的相对偏移（不过，这个offset没有那么精确，是以4K为单位，或者说，低12个bit是0）。在指令编码的时候，立即数（也就是 offset）占据21个bit，此外，由于偏移计算是按照4K进行的，因此最后计算出来的符号地址必须要在该指令的－4G和4G之间。由于执行该指令的 时候，还没有打开MMU，因此通过adrp获取的都是物理地址，当然该物理地址的低12个bit是全零的。此外，由于在链接脚本中 idmap\_pg\_dir和swapper\_pg\_dir是page size aligned，因此使用adrp指令也是OK的。

（2）这段代码是要进行invalid cache的操作了，具体要操作的范围就是identity mapping和kernel image mapping所对应的页表区域，起始地址是idmap\_pg\_dir，结束地址是swapper\_pg\_dir＋SWAPPER\_DIR\_SIZE。

为什么要调用\_\_inval\_cache\_range来invalidate idmap\_pg\_dir和swapper\_pg\_dir对应页表空间的cache呢？根据boot protocol，代码执行到此，对于cache的要求是kernel image对应的那段空间的cache line是clean到PoC的，不过idmap\_pg\_dir和swapper\_pg\_dir对应页表空间不属于kernel image的一部分，因此其对应的cacheline很可能有一些旧的，无效的数据，必须要清理掉。

（3）将idmap和swapper页表内容设定为0是有意义的。实际上这些translation table中的大部分entry都是没有使用的，PGD和PUD都是只有一个entry是有用的，而PMD中有效的entry数目是和mapping的地 址size有关。将页表内容清零也就是意味着将页表中所有的描述符设定为invalid（描述符的bit 0指示是否有效，等于0表示无效描述符）。

（4）要创建mapping除了需要VA和PA，还需要memory attribute的参数，这个参数定义如下：

> #if ARM64\_SWAPPER\_USES\_SECTION\_MAPS   
> #define SWAPPER\_MM\_MMUFLAGS (PMD\_ATTRINDX(MT\_NORMAL) | SWAPPER\_PMD\_FLAGS)   
> #else   
> #define SWAPPER\_MM\_MMUFLAGS (PTE\_ATTRINDX(MT\_NORMAL) | SWAPPER\_PTE\_FLAGS)   
> #endif

为了理解这些定义，需要理解block type和page type的描述符的格式，大家自行对照ARMv8文档，这里就不贴图了。SWAPPER\_MM\_MMUFLAGS这个flag其实定义了要映射地址的memory attribut。对于kernel image这一段内存，当然是普通内存，因此其中的MT\_NORMAL就是表示后续的地址映射都是为normal memory而创建的。其他的flag定义如下：

> #define SWAPPER\_PTE\_FLAGS (PTE\_TYPE\_PAGE | PTE\_AF | PTE\_SHARED)   
> #define SWAPPER\_PMD\_FLAGS (PMD\_TYPE\_SECT | PMD\_SECT\_AF | PMD\_SECT\_S)

PMD\_SECT\_AF（PTE\_AF）中的AF是access flag的缩写，这个bit用来表示该entry是否第一次使用（当程序访问对应的page或者section的时候，就会使用该entry，如果从来没有被访问过，那么其值等于0，否者等于1）。该bit主要被操作系统用来跟踪一个page是否被使用过（最近是否被访问），当该page首次被创建的时候，AF等于0，当代码第一次访问该page的时候，会产生MMU fault，这时候，异常处理函数应该设定AF等于1，从而阻止下一次访问该page的时候产生MMU Fault。在这里，kernel image对应的page，其描述符的AF bit都设定为1，表示该page当前状态是actived（最近被访问），因为只有用户空间进程的page才会根据AF bit来确定哪些page被swap out，而kernel image对应的page是always actived的。

PMD\_SECT\_S（PTE\_SHARED）对应shareable attribute bits，这个两个bits定义了该page的shareable attribute。那么是shareable attribute呢？shareable attribute定义了memory location被多个系统中的bus master共享的属性。具体定义如下：

|  |  |
| --- | --- |
| SH[1:0] | Normal memory |
| 00 | Non-shareable |
| 01 | 无效 |
| 10 | outer shareable |
| 11 | inner shareble |

这里memory attribute中SH被设定为0b11，即inner shareable。如果一个page被标注为inner shareable，那么在inner shareable domain中，所有的bus mast访问该page中的memory都是coherent的（HW会处理cache coherence问题），软件不需要考虑cache。一般而言，所有cpu core组成了inner shareable domain，也就是说，对于kernel direct mapping而言，其对应的内存对所有的cpu core的访问都是coherent的。

memory attribute中其他的flag都没有显式指定，也就是说它们的值都是0，我们可以简单过一下。AP的值是0，表示该page对kernel mode（EL1）是read/write的，对于userspace（EL0），是不允许访问的。nG bit是0，表示该地址翻译是全局的，不是process-specific的，这也合理，内核page的映射当然是全局的了。

2、建立identity mapping

> mov x0, x25 －－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> adrp x3, \_\_idmap\_text\_start －－－－－－－－－－－－－－－－－－－－（2）
>
> #ifndef CONFIG\_ARM64\_VA\_BITS\_48－－－－－－－－－－－－－－－－－－－－－（3）   
> #define EXTRA\_SHIFT (PGDIR\_SHIFT + PAGE\_SHIFT - 3)－－－－－－－－－－－（4）   
> #define EXTRA\_PTRS (1 << (48 - EXTRA\_SHIFT)) －－－－－－－－－－－－－－－（5）
>
> #if VA\_BITS != EXTRA\_SHIFT－－－－－－－－－－－－－－－－－－－－－－－－－（6）   
> #error "Mismatch between VA\_BITS and page size/number of translation levels"   
> #endif
>
> adrp x5, \_\_idmap\_text\_end－－－－－－－－－－－－－－－－－－－－－－－－－（7）   
> clz x5, x5   
> cmp x5, TCR\_T0SZ(VA\_BITS) －－－－－－－－－－－－－－－－－－－－－－（8）   
> b.ge 1f
>
> adr\_l x6, idmap\_t0sz－－－－－－－－－－－－－－－－－－－－－－－－－－－（9）   
> str x5, [x6]   
> dmb sy   
> dc ivac, x6
>
> create\_table\_entry x0, x3, EXTRA\_SHIFT, EXTRA\_PTRS, x5, x6－－－－－－－－（10）   
> 1:   
> #endif
>
> create\_pgd\_entry x0, x3, x5, x6－－－－－－－－－－－－－－－－－－－－－－－（11）   
> mov x5, x3 // \_\_pa(\_\_idmap\_text\_start)   
> adr\_l x6, \_\_idmap\_text\_end // \_\_pa(\_\_idmap\_text\_end)   
> create\_block\_map x0, x7, x3, x5, x6－－－－－－－－－－－－－－－－－－－－－（12）

（1）x0保存了idmap\_pg\_dir变量的物理地址，也就是identity mapping的PGD。

（2）x3保存了\_\_idmap\_text\_start的物理地址，对于identity mapping而言，x3也保存了虚拟地址，因为虚拟地址是等于物理地址的。

（3）基本上创建identity mapping是没有什么大问题的，但是，如果物理内存的地址位于非常高的位置，那么在进行identity mapping就有问题了，因为有可能你配置的VA\_BITS不够大，超出了虚拟地址的范围。这时候，就需要扩展virtual address range了。当然，如果配置了48bits的VA\_BITS就不存在这样的问题了，因为ARMv8最大支持的VA BITS就是48个，根本不可能扩展了。

（4）在虚拟地址地址不是48 bit，而系统内存的物理地址又放到了非常非常高的位置，这时候，为了完成identity mapping，我们必须要扩展虚拟地址，那么扩展多少呢？扩展到48个bit。扩展之后，增加了一个EXTRA的level，地址映射关系是EXTRA--->PGD--->……，其中EXTRA\_SHIFT等于(PGDIR\_SHIFT + PAGE\_SHIFT - 3)。

（5）扩展之后，地址映射多个一个level，我们称之EXTRA level，该level的Translation table中有多少个entry呢？EXTRA\_PTRS给出了答案。

（6）其实现行的linux kernel中，对地址映射是有要求的，即要求PGD是满的。例如：48 bit的虚拟地址，4k的page size，对应的映射关系是PGD(9-bit）＋PUD(9-bit）＋PMD(9-bit）＋PTE(9-bit）＋page offset(12-bit），对于42bit的虚拟地址，64k的page size，对应的映射关系是PGD(13-bit）＋ PTE(13-bit）＋ page offset(16-bit）。这两种例子有一个共同的特点就是PGD中的entry数目都是满的，也就是说索引到PGD的bit数目都是PAGE\_SIZE-3。如果不满足这个关系，linux kernel会认为你的配置是有问题的。注意：这是内核的要求，实际上ARM64的硬件没有这么要求。

正因为正确的配置下，PGD都是满的，因此扩展之后EXTRA\_SHIFT一定是等于VA\_BITS的，否则一定是你的配置有问题。我们延续上一个实例来说明如何扩展虚拟地址的bit数目。对于42bit的虚拟地址，64k的page size，扩展之后，虚拟地址是48个bit，地址映射关系是EXTRA（6-bit）＋ PGD(13-bit）＋ PTE(13-bit）＋ page offset(16-bit）。

（7）x5保存了\_\_idmap\_text\_end的物理地址，之所以这么做是因为需要确定identity mapping的最高的物理地址，计算该物理地址的前导0有多少个，从而可以判断该地址是否是位于物理地址空间中比较高的位置。

（8）宏定义TCR\_T0SZ可以计算给定虚拟地址数目下，前导0的个数。如果虚拟地址是48的话，那么前导0是16个。如果当前物理地址的前导0的个数（x5的值）还有小于当前配置虚拟地址的前导0的个数，那么就需要扩展。

（9）OK，现在进入需要扩展的分支，当然，具体要配置虚拟地址是通过TCR\_EL1寄存器中的T0SZ域进行的，现在还不是时候（具体的设定在\_\_cpu\_setup函数中），这里，我们只要设定idmap\_t0sz这个变量值就OK了，在\_\_cpu\_setup函数中会从该变量取值并设定到TCR\_EL1寄存器中的。代码中，x6是idmap\_t0sz变量的物理地址，x5是物理地址前导0的个数，将其保存到idmap\_t0sz变量中。

（10）创建extra translation table的entry。具体传递的参数如下：

x0：页表地址idmap\_pg\_dir

x3：准备映射的虚拟地址（虽然x3保存的是物理地址，但是identity mapping嘛，VA和PA都是一样的）

EXTRA\_SHIFT：正常建立最高level mapping的时候， shift是PGDIR\_SHIFT，但是，由于物理地址位置太高，需要额外的映射，因此这里需要再加上一个level的mapping，因此shift需要PGDIR\_SHIFT ＋ （PAGE\_SHIFT - 3）。

EXTRA\_PTRS：增加了一个level的Translation table，我们需要确定这个增加level的Translation table中包含的描述符的数目，EXTRA\_PTRS给出了这个参数。

（11）create\_pgd\_entry这个函数上面解释过了，建立各个中间level的table描述符。

（12）创建最后一个level translation table的entry。该entry可能是page descriptor，也可能是block descriptor，具体传递的参数如下：

x0：指向最后一个level的translation table

x7：要创建映射的memory attribute

x3：物理地址

x5：虚拟地址的起始地址（其实和x3一样）

x6：虚拟地址的结束地址

3、创建kernel direct mapping

> mov x0, x26 －－－－－－－－－－－－－－－－－－－－－－－－（1）   
> mov x5, #PAGE\_OFFSET－－－－－－－－－－－－－－－－－－－－－－－（2）   
> create\_pgd\_entry x0, x5, x3, x6－－－－－－－－－－－－－－－－－－－－－（3）   
> ldr x6, =KERNEL\_END // \_\_va(KERNEL\_END)   
> mov x3, x24 // phys offset   
> create\_block\_map x0, x7, x3, x5, x6 －－－－－－－－－－－－－－－－－－－（4）
>
> mov x0, x25   
> add x1, x26, #SWAPPER\_DIR\_SIZE   
> dmb sy   
> bl \_\_inval\_cache\_range
>
> mov lr, x27   
> ret

（1）swapper\_pg\_dir其实就是swapper进程（pid等于0的那个，其实就是idle进程）的地址空间，这时候，x0指向了内核地址空间的PGD的基地址。

（2）PAGE\_OFFSET是kernel image的首地址，对于48bit的VA而言，该地址是0xffff8000-00000000

（3）创建PAGE\_OFFSET（即kernel image首地址，虚拟地址）对应中间level的table描述符。

（4）创建PAGE\_OFFSET～KERNEL\_END之间地址映射的最后一个level的描述符。

参考文献：

1、ARMv8技术手册

2、Linux 4.4.6内核源代码

*原创文章，转发请注明出处。蜗窝科技*
