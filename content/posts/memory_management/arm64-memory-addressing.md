---
title: "ARM64架构下地址翻译相关的宏定义"
date: 2016-08-12T18:50:53+08:00
url: "/memory_management/arm64-memory-addressing.html"
gid: "324"
emlog_type: "blog"
summary: "本文主要分析linux-4.4.6/arch/arm64/include/asm目录下的若干和地址翻译相关的头文件（例如page.h、 pgtable.h、pgtable-hwdef.h、pgtable-prot.h等文件）中的各种宏定义以及相关的ARM64硬件知识。硬肯ARM ARM文档有时候太费劲，结合linux源代码会让学习变得简单一些。"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["arm64", "地址翻译"]
views: 24678
comment_count: 5
aliases:
  - "/memory_management/324.html"
  - "/324.html"
---

一、前言

本文主要分析linux-4.4.6/arch/arm64/include/asm目录下的若干和地址翻译相关的头文件（例如page.h、pgtable.h、pgtable-hwdef.h、pgtable-prot.h等文件）中的各种宏定义以及相关的ARM64硬件知识。硬肯ARM ARM文档有时候太费劲，结合linux源代码会让学习变得简单一些。

二、ARM64地址翻译概述

ARM64定义了若干个translation regimes，下面的每一行地址翻译过程都是一个translation regimes：

Secure EL3 VA ----------- Secure EL3 stage 1 -----------> PA, Secure or Non-secure

Secure EL1&EL0 VA ----------- Secure EL1&EL0 stage 1 -----------> PA, Secure or Non-secure

Non-Secure EL2 VA ----------- Non-Secure EL2 stage 1 -----------> PA, Non-secure only

Non-Secure EL1&0 VA ------ stage 1 -----> IPA ------ stage 2 -----> PA, Non-secure only

translation regime可能包括一个stage，也可能包括两个stage。每个exception level都有自己的独立一套的地址翻译的机制，使用不同的页表基地址寄存器和控制寄存器。地址翻译可以细分到stage，大部分的EL包括一个stage的地址翻译过程， Non-Secure EL1&0包括了2个stage的地址翻译过程。每个stage都有自己独立的一系列Translation tables，每个stage都能独立的enable或者disable。每个stage都是将输入地址（可能是虚拟地址或者IPA）翻译成输出地址（可能是物理地址或者IPA）。

对于一个stage的地址翻译而言，也不是一蹴而就的，而是分成若干个level，每个level都是根据内存中的Translation table（我们将PGD，PUD，PMD和Page table统称Translation table）将整个VA中的部分地址翻译出来，一个简单的示意图如下（来自ULK3）：

![](/content/uploadfile/201608/f0651470999247.gif)

当然，上图是基于x86，对于ARM64，cr3寄存器应该是TTBRx寄存器，PGD也就是Level 0 translation table、PUD相当于Level 1 translation table、PMD对应Level 2 translation table、Page Table对应Level 3 translation table。

Linear Address是X86特有的地址类型，对于ARM64，Linear Address应该被修改为VA或者IPA，具体ARM64地址翻译单元要处理的地址类型如下：

（1）虚拟地址（Virtual Address，简称VA）。MMU的存在可以让各个进程生活在自己的虚拟地址空间中，因此，在进程在进行数据操作的时候（内存操作指令），在进程逻辑跳转的时候（指令地址）都是使用的虚拟地址。更具体的说，进程正文段程序位于虚拟地址之上，进程的数据段、stack和heap都是位于虚拟地址之上，因此CPU的PC、LR、SP、ELR等都是指向了虚拟地址。

（2）Intermediate Physical Address，简称IPA。IPA是计算机虚拟化之后引入的一个概念，传统的计算机系统都是虚拟地址直接映射到物理地址，但是，对于支持虚拟化的计算机系统，每一个guest OS不能直接将虚拟地址映射到整个系统的物理地址，而是映射到一个受限的物理地址空间上，而且映射是随着VM的创建而创建，一旦VM销毁，这些物理内存还需要返回给Hypervisor。因此在支持虚拟化的计算机系统中，guest OS负责将VA映射到IPA，而Hypervisor负责将IPA映射到具体的物理地址上去。

（3）物理地址（Physical Address，简称PA）。物理地址是实实在在的地址，体现在实际的电路中。如果CPU和memory chip是通过bus连接，那么物理地址就是bus上的地址信号线。实际的物理地址空间被分成了两个世界，一个是Normal world，另外一个是Secure world，虽然物理地址一样，但是却通往不同的memory cell。

三、如何确定page table level？

定义如下：

> #define ARM64\_HW\_PGTABLE\_LEVELS(va\_bits) (((va\_bits) - 4) / (PAGE\_SHIFT - 3))

从这个宏定义可以看出，两个输入参数就可以确定page table level。其中一个参数就是PAGE\_SHIFT（也就是page size了），另外一个va\_bits，也就是虚拟地址的bit数目。为何公式这么怪异呢？3和4又是什么鬼？为了回答这个问题，我们先看看一些具体的例子好了。我们还是先用最经典的4K page为例来描述。一旦确定了4K的page size，那么页偏移所占用的bit数就确定了，即[11:0]这12个地位bit用来确定页内偏移。此外，一个Translation table往往占用一个page的size，由于ARM64中，一个page table中的描述符是8个字节，因此4K中有512个描述符，因此各级index（指向PGD/PUD/PMD/PT）占用的bit数都是9个，综上所述，48bit的虚拟地址在4K page的情况下，4级映射的地址分配如下：

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| 页表基地址 | Global DIR | Upper DIR | Middle DIR | Page Table | Offset |
| 16 | 9 | 9 | 9 | 9 | 12 |

高16bit用来确定选用TTBR0或者TTBR1的Translation tables。中间的bit被平均分成4个9-bit的段，分别用来索引到PGD/PUD/PMD/PT中的具体的描述符。

如果page size是64K的话，那么offset需要16个bit，一个Translation table占有64K，每个描述符8B，总共有8K个entry，需要13个bit做为index，这时候使用3级映射，地址分配如下：

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| 页表基地址 | Global DIR | Upper DIR | Middle DIR | Page Table | Offset |
| 16 | N/A | 6 | 13 | 13 | 16 |

这时候，由于是3级映射，PGD和PUD是重合的。此外需要说明的是PGD（或者PUD）中只有64个entry，其他的都是无效的。

OK，搞定了4K和64K page size之后，我们来看看16K size的情况。16K的页对应的offset的bit数目是14个bit，而index需要的bit是11个bit（即每个16K的Translation table中有2K个entry）。这时候使用4级映射，地址分配如下：

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| 页表基地址 | Global DIR | Upper DIR | Middle DIR | Page Table | Offset |
| 16 | 1 | 11 | 11 | 11 | 14 |

因此，经过上面的三个例子之后，我们可以回头看看ARM64\_HW\_PGTABLE\_LEVELS这个宏定义了，该宏定义中的3其实是和描述符的size相关的，对于ARM64，描述符的size是8个字节，因此PAGE\_SHIFT - 3实际上描述了中间level的translation table所占据的虚拟地址的bit数目。也就是说，从虚拟地址的LSB开始，先切掉 PAGE\_SHIFT 个bit做为页内偏移，然后按照PAGE\_SHIFT - 3来切其他的中间的各个中间level的translation table所占据的虚拟地址的bit数目。因此，page table levels 应该等于 DIV\_ROUND\_UP((va\_bits - PAGE\_SHIFT), (PAGE\_SHIFT - 3))，也就是((((va\_bits) - PAGE\_SHIFT) + (PAGE\_SHIFT - 3) - 1) / (PAGE\_SHIFT - 3))，简单的数学运算之后就得到了(((va\_bits) - 4) / (PAGE\_SHIFT - 3))。

在linux kernel中，具体支持的配置请参考下面的表格：

|  |  |  |
| --- | --- | --- |
| 虚拟地址的数目 | page size | page table level |
| 48 | 64K | 3 |
| 48 | 4K or 16K | 4 |
| 47 | 16K | 3 |
| 47 | 64K or 16K | 无效 |
| 42 | 64K | 2 |
| 42 | 16K or 4K | 无效 |
| 39 | 4K | 3 |
| 39 | 64K or 16K | 无效 |
| 36 | 16K | 2 |
| 36 | 64K or 4K | 无效 |

四、如何定义各个level的地址bit偏移

在linux paging model中，PGD\_SHIFT、PUD\_SHIFT和PMD\_SHIFT用来定义定义各个Translation table在虚拟地址上的偏移量，这些定义都借用了一个ARM64\_HW\_PGTABLE\_LEVEL\_SHIFT的宏定义，如下：

> #define ARM64\_HW\_PGTABLE\_LEVEL\_SHIFT(n) ((PAGE\_SHIFT - 3) \* (4 - (n)) + 3)

我们用下面的表格来表述虚拟地址偏移的定义（4 level page table）：

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Global Dir bits（L0） | Upper Dir bits（L1） | Middle Dir bits（L2） | table bits（L3） | offset bits |

|  |  |
| --- | --- |
|  | <----page\_shift-----> |

|  |  |
| --- | --- |
|  | <-------------------pmd\_shift---------------------------> |

|  |  |
| --- | --- |
|  | <----------------------------------------pud\_shift-----------------------------------------> |

|  |  |
| --- | --- |
|  | <-------------------------------------------------------pgd\_shift-------------------------------------------------------------> |

从上面的表格可以看出，如果是4级映射都在，对于L0而言，该level的SHIFT值应该是3 x (PAGE\_SHIFT - 3) + PAGE\_SHIFT。对于L1而言，该level的SHIFT值应该是2 x (PAGE\_SHIFT - 3) + PAGE\_SHIFT。以此类推L2和L3的。假设用n来表示level，那么Ln的SHIFT值应该是((4 - n) - 1) \* (PAGE\_SHIFT - 3) + PAGE\_SHIFT，经过简单的数学运算之后可以得到(4 - n) \* (PAGE\_SHIFT - 3) + 3。当然，如果page table的level没有那么多，那么情况也类似，只不过少了PUD和PMD而已。我们用下面的表格来表述3 level page table中虚拟地址偏移的定义：

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
|  | Global Dir bits（L1） | Middle Dir bits（L2） | table bits（L3） | offset bits |

|  |  |
| --- | --- |
|  | <----page\_shift-----> |

|  |  |
| --- | --- |
|  | <-------------------pmd\_shift---------------------------> |

|  |  |
| --- | --- |
|  | <----------------------------------------pud\_shift-----------------------------------------> |

|  |  |
| --- | --- |
|  | <----------------------------------------pgd\_shift----------------------------------------> |

2 level page table的情况请自行补脑。

五、Translation table中的一个描述符对应多大的地址空间呢？

对于Level 3 translation table而言（也就是linux paging model中的page table），一个描述符就指向一个page，因此相关定义如下：

> #ifdef CONFIG\_ARM64\_64K\_PAGES   
> #define PAGE\_SHIFT 16   
> #elif defined(CONFIG\_ARM64\_16K\_PAGES)   
> #define PAGE\_SHIFT 14   
> #else   
> #define PAGE\_SHIFT 12   
> #endif   
> #define PAGE\_SIZE (\_AC(1, UL) << PAGE\_SHIFT)   
> #define PAGE\_MASK (~(PAGE\_SIZE-1))

PAGE\_SIZE定义了一个page的大小，可能是4K，16K或者64K。PAGE\_MASK是地址掩码，可以屏蔽掉虚拟地址offset域的那些地址bits。

对于Level 2 translation table而言（也就是PMD），当page level大于2的时候（也就是说page level是3或者4的时候），定义如下：

> #if CONFIG\_PGTABLE\_LEVELS > 2   
> #define PMD\_SHIFT ARM64\_HW\_PGTABLE\_LEVEL\_SHIFT(2)   
> #define PMD\_SIZE (\_AC(1, UL) << PMD\_SHIFT)   
> #define PMD\_MASK (~(PMD\_SIZE-1))   
> #define PTRS\_PER\_PMD PTRS\_PER\_PTE   
> #endif

PMD\_SHIFT包括了虚拟地址中的offset域和table域，PMD\_SIZE定义了PMD中的一个描述能mapping的地址空间的size。PMD\_MASK是地址掩码，可以mask掉虚拟地址level 3 以及offset域的那些地址bits。

page level小于等于2的时候（也就是说page level是1或者2的时候，当然，目前ARM64中不支持page level等于1的情况），相关定义如下：

> #define PMD\_SHIFT PUD\_SHIFT   
> #define PTRS\_PER\_PMD 1   
> #define PMD\_SIZE (1UL << PMD\_SHIFT)   
> #define PMD\_MASK (~(PMD\_SIZE-1))

也就是说，PMD\_SHIFT跟随PUD\_SHIFT（当然，这时候其实PUD也不存在，是说L2变成了PGD）。对于Level 1 translation table而言（也就是PUD），当page level大于3的时候（也就是说page level是4的时候），定义如下：

> #if CONFIG\_PGTABLE\_LEVELS > 3   
> #define PUD\_SHIFT ARM64\_HW\_PGTABLE\_LEVEL\_SHIFT(1)   
> #define PUD\_SIZE (\_AC(1, UL) << PUD\_SHIFT)   
> #define PUD\_MASK (~(PUD\_SIZE-1))   
> #define PTRS\_PER\_PUD PTRS\_PER\_PTE   
> #endif

当page level小于等于3的时候（也就是说page level是3或者2的时候），相关定义如下：

> #define PUD\_SHIFT PGDIR\_SHIFT   
> #define PTRS\_PER\_PUD 1   
> #define PUD\_SIZE (1UL << PUD\_SHIFT)   
> #define PUD\_MASK (~(PUD\_SIZE-1))

也就是说，PUD\_SHIFT跟随PGDIR\_SHIFT。而PGD相关的定义如下：

> #define PGDIR\_SHIFT ARM64\_HW\_PGTABLE\_LEVEL\_SHIFT(4 - CONFIG\_PGTABLE\_LEVELS)   
> #define PGDIR\_SIZE (\_AC(1, UL) << PGDIR\_SHIFT)   
> #define PGDIR\_MASK (~(PGDIR\_SIZE-1))   
> #define PTRS\_PER\_PGD (1 << (VA\_BITS - PGDIR\_SHIFT))

PGDIR\_SHIFT其实可以确定最高层那个level的Translation table（TTBR指向的那个Translation table）中的一个描述符能够mapping多大size的地址空间（参考PGDIR\_SIZE的定义）。具体这个top level的Translation table是那个呢？根据硬件手册的描述，可能是L0，可能是L1，也可能是L2，和page level的配置有关。具体的关系是4 - CONFIG\_PGTABLE\_LEVELS，也就是说，如果CONFIG\_PGTABLE\_LEVELS等于4，那么top level的Translation table就是L0，如果CONFIG\_PGTABLE\_LEVELS等于3，那么top level的Translation table就是L1。

OK，我们一起来整理一下ARM64上的具体映射关系，如下图所示：

![](/content/uploadfile/201608/7fc21470999301.gif)

当page level等于4的时候，映射关系是PGD（L0）--->PUD（L1）--->PMD（L2）--->Page table（L3）--->page。当page level等于3的时候，没有PUD，这时候映射关系是PGD（L1）--->PMD（L2）--->Page table（L3）--->page。当page level等于2的时候，没有PUD和PMD，映射关系是PGD（L2）--->Page table（L3）--->page。

最后，闲聊一下PTRS\_PER\_PTE、PTRS\_PER\_PMD、PTRS\_PER\_PUD和PTRS\_PER\_PGD。PTRS\_PER\_PGD定义了PGD中有多少个描述符，当然，有多少个描述符是和Global Dir bits的长度相关，也就是VA\_BITS - PGDIR\_SHIFT。而其他的PTRS\_PER\_XXX都是描述相应translation table中描述符的个数，对于ARM64，PTRS\_PER\_PMD和PTRS\_PER\_PUD（如果存在的话）中的描述符个数基本是是固定的，和PTRS\_PER\_PTE保持一致，定义如下：

> #define PTRS\_PER\_PTE (1 << (PAGE\_SHIFT - 3))

六、Translation table相关的宏定义

在内核中，pte\_t，pmd\_t，pud\_t和pgd\_t分别描述了page table（L3），PMD（L2），PUD（L1）和PGD（L0）中一个描述符的数据结构，对于ARM64而言其类型就是U64。pgprot\_t也是U64，描述了各个Translation table中一个描述符中的flag域。根据ARM硬件手册，Translation table中的描述符可能有四种情况：

（1）是table descriptor，指向下一级的Translation table

（2）是page descriptor，指向一个PAGE size的地址区域

（3）是block descriptor，指向一个Block size的地址区域

（4）无效描述符

对于L0，L1和L2级别的tranlation table而言，其描述符的定义如下：

![](/content/uploadfile/201608/a4ad1470999344.gif)

我们选择L1为例子来看看内核代码（其他的定义大家自己看source code吧，灰常类似）：

> #define PUD\_TYPE\_TABLE (\_AT(pudval\_t, 3) << 0)   
> #define PUD\_TABLE\_BIT (\_AT(pgdval\_t, 1) << 1)   
> #define PUD\_TYPE\_MASK (\_AT(pgdval\_t, 3) << 0)   
> #define PUD\_TYPE\_SECT (\_AT(pgdval\_t, 1) << 0)

描述符中，bit 0是表示该描述符是否是一个有效描述符，bit 1表示该描述符的类型。0b01是block descriptor，0b11是table描述符。L0，L1和L2的描述符不可能指向page descripotr。

这里我们还要具体讲讲什么是block。根据上文的描述，VA到PA的映射的最小力度就是page size（4K，16K或者64K），不过在有些情况下，例如kernel image对应地址空间的翻译，即便64K的page size也显得比较小（更大的mapping粒度意味着更高的TLB hit，从而提高性能），这时候，有一个叫做section的概念被提出了（ARM手册的术语是block），具体定义如下：

> #define SECTION\_SHIFT PMD\_SHIFT   
> #define SECTION\_SIZE (\_AC(1, UL) << SECTION\_SHIFT)   
> #define SECTION\_MASK (~(SECTION\_SIZE-1))

什么是section呢？我用一个实际的例子来描述好了。假设VA是48 bit，page size是4K，那么，在地址映射过程中，地址被分成9（level 0） ＋ 9（level 1） ＋ 9（level 2） ＋ 9（level 3） ＋ 12（page offset），对于kernel image这样的big block memory region，使用4K的page来mapping有点得不偿失，在这种情况下，可以考虑让level 2的Translation table entry指向一个2M 的memory region，而不是下一级的Translation table。所谓的section map就是指使用2M的为单位进行映射。对于其他的VA配置和page size的情况请大家自行理解吧，都是类似的。

对于L3级别的tranlation table而言，其描述符的定义和上图非常类似，只不过0b01是reserved，0b11是page描述符。L3的描述符不可能指向block descripotr或者table descriptor。具体定义如下：

> #define PTE\_TYPE\_MASK (\_AT(pteval\_t, 3) << 0)   
> #define PTE\_TYPE\_FAULT (\_AT(pteval\_t, 0) << 0)   
> #define PTE\_TYPE\_PAGE (\_AT(pteval\_t, 3) << 0)   
> #define PTE\_TABLE\_BIT (\_AT(pteval\_t, 1) << 1)

（还有一些其他相关的宏定义以后会慢慢补充）

参考文献：

1、ULK3 第二章

2、ARM Architecture Reference Manual(ARMv8, for ARMv8-A architecture profile)
