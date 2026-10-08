---
title: "ARM64的启动过程之（四）：打开MMU"
date: 2015-10-24T12:35:07+08:00
url: "/armv8a_arch/turn-on-mmu.html"
gid: "221"
emlog_type: "blog"
summary: "经过漫长的前戏，我们终于迎来了打开MMU的时刻，本文主要描述打开MMU以及跳转到start_kernel之前的代码逻辑。这一节完成之后，我们就会离开痛苦的汇编，进入人民群众喜闻乐见的c代码了。"
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["打开MMU"]
views: 66894
comment_count: 52
aliases:
  - "/armv8a_arch/221.html"
  - "/221.html"
---

一、前言

经过漫长的前戏，我们终于迎来了打开MMU的时刻，本文主要描述打开MMU以及跳转到start\_kernel之前的代码逻辑。这一节完成之后，我们就会离开痛苦的汇编，进入人民群众喜闻乐见的c代码了。

二、打开MMU前后的概述

对CPU以及其执行的程序而言，打开MMU是一件很有意思的事情，好象从现实世界一下子走进了奇妙的虚幻世界，本节，我们一起来看看内核是如何“穿越”的。下面这张图描述了两个不同的世界：

[![mmu-on-off](/content/uploadfile/201512/b8d2febaa80339bcb73e255061e7aada20151202015400.gif "mmu-on-off")](/content/uploadfile/201512/60448863bf7d21ce6ac493a4b2d92de920151202015359.gif)

当没有打开MMU的时候，cpu在进行取指以及数据访问的时候是直接访问物理内存或者IO memory。虽然64bit的CPU理论上拥有非常大的address space，但是实际上用于存储kernel image的物理main memory并没有那么大，一般而言，系统的main memory在低端的一小段物理地址空间中，如上图右侧的图片所示。当打开MMU的时候，cpu对memory系统的访问不能直接触及物理空间，而是需要通过一系列的Translation table进行翻译。虚拟地址空间分成三段，低端是0x00000000\_00000000～0x0000FFFF\_FFFFFFFF，用于user space。高端是0xFFFF0000\_00000000～0xFFFFFFFF\_FFFFFFFF，用于kernel space。中间的一段地址是无效地址，对其访问会产生MMU fault。虚拟地址空间如上图右侧的图片所示。

Linker感知的是虚拟地址，在将内核的各个object文件链接成一个kernel image的时候，kernel image binary code中访问的都是虚拟地址，也就是说kernel image应该运行在Linker指定的虚拟地址空间上。问题来了，kernel image运行在那个地址上呢？实际上，将kernel image放到kernel space的首地址运行是一个最直观的想法，不过由于各种原因，具体的arch在编译内核的时候，可以指定一个offset（TEXT\_OFFSET），对于ARM64而言是512KB（0x00080000），因此，编译后的内核运行在0xFFFF8000\_00080000的地址上。系统启动后，bootloader会将kernel image copy到main memory，当然，和虚拟地址空间类似，kernel image并没有copy到main memory的首地址，也保持了一个同样size的offset。现在，问题又来了：在kernel的开始运行阶段，MMU是OFF的，也就是说kernel image是直接运行在物理地址上的，但是实际上kernel是被linker链接到了虚拟地址上去的，在这种情况下，在没有turn on MMU之前，kernel能正常运行吗？可以的，如果kernel在turn on MMU之前的代码都是PIC的，那么代码实际上是可以在任意地址上运行的。你可以仔细观察turn on MMU之前的代码，都是位置无关的代码。

OK，解决了MMU turn on之前的问题，现在我们可以准备“穿越”了。真正打开MMU就是一条指令而已，就是将某个system register的某个bit设定为1之类的操作。这样我们可以把相关指令分成两组，turn on mmu之前的绿色指令和之后的橘色指令，如下图所示：

[![mmu-1](/content/uploadfile/201510/34e38e720d5cc7776246207c6cdc92bd20151024043506.gif "mmu-1")](/content/uploadfile/201510/a4baf59a65665a921228cf031606bbe320151024043505.gif)

由于现代CPU的设计引入了pipe， super scalar，out-of-order execution，分支预测等等特性，实际上在turn on MMU的指令执行的那个时刻，该指令附近的指令的具体状态有些混乱，可能绿色指令执行的数据加载在实际在总线上发起bus transaction的时候已经启动了MMU，本来它是应该访问physical address space的。而也有可能橘色的指令提前执行，导致其发起的memory操作在MMU turn on之前就完成。为了解决这些混乱，可以采取一种投机取巧的办法，就是建立一致性映射：假设kernel image对应的物理地址段是A～B这一段，那么在建立页表的时候就把A～B这段虚拟地址段映射到A～B这一段的物理地址。这样，在turn on MMU附近的指令是毫无压力的，无论你是通过虚拟地址还是物理地址，访问的都是同样的物理memory。

还有一种方法，就是清楚的隔离turn on MMU前后的指令，那就是使用指令同步工具，如下：

[![mmu-2](/content/uploadfile/201510/1814f128c7e1cf94cacff66e8824056220151024043507.gif "mmu-2")](/content/uploadfile/201510/4e9eff9c8d6e4d68316b168c76299b3620151024043506.gif)

指令屏障可以清清楚楚的把指令的执行划分成三段，第一段是绿色指令，在执行turn on mmu指令执行之前全部完成，随后启动turn on MMU的指令，随后的指令屏障可以确保turn on MMU的指令完全执行完毕（整个计算机系统的视图切换到了虚拟世界），这时候才启动橘色指令的取指、译码、执行等操作。

三、打开MMU的代码

具体打开MMU的代码在\_\_enable\_mmu函数中如下：

> \_\_enable\_mmu:   
> ldr x5, =vectors   
> msr vbar\_el1, x5 －－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> msr ttbr0\_el1, x25 // load TTBR0 －－－－－－－－－－－－－－－－－（2）   
> msr ttbr1\_el1, x26 // load TTBR1   
> isb   
> msr sctlr\_el1, x0 －－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> isb   
> br x27 －－－－－－－－－－－－－跳转到\_\_mmap\_switched执行，不设定lr寄存器   
> ENDPROC(\_\_enable\_mmu)

传入该函数的参数有四个，一个是x0寄存器，该寄存器中保存了打开MMU时候要设定的SCTLR\_EL1的值（在\_\_cpu\_setup函数中设定），第二个是个是x25寄存器，保存了idmap\_pg\_dir的值。第三个参数是x26寄存器，保存了swapper\_pg\_dir的值。最后一个参数是x27，是执行完毕该函数之后，跳转到哪里去执行（\_\_mmap\_switched）。

（1）VBAR\_EL1, Vector Base Address Register (EL1)，该寄存器保存了EL1状态的异常向量表。在ARMv8中，发生了一个exception，首先需要确定的是该异常将送达哪一个exception level。如果一个exception最终送达EL1，那么cpu会跳转到这里向量表来执行。具体异常的处理过程由其他文档描述，这里就不说了。

（2）idmap\_pg\_dir是为turn on MMU准备的一致性映射，物理地址的高16bit都是0，因此identity mapping必定是选择TTBR0\_EL1指向的各级地址翻译表。后续当系统运行之后，在进程切换的时候，会修改TTBR0的值，切换到真实的进程地址空间上去。TTBR1用于kernel space，所有的内核线程都是共享一个空间就是swapper\_pg\_dir。

（3）打开MMU。实际上在这条指令的上下都有isb指令，理论上已经可以turn on MMU之前之后的代码执行顺序严格的定义下来，其实我感觉不必要再启用idmap\_pg\_dir的那些页表了，当然，这只是猜测。

四、通向start\_kernel

我痛恨汇编，如果能不使用汇编那绝对不要使用汇编，还好我们马上就要投奔start\_kernel：

> \_\_mmap\_switched:   
> adr\_l x6, \_\_bss\_start   
> adr\_l x7, \_\_bss\_stop
>
> 1: cmp x6, x7   
> b.hs 2f   
> str xzr, [x6], #8 －－－－－－－－－－－－－－－clear BSS   
> b 1b   
> 2:   
> adr\_l sp, initial\_sp, x4 －－－－－－－－－－－建立和swapper进程的链接   
> str\_l x21, \_\_fdt\_pointer, x5 // Save FDT pointer   
> str\_l x24, memstart\_addr, x6 // Save PHYS\_OFFSET   
> mov x29, #0   
> b start\_kernel   
> ENDPROC(\_\_mmap\_switched)

这段代码分成两个部分，一部分是清BSS，另外一部分是为进入c代码做准备（主要是stack）。clear BSS段就是把未初始化的全局变量设定为0的初值，没有什么可说的。要进入start\_kernel这样的c代码，没有stack可不行，那么如何设定stack呢？熟悉kernel的人都知道，用户空间的进程当陷入内核态的时候，stack切换到内核栈，实际上就是该进程的thread info内存段（4K或者8K）的顶部。对于swapper进程，原理是类似的：

> .set initial\_sp, init\_thread\_union + THREAD\_START\_SP

如果说之前的代码执行都处于一个孤魂野鬼的状态，“adr\_l sp, initial\_sp, x4”指令执行之后，初始化代码终于找到了归宿，初始化代码有了自己的thread info，有了自己的task struct，有了自己的pid，有了进程（内核线程）应该拥有的一切，从此之后的代码归属idle进程，pid等于0的那个进程。

为了方便后面的代码的访问，这里还初始化了两个变量，分别是\_\_fdt\_pointer（设备树信息，物理地址）和memstart\_addr（kernel image所在的物理地址，一般而言是main memory的首地址）。 memstart\_addr主要用于main memory中物理地址和虚拟地址的转换，具体可以参考\_\_virt\_to\_phys和\_\_phys\_to\_virt的实现。

五、参考文献

1、ARM Architecture Reference Manual

change log：

1、2015-11-30，强调了初始化代码和idle进程的连接

2、2015-12-2，修改了物理空间和虚拟空间的视图

3、2016-9-21，修改对一致性映射的描述

*原创文章，转发请注明出处。蜗窝科技*
