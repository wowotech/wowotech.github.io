---
title: "ARM64的启动过程之（二）：创建启动阶段的页表"
date: 2015-10-13T18:18:49+08:00
url: "/armv8a_arch/create_page_tables.html"
gid: "218"
emlog_type: "blog"
summary: "本文主要描述了ARM64启动过程中，如何建立初始化阶段页表的过程。我们知道，从bootloader到kernel的时候，MMU是off的 （顺带的负作用是无法打开data cache），为了提高性能，加快初始化速度，我们必须某个阶段（越早越好）打开MMU和cache，而在此之前，我们必须要设定好页表。 在 初始化阶段，我们mapping三段地址，一段是identity mapping，其实就是把物"
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["__create_page_tables"]
views: 71206
comment_count: 42
aliases:
  - "/armv8a_arch/218.html"
  - "/218.html"
---

一、前言

本文主要描述了ARM64启动过程中，如何建立初始化阶段页表的过程。我们知道，从bootloader到kernel的时候，MMU是off的（顺带的负作用是无法打开data cache），为了提高性能，加快初始化速度，我们必须某个阶段（越早越好）打开MMU和cache，而在此之前，我们必须要设定好页表。

在初始化阶段，我们mapping三段地址，一段是identity mapping，其实就是把物理地址mapping到物理地址上去，在打开MMU的时候需要这样的mapping（ARM ARCH强烈推荐这么做的）。第二段是kernel image mapping，内核代码欢快的执行当然需要将kernel running需要的地址（kernel txt、dernel rodata、data、bss等等）进行映射了，第三段是blob memory对应的mapping。

在本文中，我们会混用下面的概念：page table和translation table、PGD和Level 0 translation table、PUD和Level 1 translation table、PMD和Level 2 translation table、Page Table和Level 3 translation table。最后，还是说明一下，本文来自4.1.10内核（部分来自4.4.6），有兴趣的读者可以下载来对照阅读本文。

二、基础知识

为了更好的理解\_\_create\_page\_tables的代码，我们需要准备一些基础知识。由于ARM64太复杂了，各种exception level、各种stage translation、各种地址宽度配置等等让虚拟地址到物理地址的映射变得非常复杂，因此，本文focus在一种配置：Non-secure EL1和EL0、stage 1 translation、VA和PA的地址宽度都是48个bit。

1、虚拟地址空间的size是多少？

在32-bit的ARM时代，这个问题问的有点白痴，大家都是耳熟能详的一句话就是每一个进程都有4G的独立的虚拟地址空间（0x0～0xffffffff）。对于ARM64而言，进程需要完全使用2^64那么多的虚拟地址空间吗？如果需要，那么CPU的MMU单元需要能接受来自处理器发出的64根地址线的输入信号，并对其进行翻译，这也就意味着MMU需要更多的晶体管来支持64根地址线的输入，而CPU也需要驱动更多的地址线，但是实际上，在短期内，没有看出有2^64那么多的虚拟地址空间的需求，因此，ARMv8实际上提供了TCR\_ELx （Translation Control Register (ELx)可以对MMU的输入地址（也就是虚拟地址）进行配置。为了不把问题复杂化，我们先不考虑TCR\_EL2和TCR\_EL3这两个寄存器。通过TCR\_EL1寄存器中的TxSZ域可以控制虚拟地址空间的size。对于ARM64（是指处于AArch64状态的处理器）而言，最大的虚拟地址的宽度是48 bit，因此虚拟地址空间的范围是0x0000\_0000\_0000\_0000 ～ 0x0000\_FFFF\_FFFF\_FFFF，总共256TB。 当然，具体实现的时候可以选择如下的地址线数目：

> config ARM64\_VA\_BITS   
> int   
> default 36 if ARM64\_VA\_BITS\_36   
> default 39 if ARM64\_VA\_BITS\_39   
> default 42 if ARM64\_VA\_BITS\_42   
> default 47 if ARM64\_VA\_BITS\_47   
> default 48 if ARM64\_VA\_BITS\_48

在代码中，有一个宏定义如下：

> #define VA\_BITS (CONFIG\_ARM64\_VA\_BITS)

这个宏定义了虚拟地址空间的size。

2、物理地址空间的size是多少？

问过虚拟地址空间的size是多少这个问题之后，很自然的会考虑物理地址空间。基本概念和上一节类似，符合ARMv8的PE最大支持的物理地址宽度也是48个bit，当然，具体的实现可以自己定义（不能超过48个bit），具体的配置可以通过ID\_AA64MMFR0\_EL1 （AArch64 Memory Model Feature Register 0）这个RO寄存器获取。

3、和地址映射相关的宏定义

|  |  |
| --- | --- |
| 宏定义符号 | 描述 |
| VA\_START | 内核地址空间的起始地址 |
| TEXT\_OFFSET | bootloader会把kernel image从外设copy到RAM中，那么具体copy到什么位置呢？从RAM的起始地址开始吗？实际上是从TEXT\_OFFSET开始的，偏移这么一小段内存估计是为了bootloader和kernel之间传递一些信息。所以，这里TEXT是指kernel text segment，而OFFSET是相对于RAM的首地址而言的。    TEXT\_OFFSET必须要4K对齐并且TEXT\_OFFSET的size不能大于2M。 |
| PAGE\_OFFSET | kernel image的起始虚拟地址，一般而言也就是系统中RAM的首地址，在该地址TEXT\_OFFSET之后保存了kernel image。    PAGE\_OFFSET必须要2M对齐 |
| TASK\_SIZE | 一般而言，用户地址空间从0开始，大小就是TASK\_SIZE，因此，这个宏定义的全称应该是task userspace size。对于ARM64的用户空间进程而言，有两种，一种是运行在AArch64状态下，另外一种是运行在AArch32状态，因此，实际上代码中又定义了TASK\_SIZE\_32和TASK\_SIZE\_64两个宏定义。 |
| PHYS\_OFFSET | 系统内存的起始物理地址。在系统初始化的过程中，会把PHYS\_OFFSET开始的物理内存映射到PAGE\_OFFSET的虚拟内存上去。 |

4、虚拟地址空间到物理地址空间的映射

MMU主要负责从VA（virutal address）到PA（Physical address）的翻译、memory的访问控制以及memory attribute的控制，这里我们暂时只关注地址翻译功能。不同的exception level和security state有自己独立的地址翻译过程，当然我们这里暂时只关注Non-secure EL1和EL0，在这种状态下，地址翻译可以分成两个stage，不过两个stage是为虚拟化考虑的，因此，为了简化问题，我们先只考虑一个stage。OK，做了这么多的简化之后，我们可以来看看地址翻译过程了（也就是Non-secure EL1和EL0 stage 1情况下的地址翻译过程）。

一个很有意思的改变（针对ARM32而言）是虚拟地址空间被分成了两个VA subrange：

> Lower VA subrange ： 从0x0000\_0000\_0000\_0000 到 (2^(64-T0SZ) - 1)   
> Upper VA subrange ： 从(2^64 - 2^(64-T1SZ)) 到 0xFFFF\_FFFF\_FFFF\_FFFF

为什么呢？熟悉ARM平台的工程师都形成了固定的印象，当进程切换地址空间的时候，实际上切换了内核地址空间+用户地址空间（total 4G地址空间），而实际上，每次进程切换的时候，内核地址空间都是不变的，实际变化的只有userspace而已。如果硬件支持了VA subrange，那么我们可以这样使用：

> Lower VA subrange ： process-specific地址空间   
> Upper VA subrange ： kernel地址空间

这样，当进程切换的时候，我们不必切换kernel space，只要切换userspace就OK了。

地址映射的粒度怎么配置呢？地址映射的粒度用通俗的语言讲就是page size（也可能是block size），传统的page size都是4K，ARM64的MMU支持4K、16K和64K的page size。除了地址映射的粒度还有一个地址映射的level的概念，在ARM32的时代，2 level或者3 level是比较常见的配置，对于ARM64，这和page size、物理地址和虚拟地址的宽度都是有关系的，具体请参考ARM ARM文档。

5、AArch64 Linux中虚拟地址空间的布局

把事情搞的太复杂了往往迷失了重点，我们这里再做一个简化就是固定page size是4K，并且VA宽度是48个bit，在这种情况下，虚拟地址空间的布局如下：

[![address space](/content/uploadfile/201510/b518d56c4987b78cffbc01b221e71d5420151013101751.gif "address space")](/content/uploadfile/201510/87d98e9346ad7283fe5e3aabc2a6ea1520151013101751.gif)

具体的映射过程如下：

[![mapping level](/content/uploadfile/201510/48dbfb274a97024f1be11433a757ea9020151013101752.gif "mapping level")](/content/uploadfile/201510/9894aaea293dc8492f2f0744360a819f20151013101751.gif)

整个地址翻译的过程是这样的：首先通过虚拟地址的高位可以知道是属于userspace还是kernel spce，从而分别选择TTBR0\_EL1（Translation Table Base Register 0 (EL1)）或者TTBR1\_EL1（Translation Table Base Register 1 (EL1)）。这个寄存器中保存了PGD的基地址，该地址指向了一个lookup table，每一个entry都是描述符，可能是Table descriptor、block descriptor或者是page descriptor。如果命中了一个block descriptor，那么地址翻译过程就结束了，当然对于4-level的地址翻译过程，PGD中当然保存的是Table descriptor，从而指向了下一节的Translation table，在kernel中称之PUD。随后的地址翻译概念类似，是一个PMD过程，最后一个level是PTE，也就是传说中的page table entry了，到了最后的地址翻译阶段。这时候PTE中都是一个个的page descriptor，完成最后的地址翻译过程。

三、代码分析

本文涉及的代码就是\_\_create\_page\_tables这个函数。

1、initial translation tables的位置。

initial translation tables定义在链接脚本文件中（参考arch/arm64/kernel下的vmlinux.lds.S），如下：

> . = ALIGN(PAGE\_SIZE);   
> idmap\_pg\_dir = .;   
> . += IDMAP\_DIR\_SIZE;   
> swapper\_pg\_dir = .;   
> . += SWAPPER\_DIR\_SIZE;

ARM32的的时候，kernel image在RAM开始的位置让出了32KB的memory保存了bootloader到kernel传递的tag参数以及内核空间的页表。在刚开始的时候，ARM64沿用了ARM32的做法，将这些初始页表放到了PHYS\_OFFSET和PHYS\_OFFSET+TEXT\_OFFSET之间（size是0x80000）。但是，其实这段内存是有可能被bootloader使用的，而且，这个时候，memory block模块（确定内核需要管理的memory block）没有ready，想要标记reservation memory也是不可能的。在这种情况下，假设bootloader在这段memory放了些数据，试图传递给kernel，但是kernel如果在这段memory上建立页表，那么就把有用数据给覆盖了。最后，initial translation tables被放到了kernel image的后面，位于bss段之后，从而解决了这个问题。

解决了位置问题之后，我们来看一看size，代码如下：

> #if ARM64\_SWAPPER\_USES\_SECTION\_MAPS  
> #define SWAPPER\_PGTABLE\_LEVELS (CONFIG\_PGTABLE\_LEVELS - 1)  
> #define IDMAP\_PGTABLE\_LEVELS (ARM64\_HW\_PGTABLE\_LEVELS(PHYS\_MASK\_SHIFT) - 1)  
> #else  
> #define SWAPPER\_PGTABLE\_LEVELS (CONFIG\_PGTABLE\_LEVELS)  
> #define IDMAP\_PGTABLE\_LEVELS (ARM64\_HW\_PGTABLE\_LEVELS(PHYS\_MASK\_SHIFT))  
> #endif  
>   
> #define SWAPPER\_DIR\_SIZE (SWAPPER\_PGTABLE\_LEVELS \* PAGE\_SIZE)  
> #define IDMAP\_DIR\_SIZE (IDMAP\_PGTABLE\_LEVELS \* PAGE\_SIZE)

ARM64\_SWAPPER\_USES\_SECTION\_MAPS这个宏定义是说明了swapper/idmap的映射是否使用section map。什么是section map呢？我们用一个实际的例子来描述。假设VA是48 bit，page size是4K，那么，在地址映射过程中，地址被分成9（level 0） ＋ 9（level 1） ＋ 9（level 2） ＋ 9（level 3） ＋ 12（page offset），对于kernel image这样的big block memory region，使用4K的page来mapping有点得不偿失，在这种情况下，可以考虑让level 2的Translation table entry指向一个2M 的memory region，而不是下一级的Translation table。所谓的section map就是指使用2M的为单位进行映射。当然，不是什么情况都是可以使用section map，对于kernel image，其起始地址是2M对齐的，因此block size是2M的情况下才OK，对于PAGE SIZE是16K，其Block descriptor指向了一个32M的内存块，PAGE SIZE是64K的时候，Block descriptor指向了一个512M的内存块，因此，只有4K page size的情况下，才可以启用section map。

OK，我们回到具体的初始阶段页表大小这个问题上。原来ARM32的时候，一个page就OK了，对于ARM64，由于虚拟地址空间变大了，因此我们需要更多的page来完成启动阶段的initial translation tables的构建。我们仍然用VA是48 bit，page size是4K为例子进行说明。根据前面的描述，我们知道，内核空间的地址大小是256T，48 bit的地址被分成9 ＋ 9 ＋ 9 ＋ 9 ＋ 12，因此PGD（Level 0）、PUD（Level 1）、PMD（Level 2）、PT（Level 3）的translation table中的entry都是512项，每个描述符是8个byte，因此这些translation table都是4KB，恰好是一个page size。根据链接脚本中的定义，idmap和swapper page tables （或者叫做translation table）分别保留了3个page的页面。3个page分别是3个level的translation table。等等，读者可能会问：上面不是说48 bit VA加上4K page size需要4阶translation table吗？这里怎么只有3个level？实际上，3级映射是PGD/PUM/PMD（每个table占据一个page），只不过PMD的内容不是下一级的table descriptor，而是基于2M block的mapping（或者说PMD中的描述符是block descriptor）。

2、创建页表前的准备

代码如下：

> \_\_create\_page\_tables:   
> adrp x25, idmap\_pg\_dir －－－－－－获取idmap的页表基地址（物理地址）   
> adrp x26, swapper\_pg\_dir －－－－－获取kernel space的页表基地址（物理地址）   
> mov x27, lr －－－－－－保存lr
>
> mov x0, x25 －－－－－－－－－－准备要invalid cache的地址段的首地址   
> add x1, x26, #SWAPPER\_DIR\_SIZE －－－－－－－准备要invalid cache的地址段的尾地址   
> bl \_\_inval\_cache\_range －－－－将idmap和swapper页表地址段对应的cacheline设定为无效
>
> mov x0, x25 －－－－－－－这一段代码是将idmap和swapper页表内容设定为0   
> add x6, x26, #SWAPPER\_DIR\_SIZE －－－－x0是开始地址，x6是结束地址   
> 1: stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> stp xzr, xzr, [x0], #16   
> cmp x0, x6   
> b.lo 1b

这段代码没有什么特别要说明的，除了adrp这条指令。adrp是计算指定的符号地址到run time PC值的相对偏移（不过，这个offset没有那么精确，是以4K为单位，或者说，低12个bit是0）。在指令编码的时候，立即数（也就是offset）占据21个bit，此外，由于偏移计算是按照4K进行的，因此最后计算出来的符号地址必须要在该指令的－4G和4G之间。由于执行该指令的时候，还没有打开MMU，因此通过adrp获取的都是物理地址，当然该物理地址的低12个bit是全零的。此外，由于在链接脚本中idmap\_pg\_dir和swapper\_pg\_dir是page size aligned，因此使用adrp指令也是OK的。

为什么要调用\_\_inval\_cache\_range来invalidate idmap\_pg\_dir和swapper\_pg\_dir对应页表空间的cache呢？根据boot protocol，代码执行到此，对于cache的要求是kernel image对应的那段空间的cache line是clean到PoC的，不过idmap\_pg\_dir和swapper\_pg\_dir对应页表空间不属于kernel image的一部分，因此其对应的cacheline很可能有一些旧的，无效的数据，必须要清理掉。

顺便再提一句，将idmap和swapper页表内容设定为0是有意义的。实际上这些translation table中的大部分entry都是没有使用的，PGD和PUD都是只有一个entry是有用的，而PMD中有效的entry数目是和mapping的地址size有关。将页表内容清零也就是意味着将页表中所有的描述符设定为invalid（描述符的bit 0指示是否有效，等于0表示无效描述符）。

3、创建identity mapping

identity mapping实际上就是建立了整个内核（从KERNEL\_START到KERNEL\_END）的一致性mapping，就是将物理地址所在的虚拟地址段mapping到物理地址上去。为什么这么做呢？ARM ARM文档中有一段话：

> If the PA of the software that enables or disables a particular stage of address translation differs from its VA, speculative instruction fetching can cause complications. ARM strongly recommends that the PA and VA of any software that enables or disables a stage of address translation are identical if that stage of translation controls translations that apply to the software currently being executed.

由于打开MMU操作的时候，内核代码欢快的执行，这时候有一个地址映射ON/OFF的切换过程，这种一致性映射可以保证在在打开MMU那一点附近的程序代码可以平滑切换。具体的操作分成两个阶段，第一个阶段是通过create\_pgd\_entry建立中间level（也就是PGD和PUD）的描述符，第二个阶段是创建PMD的描述符，由于PMD的描述符是block descriptor，因此，完成PMD的设定后就完成了整个identity mapping页表的设定。具体代码如下：

> ldr x7, =MM\_MMUFLAGS   
> mov x0, x25－－－－－－－－－x0保存了idmap\_pg\_dir变量的物理地址   
> adrp x3, KERNEL\_START－－－x3保存了内核image的物理地址
>
> create\_pgd\_entry x0, x3, x5, x6   
> mov x5, x3 // \_\_pa(KERNEL\_START)   
> adr\_l x6, KERNEL\_END // \_\_pa(KERNEL\_END)   
> create\_block\_map x0, x7, x3, x5, x6

create\_pgd\_entry用来在PGD（level 0 translation table）中创建一个描述符，如果需要下一级的translation table，也需要同时建立，最终的要求是能够完成所有中间level的translation table的建立（其实每个table中都是只建立了一个描述符），对于identity mapping，这里需要PGD和PUD就OK了。该函数需要四个参数：x0是pgd的地址，具体要创建哪一个地址的描述符由x3指定，x5和x6是临时变量，create\_pgd\_entry具体代码如下：

> .macro create\_pgd\_entry, tbl, virt, tmp1, tmp2   
> create\_table\_entry \tbl, \virt, PGDIR\_SHIFT, PTRS\_PER\_PGD, \tmp1, \tmp2   
> create\_table\_entry \tbl, \virt, TABLE\_SHIFT, PTRS\_PER\_PTE, \tmp1, \tmp2   
> .endm

create\_table\_entry这个宏定义主要是用来创建一个translation table的描述符，具体创建哪一个level的Translation table descriptor是由tbl参数指定的。怎么来创建描述符呢？如果是table descriptor，那么该描述符需要指向下一级页表基地址，当然，create\_table\_entry参数并没有给出，是在程序中hardcode实现：L（n）的translation table中的描述符指向的L（n＋1） Translation table位于L（n）translation table所在page的下一个page（太拗口了，但是我也懒得画图了）。shift和ptrs这两个参数用来计算页表内的index，具体算法可以参考下面的代码：

> .macro create\_table\_entry, tbl, virt, shift, ptrs, tmp1, tmp2   
> lsr \tmp1, \virt, #\shift－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> and \tmp1, \tmp1, #\ptrs - 1 －－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> add \tmp2, \tbl, #PAGE\_SIZE－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> orr \tmp2, \tmp2, #PMD\_TYPE\_TABLE－－－－－－－－－－－－－－－－－－－－（4）   
> str \tmp2, [\tbl, \tmp1, lsl #3]－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> add \tbl, \tbl, #PAGE\_SIZE －－－－－－－－－－－－－－－－－－－－－－－－－（6）   
> .endm

（1）如果是PGD，那么shift等于PGDIR\_SHIFT，也就是39了。根据第二章的描述，我们知道L0 index（PGD index）使用虚拟地址的bit[47:39]。如果是PUD，那么shift等于PUD\_SHIFT，也就是30了（注意：L1 index（PUD index）使用虚拟地址的bit[38:30]）。要想找到virt这个地址（实际传入的是物理地址，当然，我们本来就是要建立和物理地址一样的虚拟地址的mapping）在translation table中的index，当然需要右移shift个bit了。

（2）除了右移操作，我们还需要mask操作（ptrs - 1实际上就是掩码）。对于PGD，其index占据9个bit，因此mask是0x1ff。同样的，对于PUD，其index占据9个bit，因此mask是0x1ff。至此，tmp1就是virt地址在translation table中对应的index了。

（3）如果是table描述符，需要指向另外一个level的translation table，在哪里呢？答案就是next page，读者可以自行回忆链接脚本中的3个连续的idmap\_pg\_dir的page定义。

（4）光有下一级translation table的地址不行，还要告知该描述符是否有效（set bit 0），该描述符的类型是哪一种类型（set bit 1表示是table descriptor），至此，描述符内容准备完毕，保存在tmp2中

（5）最关键的一步，将描述符写入页表中。之所以有“lsl #3”操作，是因为一个描述符占据8个Byte。

（6）将translation table的地址移到next level，以便进行下一步设定。

如果你足够细心，一定不会忽略这样的一个细节。获取KERNEL\_START和KERNEL\_END的代码是不一样的，对于KERNEL\_START直接使用了adrp x3, KERNEL\_START，而对于KERNEL\_END使用了adr\_l x6, KERNEL\_END。具体使用哪一个是和该地址是否4K对齐相关的。KERNEL\_START一定是4K对齐的，而KERNEL\_END就不一定了，虽然在4.1.10中KERNEL\_END也是4K对齐的，不过没有任何协议保证这一点，为了保险起见，代码使用了adr\_l，确保获取正确的KERNEL\_END的物理地址。

回到create\_pgd\_entry函数中，这个函数填充了内核image首地址对应的1G memory range所需要的Translation table描述符，听起来很吓人，不过就是两个描述符，一个是在PGD中，另外一个是在PUD中。虽然只有两个描述符，可以可以支持1G虚拟地址的mapping了。当然具体mapping多少（PMD中有多少entry），还是要看kernel image的size了。

OK，来到PMD部分的设定了，我们看看代码：

> .macro create\_block\_map, tbl, flags, phys, start, end   
> lsr \phys, \phys, #BLOCK\_SHIFT   
> lsr \start, \start, #BLOCK\_SHIFT   
> and \start, \start, #PTRS\_PER\_PTE - 1 // table index   
> orr \phys, \flags, \phys, lsl #BLOCK\_SHIFT // table entry   
> lsr \end, \end, #BLOCK\_SHIFT   
> and \end, \end, #PTRS\_PER\_PTE - 1 // table end index   
> 9999: str \phys, [\tbl, \start, lsl #3] // store the entry   
> add \start, \start, #1 // next entry   
> add \phys, \phys, #BLOCK\_SIZE // next block   
> cmp \start, \end   
> b.ls 9999b   
> .endm

create\_block\_map的名字起得不错，该函数就是在tbl指定的Translation table中建立block descriptor以便完成address mapping。具体mapping的内容是将start 到 end这一段VA mapping到phys开始的PA上去。其实这里的代码逻辑和上面类似，我们这里就不详述，需要提及的是PTE已经进入了最后一个level的mapping，因此描述符中除了地址信息之外（占据bit[47:21]，还需要memory attribute和memory accesse的信息。对于这个场景，PMD中是block descriptor，因此描述符中还包括了block attribute域，分成upper block attribute[63:52]和lower block attribute[11:2]。对这些域的定义如下：

[![attribute](/content/uploadfile/201510/b80930fd42f49a4f2712cb47fe2d1eae20151013101847.gif "attribute")](/content/uploadfile/201510/08cc60334ad8425f4eb5ee92ed9a2c1320151013101752.gif)

在代码中，block attribute是通过flags参数传递的，MM\_MMUFLAGS定义如下：

> #define MM\_MMUFLAGS PMD\_ATTRINDX(MT\_NORMAL) | PMD\_FLAGS
>
> #define PMD\_FLAGS PMD\_TYPE\_SECT | PMD\_SECT\_AF | PMD\_SECT\_S

MT\_NORMAL表示该段内存的memory type是普通memory（对应AttrIndx[2:0]），而不是device什么的。PMD\_TYPE\_SECT 说明该描述符是一个有效的（bit 0等于1）的block descriptor（bit 1等于0）。PMD\_SECT\_AF中的AF是access flag的意思，表示该memory block（或者page）是否被最近被访问过。当然，这需要软件的协助。如果该bit被设置为0，当程序第一次访问的时候会产生异常，软件需要将给bit设置为1，之后再访问该page的时候，就不会产生异常了。不过当软件认为该page已经old enough的时候，也可以clear这个bit，表示最近都没有访问该page。这个flag是硬件对page reclaim算法的支持，找到最近不常访问的那些page。当然在这个场景下，我们没有必要enable这个特性，因此将其设定为1。PMD\_SECT\_S对应SH[1:0]，描述memory的sharebility。这些内容和memory attribute相关，我们会在后续的文档中描述，这里就不偏离主题了。

广大人民群众最关心的当然也是最熟悉的是memory access control，这是通过AP[2:1]域来控制的。这里该域被设定为00b，表示EL1状态下是RW，EL0状态不可访问。UXN和PXN是用来控制可执行权限的，这里UXN和PXN都是0，表示EL1和EL0状态下都是excutable的。

4、创建kernel space mapping

要创建kernel space的页表了，遇到的第一个问题就是：mapping多少呢？kernel space辣么大，256T，不可能全部都mapping。OK，答案就是创建两部分的页表，一个从kernel image的开始地址（包括开始的那一段TEXT\_OFFSET的保留区域）到kernel image的结束地址（内核的正常运行需要这段mapping），这一段覆盖了内核的正文段、各种data段、bss段、各种奇奇怪怪段等。还有一个就是bootloader传递过来的blob memory对应的页表。我们先看第一段kernel image的mapping：

> mov x0, x26－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> mov x5, #PAGE\_OFFSET－－－－－－－－－－－－－－－－－－－（2）   
> create\_pgd\_entry x0, x5, x3, x6－－－－－－－－－－－－－－－－－（3）   
> ldr x6, =KERNEL\_END－－－－－－end address   
> mov x3, x24 // phys offset   
> create\_block\_map x0, x7, x3, x5, x6－－－－－－－－－－－－－－－（4）

（1）swapper\_pg\_dir其实就是swapper进程（pid等于0的那个，其实就是idle进程）的地址空间，这时候，x0指向了内核地址空间的PGD的基地址。

（2）PAGE\_OFFSET是kernel image的首地址，对于48bit的VA而言，该地址是0xffff8000-00000000。

（3）创建PAGE\_OFFSET（即kernel image首地址）对应的PGD和PUD中的描述符。

（4）创建PMD中的描述符。x24保存了\_\_PHYS\_OFFSET，实际上也就是kernel image的首地址（物理地址）。

完成了kernel image的mapping，我们来看看blob mapping的建立。由于ARM64 boot protocol要求blob必须在内核空间开始的512MB内（同时要求8字节对齐，dtb image不能越过2M section size的边界），因此实际上PGD和PUD都不需要建立了，只要建立PMD的描述符就OK了。对应的PMD描述符的建立代码如下：

> mov x3, x21－－－－－－－－－－－－－－FDT phys address   
> and x3, x3, #~((1 << 21) - 1) －－－－－－2MB aligned   
> mov x6, #PAGE\_OFFSET－－－－－－－kernel space start virtual address   
> sub x5, x3, x24－－－－－－－－－－－－subtract kernel space start physical address
>
> tst x5, #~((1 << 29) - 1) －－－－－－－－within 512MB?   
> csel x21, xzr, x21, ne －－－－－－－－－bad blob parameter and zero the FDT pointer   
> b.ne 1f   
> add x5, x5, x6 －－－－－－－－－－－－x5 equal blob virtual address   
> add x6, x5, #1 << 21 －－－－－－－－－mapping 2M size   
> sub x6, x6, #1   
> create\_block\_map x0, x7, x3, x5, x6－－－create blob block descriptor in PMD

5、收尾

> mov x0, x25－－－－－－－再次invalid上文中建立page table memory对应的cache   
> add x1, x26, #SWAPPER\_DIR\_SIZE   
> dmb sy   
> bl \_\_inval\_cache\_range
>
> mov lr, x27－－－－－－恢复lr   
> ret－－－－－－－－－－－返回   
> ENDPROC(\_\_create\_page\_tables)

由于页表中写了新的内容，而且是在没有打开cache的情况下写的，这时候，cache line的数据有可能被speculatively load，因此再次invalid是一个比较保险的做法。

四、参考文献

1、Documentation/arm64/memory.txt

2、ARM Architecture Reference Manual

change log：

1、2015-12-1，修正对PAGE\_OFFSET的描述。

2、2016-7-12，（1）增加了和地址映射相关的几个宏定义的描述。（2）增加建立identity mapping的原因

3、2016-7-15，对initial translation tables的位置和size进行补充描述。

4、2016-9-9，修改DTB的限制。

*原创文章，转发请注明出处。蜗窝科技*
