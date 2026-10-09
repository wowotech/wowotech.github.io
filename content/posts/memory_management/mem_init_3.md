---
title: "内存初始化代码分析（三）：创建系统内存地址映射"
date: 2016-11-24T12:08:56+08:00
url: "/memory_management/mem_init_3.html"
gid: "357"
emlog_type: "blog"
summary: "经过 内存初始化代码分析（一） 和 内存初始化代码分析（二） 的过渡，我们终于来到了内存初始化的核心部分：paging_init。当然本文不能全部解析完该函数（那需要的篇幅太长了），我们只关注创建系统内存地址映射这部分代码实现，也就是解析paging_init中的map_mem函数。 同样的，我们选择的是4.4.6的内核代码，体系结构相关的代码来自ARM64。"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["create_mapping"]
views: 27218
comment_count: 22
aliases:
  - "/memory_management/357.html"
  - "/357.html"
---

一、前言

经过[内存初始化代码分析（一）](/memory_management/__create_page_tables_code_analysis.html)和[内存初始化代码分析（二）](/memory_management/memory-layout.html)的过渡，我们终于来到了内存初始化的核心部分：paging\_init。当然本文不能全部解析完该函数（那需要的篇幅太长了），我们只关注创建系统内存地址映射这部分代码实现，也就是解析paging\_init中的map\_mem函数。

同样的，我们选择的是4.4.6的内核代码，体系结构相关的代码来自ARM64。

二、准备阶段

在进入实际的代码分析之前，我们首先回头看看目前内存的状态。偌大的物理地址空间中，系统内存占据了一段或者几段地址空间，这些信息被保存在了memblock模块中的memory type类型的数组中，数组中每一个memory region描述了一段系统内存信息（base、size以及node id）。OK，系统内存就这么多，但是也并非所有的memory type类型的数组中区域都是free的，实际上，有些已经被使用或者保留使用的内存区域需要从memory type类型的一段或者几段地址空间中摘取下来，并定义在reserved type类型的数组中。实际上，在整个系统初始化过程中（更具体的说是内存管理模块完成初始化之前），我们都需要暂时使用memblock这样一个booting阶段的内存管理模块来暂时进行内存的管理（收集内存布局信息只是它的副业），每次分配的内存都是在reserved type数组中增加一个新的item或者扩展其中一个memory region的size而已。

通过memblock模块，我们已经收集了内存布局的信息（memory type类型的数组），也知道了free memory资源的信息（memory type类型的数组减去reserved type类型的数组，从集合论的角度看，reserved type类型的数组是memory type类型的数组的真子集），但是，要管理这些珍贵的系统内存，首先要能够访问他们啊（顺便说一句：memblock中的那些数组定义的地址都是物理地址），通过前面的分析文章，我们知道有两段内存已经是可见的（完成了地址映射），一个是kernel image段，另外一个是fdt段。而广大的系统内存区域仍然在黑暗之中，等待我们去拯救（进行地址映射）。

最后，我们思考这样一个问题：是否memory type类型的数组代表了整个的系统内存的地址空间呢？当然不是，有些驱动可能会保留一段系统内存区域为自己使用，同时也不希望OS管理这段内存（或者说对OS不可见），而是自己创建该段内存的地址映射。如果你对dts中的memory reserve节点比较熟悉的话，那么实际上这样的reserved memory region是有no-map属性的。这时候，内核初始化过程中，在解析该reserved-memory节点的时候，会将该段地址从memblock模块中移除。而在map\_mem函数中，为所有memory type类型的数组创建地址映射的时候，有no-map属性的那段内存地址将不会创建地址映射，也就不在OS的控制范围内了。

三、概览

创建系统内存地址映射的代码在map\_mem中，如下：

> static void \_\_init map\_mem(void) {   
> struct memblock\_region \*reg;   
> phys\_addr\_t limit;
>
> limit = PHYS\_OFFSET + SWAPPER\_INIT\_MAP\_SIZE;－－－－－－－－－－－－－－－（1）   
> memblock\_set\_current\_limit(limit);
>
> for\_each\_memblock(memory, reg) {－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> phys\_addr\_t start = reg->base;――确定该region的起始地址   
> phys\_addr\_t end = start + reg->size; ――确定该region的结束地址
>
> if (start >= end)－－参数检查   
> break;
>
> if (ARM64\_SWAPPER\_USES\_SECTION\_MAPS) {－－－－－－－－－－－－－－－－（3）   
> if (start < limit)   
> start = ALIGN(start, SECTION\_SIZE);   
> if (end < limit) {   
> limit = end & SECTION\_MASK;   
> memblock\_set\_current\_limit(limit);   
> }   
> }   
> \_\_map\_memblock(start, end);－－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> }
>
> memblock\_set\_current\_limit(MEMBLOCK\_ALLOC\_ANYWHERE);－－－－－－－－－－（5）   
> }

（1）首先限制了当前memblock的上限。之所以这么做是因为在进行mapping的时候，如果任何一级的Translation table不存在的话都需要进行页表内存的分配。而在这个时间点上，伙伴系统没有ready，无法动态分配。当然，这时候memblock已经ready了，但是如果分配的内存都还没有创建地址映射（整个物理内存布局已知并且保存在了memblock模块中的memblock模块中，但是并非所有系统内存的地址映射都已经建立好的，而我们map\_mem函数的本意就是要创建所有系统内存的mapping），内核一旦访问memblock\_alloc分配的物理内存，悲剧就会发生了。怎么破？这里采用了限定memblock上限的方法。一旦设定了上限，那么memblock\_alloc分配的物理内存不会高于这个上限。

设定怎样的上限呢？基本思路就是在map\_mem的调用过程中，不需要分配translation table，怎么做到呢？当然是尽量利用已经静态定义好的那些页表了。PHYS\_OFFSET是物理内存的起始地址，SWAPPER\_INIT\_MAP\_SIZE 是启动阶段kernel direct mapping的size。也就是说，从PHYS\_OFFSET到PHYS\_OFFSET + SWAPPER\_INIT\_MAP\_SIZE的区域，所有的页表（各个level的translation table）都已经OK，不需要分配，只需要把描述符写入页表即可。因此，如果将当前memblock分配的上限设定在这里将不会产生内存分配的动作（因为页表都已经ready）。

（2）对系统中所有的memory type的region建立对应的地址映射。由于reserved type的memory region是memory type的region的真子集，因此reserved memory 的地址映射也就一并建立了。

（3）如果不使用section map，那么我们在kernel direct mapping区域静态分配了PGD~PTE的页表，通过起始地址对齐以及对memblock limit的设定就可以保证在create\_mapping（）的时候不分配页表内存。但是在下面的情况下：

（A）Memory block的start或者end地址并没有对齐在2M上

（B）使用section map

在这种情况下，调用create\_mapping（）的时候会分配pte页表内存（没有对齐2M，无法进行section mapping）。怎么破？还好第一个memory block（也就是kernel image所在的block）的start address是必定对齐在2M地址上的，所以只要考虑end地址，这时候需要适当的缩小limit到end & SECTION\_MASK就可以保证分配的页表内存是已经建立地址映射的了。

（4）\_\_map\_memblock代码如下：

> static void \_\_init \_\_map\_memblock(phys\_addr\_t start, phys\_addr\_t end)   
> {   
> create\_mapping(start, \_\_phys\_to\_virt(start), end - start,   
> PAGE\_KERNEL\_EXEC);   
> }

需要说明的是，在map\_mem之后，所有之前通过\_\_create\_page\_tables创建的描述符都被覆盖了，取而代之的是新的映射，并且memory attribute如下：

> #define PAGE\_KERNEL\_EXEC \_\_pgprot(\_PAGE\_DEFAULT | PTE\_UXN | PTE\_DIRTY | PTE\_WRITE)

大部分memory attribute保持不变（例如MT\_NORMAL、PTE\_AF 、 PTE\_SHARED等），有几个bit需要说明一下：PTE\_UXN，Unprivileged Execute-never bit，也就是限制userspace从这里取指执行。PTE\_DIRTY是一个软件设定的bit，硬件并不操作这个bit，OS软件用这个bit标识该entry是clean or dirty，如果是dirty的话，说明该page的数据已经被写入过，如果该page需要被swapped out，那么还需要保存dirty的数据才能回收该page。关于PTE\_WRITE的解释todo。

（5）所有的系统内存的地址映射已经建立完毕，取消之前的上限，让memblock模块可以自由的分配内存。

四、填充PGD中的描述符

create\_mapping实际上是调用底层的\_\_create\_mapping函数完成地址映射的，具体代码如下：

> static void \_\_init create\_mapping(phys\_addr\_t phys, unsigned long virt,   
> phys\_addr\_t size, pgprot\_t prot)   
> {   
> if (virt < VMALLOC\_START) {   
> pr\_warn("BUG: not creating mapping for %pa at 0x%016lx - outside kernel range\n",   
> &phys, virt);   
> return;   
> }   
> \_\_create\_mapping(&init\_mm, pgd\_offset\_k(virt & PAGE\_MASK), phys, virt,   
> size, prot, early\_alloc);   
> }

create\_mapping的作用是将起始物理地址等于phys，大小是size的这一段物理内存mapping到起始虚拟地址是virt的虚拟地址空间，映射的memory attribute是prot。内核的虚拟地址空间从VMALLOC\_START开始，低于这个地址就不对了，验证完虚拟地址，底层是调用\_\_create\_mapping函数，传递的参数情况是这样的，init\_mm是内核空间的内存描述符，pgd\_offset\_k是根据给定的虚拟地址，在kernel space的pgd中找到对应的描述符的位置，early\_alloc是在mapping过程中，如果需要分配内存的话（页表需要内存），调用该函数进行内存的分配。\_\_create\_mapping函数具体代码如下：

> static void \_\_create\_mapping(struct mm\_struct \*mm, pgd\_t \*pgd,   
> phys\_addr\_t phys, unsigned long virt,   
> phys\_addr\_t size, pgprot\_t prot,   
> void \*(\*alloc)(unsigned long size))   
> {   
> unsigned long addr, length, end, next;
>
> addr = virt & PAGE\_MASK;－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> length = PAGE\_ALIGN(size + (virt & ~PAGE\_MASK));
>
> end = addr + length;   
> do {－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> next = pgd\_addr\_end(addr, end);－－－－－－－－－－－－－－－－－－－－（3）   
> alloc\_init\_pud(mm, pgd, addr, next, phys, prot, alloc);－－－－－－－－－－（4）   
> phys += next - addr;   
> } while (pgd++, addr = next, addr != end);   
> }

创建地址映射熟悉要明确地址空间，不同的进程有不同的地址空间，struct mm\_struct就是描述一个进程的虚拟地址空间，当然，我们这里的场景是为内核虚拟地址空间而创建地址映射，因此传递的参数是init\_mm。需要创建地址映射的起始虚拟地址是virt，该虚拟地址对应的PUD中的描述符是一个8B的内存，pgd就是指向这个描述符内存的指针。

（1）因为地址映射的最小单位是page，因此这里进行mapping的虚拟地址需要对齐到page size，同样的，长度也需要对齐到page size。经过对齐运算，（addr，length）定义的地址范围应该是囊括（virt，size）定义的地址范围，并且是对齐到page的。

（2）（addr，length）这个虚拟地址范围可能需要占据多个PGD entry，因此这里我们需要一个循环，不断的调用alloc\_init\_pud函数来完成（addr，length）这个虚拟地址范围的映射，当然，alloc\_init\_pud函数其实也会建立下游（例如PUD、PMD、PTE）翻译表的entry。

（3）pgd中的一个描述符只能mapping有限区域的虚拟地址（PGDIR\_SIZE），pgd\_addr\_end的宏就是计算addr所在区域的end address。如果计算出来的end address小于传入的end地址参数，那么返回end参数值。也就是说，如果（addr，length）这个虚拟地址范围的mapping需要跨越多个pgd entry，那么next变量保存了下一个pgd entry的起始虚拟地址。

（4）这个函数有两个作用，一是填充pgd entry，二是创建后续的pud translation table（如果需要的话）并进行下游Translation table的建立。

五、分配PUD页表内存并填充相应的描述符

alloc\_init\_pud并非只是操作pud，实际上它是操作pgd的一个entry，并分配初始pud以及后续translation table的。填充PGD的entry需要给出对应PUD translation table的内存地址，如果PUD不存在，那么alloc\_init\_pud还需要分配PUD translation table（page size），只有得到PUD翻译表的物理内存地址，我们才能填充PGD entry。具体代码如下：

> static void alloc\_init\_pud(struct mm\_struct \*mm, pgd\_t \*pgd,   
> unsigned long addr, unsigned long end,   
> phys\_addr\_t phys, pgprot\_t prot,   
> void \*(\*alloc)(unsigned long size))   
> {   
> pud\_t \*pud;   
> unsigned long next;
>
> if (pgd\_none(\*pgd)) {－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> pud = alloc(PTRS\_PER\_PUD \* sizeof(pud\_t));   
> pgd\_populate(mm, pgd, pud);   
> }   
> pud = pud\_offset(pgd, addr); －－－－－－－－－－－－－－－－－－－－－（2）   
> do { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> next = pud\_addr\_end(addr, end);
>
> if (use\_1G\_block(addr, next, phys)) { －－－－－－－－－－－－－－－－（4）   
> pud\_t old\_pud = \*pud;   
> set\_pud(pud, \_\_pud(phys | pgprot\_val(mk\_sect\_prot(prot)))); －－－－－（5）
>
> if (!pud\_none(old\_pud)) { －－－－－－－－－－－－－－－－－－－－－（6）   
> flush\_tlb\_all(); －－－－－－－－－－－－－－－－－－－－－－－－（7）   
> if (pud\_table(old\_pud)) {   
> phys\_addr\_t table = \_\_pa(pmd\_offset(&old\_pud, 0));   
> if (!WARN\_ON\_ONCE(slab\_is\_available()))   
> memblock\_free(table, PAGE\_SIZE); －－－－－－－－－－－－（8）   
> }   
> }   
> } else {   
> alloc\_init\_pmd(mm, pud, addr, next, phys, prot, alloc);   
> }   
> phys += next - addr;   
> } while (pud++, addr = next, addr != end);   
> }

（1）如果当前pgd entry是全0的话，说明还没有对应的下级PUD页表内存，因此需要进行PUD页表内存的分配。需要说明的是这时候，伙伴系统没有ready，分配内存仍然使用memblock模块，pgd\_populate用来建立pgd entry和PUD 页表内存的关系。

（2）至此，pud的页表内存已经有了，但是addr对应PUD中的哪一个描述符呢？pud\_offset给出了答案，其返回的指针指向传入参数addr地址对应的pud 描述符内存，而我们随后的任务就是填充pud entry了。

（3）虽然（addr，end）之间的虚拟地址范围共享一个pgd entry，但是这个地址范围对应的pud entry可能有多个，通过循环，逐一填充pud entry，同时分配并初始化下一阶页表。

（4）如果没有可能存在的1G block地址映射，这里的代码逻辑和上一节中的类似，只不过不断的循环调用alloc\_init\_pud改成alloc\_init\_pmd即可。然而，ARM64的MMU硬件提供了灰常强大的功能，系统支持1G size的block mapping，如果能够应用会获取非常多的好处：不需要分配下级的translation table节省了内存，更重要的是大大降低了TLB miss，提高了性能。既然这么好，当然要使用，不过有什么条件呢？首先系统配置必须是4k的page size，这种配置下，一个PUD entry可以覆盖1G的memory block。此外，起止虚拟地址以及映射到的物理地址都必须要对齐在1G size上。

（5）填写一个PUD描述符，一次搞定1G size的address mapping，没有PMD和PTE的页表内存，没有对PMD 和PTE描述符的访问，多么简单，多么美妙啊。假设系统内存4G，并且物理地址对齐在1G上（虚拟地址PAGE\_OFFSET本来就是对齐在1G的），那么4个PUD的描述符就搞定了内核空间的线性地址映射区间。

（6）如果pud entry是非空的，那么就说明之前已经有了对该段地址的mapping（也许是只映射了部分）。一个简单的例子就是起始阶段的kernel image mapping，在\_\_create\_page\_tables创建pud 以及pmd中entry。如果不能进行section mapping，那么还建立了PTE中的描述符，现在这些描述符都没有用了，我们可以丢弃它们了。

（7）虽然建立了新的页表，但是旧的页表还残留在了TLB中，必须将其“赶尽杀绝”，清除出TLB。

（8）如果pud指向了一个table描述符，也就是说明该entry指向一个PMD table，那么需要释放其memory。

六、分配PMD页表内存并填充相应的描述符

1G block mapping虽好，不一定适合所有的系统，下面我一起看看PUD entry中填充的是block descriptor的情况（描述符指向PMD translation table）：

> static void alloc\_init\_pmd(struct mm\_struct \*mm, pud\_t \*pud,   
> unsigned long addr, unsigned long end,   
> phys\_addr\_t phys, pgprot\_t prot,   
> void \*(\*alloc)(unsigned long size))   
> {   
> pmd\_t \*pmd;   
> unsigned long next;
>
> if (pud\_none(\*pud) || pud\_sect(\*pud)) {－－－－－－－－－－－－－－－－－－－（1）   
> pmd = alloc(PTRS\_PER\_PMD \* sizeof(pmd\_t));－－－分配pmd页表内存   
> if (pud\_sect(\*pud)) {－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> split\_pud(pud, pmd);   
> }   
> pud\_populate(mm, pud, pmd);－－－－－－－－－－－－－－－－－－－－－（3）   
> flush\_tlb\_all();   
> }   
> BUG\_ON(pud\_bad(\*pud));
>
> pmd = pmd\_offset(pud, addr);－－－－－－－－－－－－－－－－－－－－－－－（4）   
> do {   
> next = pmd\_addr\_end(addr, end);   
> if (((addr | next | phys) & ~SECTION\_MASK) == 0) {－－－－－－－－－－－－（5）   
> pmd\_t old\_pmd =\*pmd;   
> set\_pmd(pmd, \_\_pmd(phys | pgprot\_val(mk\_sect\_prot(prot))));   
>   
> if (!pmd\_none(old\_pmd)) {－－－－－－－－－－－－－－－－－－－－－－（6）   
> flush\_tlb\_all();   
> if (pmd\_table(old\_pmd)) {   
> phys\_addr\_t table = \_\_pa(pte\_offset\_map(&old\_pmd, 0));   
> if (!WARN\_ON\_ONCE(slab\_is\_available()))   
> memblock\_free(table, PAGE\_SIZE);   
> }   
> }   
> } else {   
> alloc\_init\_pte(pmd, addr, next, \_\_phys\_to\_pfn(phys),   
> prot, alloc);   
> }   
> phys += next - addr;   
> } while (pmd++, addr = next, addr != end);   
> }

（1）有两个场景需要分配PMD的页表内存，一个是该pud entry是空的，我们需要分配后续的PMD页表内存。另外一个是旧的pud entry是section 描述符，映射了1G的address block。但是现在由于种种原因，我们需要修改它，故需要remove这个1G block的section mapping。

（2）虽然是建立新的mapping，但是原来旧的1G mapping也要保留的，也许这次我们只是想更新部分地址映射呢。在这种情况下，我们先通过split\_pud函数调用把一个1G block mapping转换成通过pmd进行mapping的形式（一个pud的section mapping描述符（1G size）变成了512个pmd中的section mapping描述符（2M size）。形式变了，味道不变，加量不加价，仍然是1G block的地址映射。

（3）修正pud entry，让其指向新的pmd页表内存，同时flush tlb的内容。

（4）下面这段代码的逻辑起始是和alloc\_init\_pud是类似的。如果不能进行2M的section mapping，那么就循环调用alloc\_init\_pte进行地址的mapping，这里我们就不多说了，重点看看2M section mapping的处理。

（5）如果满足2M section的要求，那么就调用set\_pmd填充pmd entry。

（6）如果有旧的section mapping，并且指向一个PTE table，那么还需要释放这些不需要的PTE页表描述符占用的内存。

七、分配PTE页表内存并填充相应的描述符

> static void alloc\_init\_pte(pmd\_t \*pmd, unsigned long addr,   
> unsigned long end, unsigned long pfn,   
> pgprot\_t prot,   
> void \*(\*alloc)(unsigned long size))   
> {   
> pte\_t \*pte;
>
> if (pmd\_none(\*pmd) || pmd\_sect(\*pmd)) {－－－－－－－－－－－－－－－－（1）   
> pte = alloc(PTRS\_PER\_PTE \* sizeof(pte\_t));   
> if (pmd\_sect(\*pmd))   
> split\_pmd(pmd, pte);－－－－－－－－－－－－－－－－－－－－－－（2）   
> \_\_pmd\_populate(pmd, \_\_pa(pte), PMD\_TYPE\_TABLE);－－－－－－－－（3）   
> flush\_tlb\_all();   
> }   
> BUG\_ON(pmd\_bad(\*pmd));
>
> pte = pte\_offset\_kernel(pmd, addr);   
> do {   
> set\_pte(pte, pfn\_pte(pfn, prot));－－－－－－－－－－－－－－－－－－－（4）   
> pfn++;   
> } while (pte++, addr += PAGE\_SIZE, addr != end);   
> }

（1）走到这个函数，说明后续需要建立PTE这一个level的页表描述符，因此，需要分配PTE页表内存，场景有两个，一个是从来没有进行过映射，另外一个是已经建立映射，但是是section mapping，不符合要求。

（2）如果之前有section mapping，那么我们需要将其分裂成512个pte中的page descriptor。

（3）让pmd entry指向新的pte页表内存。需要说明的是：如果之前pmd entry是空的，那么新的pte页表中有512个invalid descriptor，如果之前有section mapping，那么实际上这个新的PTE页表已经通过split\_pmd填充了512个page descritor。

（4）循环设定（addr，end）这段地址区域的pte中的page descriptor。

参考文献：

1、ARMv8技术手册

2、Linux 4.4.6内核源代码

*原创文章，转发请注明出处。蜗窝科技*
