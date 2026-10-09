---
title: "Device Tree（三）：代码分析"
date: 2014-06-06T16:03:48+08:00
url: "/device_model/dt-code-analysis.html"
gid: "48"
emlog_type: "blog"
summary: "Device Tree总共有三篇，分别是： 1、为何要引入Device Tree，这个机制是用来解决什么问题的？（请参考 引入Device Tree的原因 ） 2、Device Tree的基础概念（请参考 DT基础概念 ） 3、ARM linux中和Device Tree相关的代码分析（这是本文的主题） 本文主要内容是：以Device Tree相关的数据流分析为索引，对ARM linux kern"
author: "linuxer"
category: "统一设备模型"
category_alias: "device_model"
tags: ["设备树"]
views: 174103
comment_count: 162
aliases:
  - "/device_model/48.html"
  - "/48.html"
---

一、前言

Device Tree总共有三篇，分别是：

1、为何要引入Device Tree，这个机制是用来解决什么问题的？（请参考[引入Device Tree的原因](/device_model/why-dt.html)）

2、Device Tree的基础概念（请参考[DT基础概念](/device_model/dt_basic_concept.html)）

3、ARM linux中和Device Tree相关的代码分析（这是本文的主题）

本文主要内容是：以Device Tree相关的数据流分析为索引，对ARM linux kernel的代码进行解析。主要的数据流包括：

1、初始化流程。也就是扫描dtb并将其转换成Device Tree Structure。

2、传递运行时参数传递以及platform的识别流程分析

3、如何将Device Tree Structure并入linux kernel的设备驱动模型。

注：本文中的linux kernel使用的是3.14版本。

二、如何通过Device Tree完成运行时参数传递以及platform的识别功能？

1、汇编部分的代码分析

linux/arch/arm/kernel/head.S文件定义了bootloader和kernel的参数传递要求：

> MMU = off, D-cache = off, I-cache = dont care, r0 = 0, r1 = machine nr, r2 = atags or dtb pointer.

目前的kernel支持旧的tag list的方式，同时也支持device tree的方式。r2可能是device tree binary file的指针（bootloader要传递给内核之前要copy到memory中），也可以能是tag list的指针。在ARM的汇编部分的启动代码中（主要是head.S和head-common.S），machine type ID和指向DTB或者atags的指针被保存在变量\_\_machine\_arch\_type和\_\_atags\_pointer中，这么做是为了后续c代码进行处理。

2、和device tree相关的setup\_arch代码分析

具体的c代码都是在setup\_arch中处理，这个函数是一个总的入口点。具体代码如下（删除了部分无关代码）：

> void \_\_init setup\_arch(char \*\*cmdline\_p)   
> {   
> const struct machine\_desc \*mdesc;
>
> ……
>
> mdesc = setup\_machine\_fdt(\_\_atags\_pointer);   
> if (!mdesc)   
> mdesc = setup\_machine\_tags(\_\_atags\_pointer, \_\_machine\_arch\_type);   
> machine\_desc = mdesc;   
> machine\_name = mdesc->name;
>
> ……   
> }

对于如何确定HW platform这个问题，旧的方法是静态定义若干的machine描述符（struct machine\_desc ），在启动过程中，通过machine type ID作为索引，在这些静态定义的machine描述符中扫描，找到那个ID匹配的描述符。在新的内核中，首先使用setup\_machine\_fdt来setup machine描述符，如果返回NULL，才使用传统的方法setup\_machine\_tags来setup machine描述符。传统的方法需要给出\_\_machine\_arch\_type（bootloader通过r1寄存器传递给kernel的）和tag list的地址（用来进行tag parse）。\_\_machine\_arch\_type用来寻找machine描述符；tag list用于运行时参数的传递。随着内核的不断发展，相信有一天linux kernel会完全抛弃tag list的机制。

3、匹配platform（machine描述符）

setup\_machine\_fdt函数的功能就是根据Device Tree的信息，找到最适合的machine描述符。具体代码如下：

> const struct machine\_desc \* \_\_init setup\_machine\_fdt(unsigned int dt\_phys)   
> {   
> const struct machine\_desc \*mdesc, \*mdesc\_best = NULL;
>
> if (!dt\_phys || !early\_init\_dt\_scan(phys\_to\_virt(dt\_phys)))   
> return NULL;
>
> mdesc = of\_flat\_dt\_match\_machine(mdesc\_best, arch\_get\_next\_mach);
>
> if (!mdesc) {   
> 出错处理   
> }
>
> /\* Change machine number to match the mdesc we're using \*/   
> \_\_machine\_arch\_type = mdesc->nr;
>
> return mdesc;   
> }

early\_init\_dt\_scan函数有两个功能，一个是为后续的DTB scan进行准备工作，另外一个是运行时参数传递。具体请参考下面一个section的描述。

of\_flat\_dt\_match\_machine是在machine描述符的列表中scan，找到最合适的那个machine描述符。我们首先看如何组成machine描述符的列表。和传统的方法类似，也是静态定义的。DT\_MACHINE\_START和MACHINE\_END用来定义一个machine描述符。编译的时候，compiler会把这些machine descriptor放到一个特殊的段中（.arch.info.init），形成machine描述符的列表。machine描述符用下面的数据结构来标识（删除了不相关的member）：

> struct machine\_desc {   
> unsigned int nr; /\* architecture number \*/   
> const char \*const \*dt\_compat; /\* array of device tree 'compatible' strings \*/
>
> ……
>
> };

nr成员就是过去使用的machine type ID。内核machine描述符的table有若干个entry，每个都有自己的ID。bootloader传递了machine type ID，指明使用哪一个machine描述符。目前匹配machine描述符使用compatible strings，也就是dt\_compat成员，这是一个string list，定义了这个machine所支持的列表。在扫描machine描述符列表的时候需要不断的获取下一个machine描述符的compatible字符串的信息，具体的代码如下：

> static const void \* \_\_init arch\_get\_next\_mach(const char \*const \*\*match)   
> {   
> static const struct machine\_desc \*mdesc = \_\_arch\_info\_begin;   
> const struct machine\_desc \*m = mdesc;
>
> if (m >= \_\_arch\_info\_end)   
> return NULL;
>
> mdesc++;   
> \*match = m->dt\_compat;   
> return m;   
> }

\_\_arch\_info\_begin指向machine描述符列表第一个entry。通过mdesc++不断的移动machine描述符指针（Note：mdesc是static的）。match返回了该machine描述符的compatible string list。具体匹配的算法倒是很简单，就是比较字符串而已，一个是root node的compatible字符串列表，一个是machine描述符的compatible字符串列表，得分最低的（最匹配的）就是我们最终选定的machine type。

4、运行时参数传递

运行时参数是在扫描DTB的chosen node时候完成的，具体的动作就是获取chosen node的bootargs、initrd等属性的value，并将其保存在全局变量（boot\_command\_line，initrd\_start、initrd\_end）中。使用tag list方法是类似的，通过分析tag list，获取相关信息，保存在同样的全局变量中。具体代码位于early\_init\_dt\_scan函数中：

> bool \_\_init early\_init\_dt\_scan(void \*params)   
> {   
> if (!params)   
> return false;
>
> /\* 全局变量initial\_boot\_params指向了DTB的header\*/   
> initial\_boot\_params = params;
>
> /\* 检查DTB的magic，确认是一个有效的DTB \*/   
> if (be32\_to\_cpu(initial\_boot\_params->magic) != OF\_DT\_HEADER) {   
> initial\_boot\_params = NULL;   
> return false;   
> }
>
> /\* 扫描 /chosen node，保存运行时参数（bootargs）到boot\_command\_line，此外，还处理initrd相关的property，并保存在initrd\_start和initrd\_end这两个全局变量中 \*/   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_chosen, boot\_command\_line);
>
> /\* 扫描根节点，获取 {size,address}-cells信息，并保存在dt\_root\_size\_cells和dt\_root\_addr\_cells全局变量中 \*/   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_root, NULL);
>
> /\* 扫描DTB中的memory node，并把相关信息保存在meminfo中，全局变量meminfo保存了系统内存相关的信息。\*/   
> of\_scan\_flat\_dt(early\_init\_dt\_scan\_memory, NULL);
>
> return true;   
> }

设定meminfo（该全局变量确定了物理内存的布局）有若干种途径：

1、通过tag list（tag是ATAG\_MEM）传递memory bank的信息。

2、通过command line（可以用tag list，也可以通过DTB）传递memory bank的信息。

3、通过DTB的memory node传递memory bank的信息。

目前当然是推荐使用Device Tree的方式来传递物理内存布局信息。

三、初始化流程

在系统初始化的过程中，我们需要将DTB转换成节点是device\_node的树状结构，以便后续方便操作。具体的代码位于setup\_arch->unflatten\_device\_tree中。

> void \_\_init unflatten\_device\_tree(void)   
> {   
> \_\_unflatten\_device\_tree(initial\_boot\_params, &of\_allnodes,   
> early\_init\_dt\_alloc\_memory\_arch);
>
> /\* Get pointer to "/chosen" and "/aliases" nodes for use everywhere \*/   
> of\_alias\_scan(early\_init\_dt\_alloc\_memory\_arch);   
> }

我们用struct device\_node 来抽象设备树中的一个节点，具体解释如下：

> struct device\_node {   
> const char \*name;－－－－－－－－－－－－－－－－－－－－－－device node name   
> const char \*type;－－－－－－－－－－－－－－－－－－－－－－－对应device\_type的属性   
> phandle phandle;－－－－－－－－－－－－－－－－－－－－－－－对应该节点的phandle属性   
> const char \*full\_name; －－－－－－－－－－－－－－－－从“/”开始的，表示该node的full path
>
> struct property \*properties;－－－－－－－－－－－－－该节点的属性列表   
> struct property \*deadprops; －－－－－－－－－－如果需要删除某些属性，kernel并非真的删除，而是挂入到deadprops的列表   
> struct device\_node \*parent;－－－－－－parent、child以及sibling将所有的device node连接起来   
> struct device\_node \*child;   
> struct device\_node \*sibling;   
> struct device\_node \*next; －－－－－－－－通过该指针可以获取相同类型的下一个node   
> struct device\_node \*allnext;－－－－－－－通过该指针可以获取node global list下一个node   
> struct proc\_dir\_entry \*pde;－－－－－－－－开放到userspace的proc接口信息   
> struct kref kref;－－－－－－－－－－－－－该node的reference count   
> unsigned long \_flags;   
> void \*data;   
> };

unflatten\_device\_tree函数的主要功能就是扫描DTB，将device node被组织成：

1、global list。全局变量struct device\_node \*of\_allnodes就是指向设备树的global list

2、tree。

这些功能主要是在\_\_unflatten\_device\_tree函数中实现，具体代码如下（去掉一些无关紧要的代码）：

> static void \_\_unflatten\_device\_tree(struct boot\_param\_header \*blob,－－－需要扫描的DTB   
> struct device\_node \*\*mynodes,－－－－－－－－－global list指针   
> void \* (\*dt\_alloc)(u64 size, u64 align))－－－－－－内存分配函数   
> {   
> unsigned long size;   
> void \*start, \*mem;   
> struct device\_node \*\*allnextp = mynodes;
>
> 此处删除了health check代码，例如检查DTB header的magic，确认blob的确指向一个DTB。
>
> /\* scan过程分成两轮，第一轮主要是确定device-tree structure的长度，保存在size变量中 \*/   
> start = ((void \*)blob) + be32\_to\_cpu(blob->off\_dt\_struct);   
> size = (unsigned long)unflatten\_dt\_node(blob, 0, &start, NULL, NULL, 0);   
> size = ALIGN(size, 4);
>
> /\* 初始化的时候，并不是扫描到一个node或者property就分配相应的内存，实际上内核是一次性的分配了一大片内存，这些内存包括了所有的struct device\_node、node name、struct property所需要的内存。\*/   
> mem = dt\_alloc(size + 4, \_\_alignof\_\_(struct device\_node));   
> memset(mem, 0, size);
>
> \*(\_\_be32 \*)(mem + size) = cpu\_to\_be32(0xdeadbeef); //用来检验后面unflattening是否溢出
>
> /\* 这是第二轮的scan，第一次scan是为了得到保存所有node和property所需要的内存size，第二次就是实打实的要构建device node tree了 \*/   
> start = ((void \*)blob) + be32\_to\_cpu(blob->off\_dt\_struct);   
> unflatten\_dt\_node(blob, mem, &start, NULL, &allnextp, 0);
>
> 此处略去校验溢出和校验OF\_DT\_END。   
> }

具体的scan是在unflatten\_dt\_node函数中，如果已经清楚地了解DTB的结构，其实代码很简单，这里就不再细述了。

四、如何并入linux kernel的设备驱动模型

在linux kernel引入统一设备模型之后，bus、driver和device形成了设备模型中的铁三角。在驱动初始化的时候会将代表该driver的一个数据结构（一般是xxx\_driver）挂入bus上的driver链表。device挂入链表分成两种情况，一种是即插即用类型的bus，在插入一个设备后，总线可以检测到这个行为并动态分配一个device数据结构（一般是xxx\_device，例如usb\_device），之后，将该数据结构挂入bus上的device链表。bus上挂满了driver和device，那么如何让device遇到“对”的那个driver呢？那么就要靠缘分了，也就是bus的match函数。

上面是一段导论，我们还是回到Device Tree。导致Device Tree的引入ARM体系结构的代码其中一个最重要的原因的太多的静态定义的表格。例如：一般代码中会定义一个static struct platform\_device \*xxx\_devices的静态数组，在初始化的时候调用platform\_add\_devices。这些静态定义的platform\_device往往又需要静态定义各种resource，这导致静态表格进一步增大。如果ARM linux中不再定义这些表格，那么一定需要一个转换的过程，也就是说，系统应该会根据Device tree来动态的增加系统中的platform\_device。当然，这个过程并非只是发生在platform bus上（具体可以参考[“Platform Device”的设备](/device_model/platform_device.html)），也可能发生在其他的非即插即用的bus上，例如AMBA总线、PCI总线。一言以蔽之，如果要并入linux kernel的设备驱动模型，那么就需要根据device\_node的树状结构（root是of\_allnodes）将一个个的device node挂入到相应的总线device链表中。只要做到这一点，总线机制就会安排device和driver的约会。

当然，也不是所有的device node都会挂入bus上的设备链表，比如cpus node，memory node，choose node等。

1、cpus node的处理

这部分的处理可以参考setup\_arch->arm\_dt\_init\_cpu\_maps中的代码，具体的代码如下：

> void \_\_init arm\_dt\_init\_cpu\_maps(void)   
> {   
> scan device node global list，寻找full path是“/cpus”的那个device node。cpus这个device node只是一个容器，其中包括了各个cpu node的定义以及所有cpu node共享的property。   
> cpus = of\_find\_node\_by\_path("/cpus");
>
> for\_each\_child\_of\_node(cpus, cpu) { 遍历cpus的所有的child node   
> u32 hwid;
>
> if (of\_node\_cmp(cpu->type, "cpu")) 我们只关心那些device\_type是cpu的node   
> continue;
>
> if (of\_property\_read\_u32(cpu, "reg", &hwid)) { 读取reg属性的值并赋值给hwid   
> return;   
> }
>
> reg的属性值的8 MSBs必须设置为0，这是ARM CPU binding定义的。   
> if (hwid & ~MPIDR\_HWID\_BITMASK)   
> return;
>
> 不允许重复的CPU id，那是一个灾难性的设定   
> for (j = 0; j < cpuidx; j++)   
> if (WARN(tmp\_map[j] == hwid, "Duplicate /cpu reg "   
> "properties in the DT\n"))   
> return;
>
> 数组tmp\_map保存了系统中所有CPU的MPIDR值（CPU ID值），具体的index的编码规则是： tmp\_map[0]保存了booting CPU的id值，其余的CPU的ID值保存在1～NR\_CPUS的位置。   
> if (hwid == mpidr) {   
> i = 0;   
> bootcpu\_valid = true;   
> } else {   
> i = cpuidx++;   
> }
>
> tmp\_map[i] = hwid;   
> }
>
> 根据DTB中的信息设定cpu logical map数组。
>
> for (i = 0; i < cpuidx; i++) {   
> set\_cpu\_possible(i, true);   
> cpu\_logical\_map(i) = tmp\_map[i];   
> }   
> }

要理解这部分的内容，需要理解ARM CUPs binding的概念，可以参考linux/Documentation/devicetree/bindings/arm目录下的CPU.txt文件的描述。

2、memory的处理

这部分的处理可以参考setup\_arch->setup\_machine\_fdt->early\_init\_dt\_scan->early\_init\_dt\_scan\_memory中的代码。具体如下：

> int \_\_init early\_init\_dt\_scan\_memory(unsigned long node, const char \*uname,   
> int depth, void \*data)   
> {   
> char \*type = of\_get\_flat\_dt\_prop(node, "device\_type", NULL); 获取device\_type属性值   
> \_\_be32 \*reg, \*endp;   
> unsigned long l;
>
> 在初始化的时候，我们会对每一个device node都要调用该call back函数，因此，我们要过滤掉那些和memory block定义无关的node。和memory block定义有的节点有两种，一种是node name是memory@形态的，另外一种是node中定义了device\_type属性并且其值是memory。   
> if (type == NULL) {   
> if (depth != 1 || strcmp(uname, "memory@0") != 0)   
> return 0;   
> } else if (strcmp(type, "memory") != 0)   
> return 0;
>
> 获取memory的起始地址和length的信息。有两种属性和该信息有关，一个是linux,usable-memory，不过最新的方式还是使用reg属性。
>
> reg = of\_get\_flat\_dt\_prop(node, "linux,usable-memory", &l);   
> if (reg == NULL)   
> reg = of\_get\_flat\_dt\_prop(node, "reg", &l);   
> if (reg == NULL)   
> return 0;
>
> endp = reg + (l / sizeof(\_\_be32));
>
> reg属性的值是address，size数组，那么如何来取出一个个的address/size呢？由于memory node一定是root node的child，因此dt\_root\_addr\_cells（root node的#address-cells属性值）和dt\_root\_size\_cells（root node的#size-cells属性值）之和就是address，size数组的entry size。
>
> while ((endp - reg) >= (dt\_root\_addr\_cells + dt\_root\_size\_cells)) {   
> u64 base, size;
>
> base = dt\_mem\_next\_cell(dt\_root\_addr\_cells, ®);   
> size = dt\_mem\_next\_cell(dt\_root\_size\_cells, ®);
>
> early\_init\_dt\_add\_memory\_arch(base, size); 将具体的memory block信息加入到内核中。   
> }
>
> return 0;   
> }

3、interrupt controller的处理

初始化是通过start\_kernel->init\_IRQ->machine\_desc->init\_irq()实现的。我们用S3C2416为例来描述interrupt controller的处理过程。下面是machine描述符的定义。

> DT\_MACHINE\_START(S3C2416\_DT, "Samsung S3C2416 (Flattened Device Tree)")   
> ……   
> .init\_irq = irqchip\_init,   
> ……   
> MACHINE\_END

在driver/irqchip/irq-s3c24xx.c文件中定义了两个interrupt controller，如下：

> IRQCHIP\_DECLARE(s3c2416\_irq, "samsung,s3c2416-irq", s3c2416\_init\_intc\_of);
>
> IRQCHIP\_DECLARE(s3c2410\_irq, "samsung,s3c2410-irq", s3c2410\_init\_intc\_of);

当然，系统中可以定义更多的irqchip，不过具体用哪一个是根据DTB中的interrupt controller node中的compatible属性确定的。在driver/irqchip/irqchip.c文件中定义了irqchip\_init函数，如下：

> void \_\_init irqchip\_init(void)   
> {   
> of\_irq\_init(\_\_irqchip\_begin);   
> }

\_\_irqchip\_begin就是所有的irqchip的一个列表，of\_irq\_init函数是遍历Device Tree，找到匹配的irqchip。具体的代码如下：

> void \_\_init of\_irq\_init(const struct of\_device\_id \*matches)   
> {   
> struct device\_node \*np, \*parent = NULL;   
> struct intc\_desc \*desc, \*temp\_desc;   
> struct list\_head intc\_desc\_list, intc\_parent\_list;
>
> INIT\_LIST\_HEAD(&intc\_desc\_list);   
> INIT\_LIST\_HEAD(&intc\_parent\_list);
>
> 遍历所有的node，寻找定义了interrupt-controller属性的node，如果定义了interrupt-controller属性则说明该node就是一个中断控制器。
>
> for\_each\_matching\_node(np, matches) {   
> if (!of\_find\_property(np, "interrupt-controller", NULL) ||   
> !of\_device\_is\_available(np))   
> continue;
>
> 分配内存并挂入链表，当然还有根据interrupt-parent建立controller之间的父子关系。对于interrupt controller，它也可能是一个树状的结构。   
> desc = kzalloc(sizeof(\*desc), GFP\_KERNEL);   
> if (WARN\_ON(!desc))   
> goto err;
>
> desc->dev = np;   
> desc->interrupt\_parent = of\_irq\_find\_parent(np);   
> if (desc->interrupt\_parent == np)   
> desc->interrupt\_parent = NULL;   
> list\_add\_tail(&desc->list, &intc\_desc\_list);   
> }
>
> 正因为interrupt controller被组织成树状的结构，因此初始化的顺序就需要控制，应该从根节点开始，依次递进到下一个level的interrupt controller。   
> while (!list\_empty(&intc\_desc\_list)) { intc\_desc\_list链表中的节点会被一个个的处理，每处理完一个节点就会将该节点删除，当所有的节点被删除，整个处理过程也就是结束了。   
>   
> list\_for\_each\_entry\_safe(desc, temp\_desc, &intc\_desc\_list, list) {   
> const struct of\_device\_id \*match;   
> int ret;   
> of\_irq\_init\_cb\_t irq\_init\_cb;
>
> 最开始的时候parent变量是NULL，确保第一个被处理的是root interrupt controller。在处理完root node之后，parent变量被设定为root interrupt controller，因此，第二个循环中处理的是所有parent是root interrupt controller的child interrupt controller。也就是level 1（如果root是level 0的话）的节点。
>
> if (desc->interrupt\_parent != parent)   
> continue;
>
> list\_del(&desc->list); －－－－－从链表中删除   
> match = of\_match\_node(matches, desc->dev);－－－－－匹配并初始化   
> if (WARN(!match->data,－－－－－－－－－－match->data是初始化函数   
> "of\_irq\_init: no init function for %s\n",   
> match->compatible)) {   
> kfree(desc);   
> continue;   
> }
>
> irq\_init\_cb = (of\_irq\_init\_cb\_t)match->data;   
> ret = irq\_init\_cb(desc->dev, desc->interrupt\_parent);－－－－－执行初始化函数   
> if (ret) {   
> kfree(desc);   
> continue;   
> }
>
> 处理完的节点放入intc\_parent\_list链表，后面会用到   
> list\_add\_tail(&desc->list, &intc\_parent\_list);   
> }
>
> 对于level 0，只有一个root interrupt controller，对于level 1，可能有若干个interrupt controller，因此要遍历这些parent interrupt controller，以便处理下一个level的child node。   
> desc = list\_first\_entry\_or\_null(&intc\_parent\_list,   
> typeof(\*desc), list);   
> if (!desc) {   
> pr\_err("of\_irq\_init: children remain, but no parents\n");   
> break;   
> }   
> list\_del(&desc->list);   
> parent = desc->dev;   
> kfree(desc);   
> }
>
> list\_for\_each\_entry\_safe(desc, temp\_desc, &intc\_parent\_list, list) {   
> list\_del(&desc->list);   
> kfree(desc);   
> }   
> err:   
> list\_for\_each\_entry\_safe(desc, temp\_desc, &intc\_desc\_list, list) {   
> list\_del(&desc->list);   
> kfree(desc);   
> }   
> }

只有该node中有interrupt-controller这个属性定义，那么linux kernel就会分配一个interrupt controller的描述符（struct intc\_desc）并挂入队列。通过interrupt-parent属性，可以确定各个interrupt controller的层次关系。在scan了所有的Device Tree中的interrupt controller的定义之后，系统开始匹配过程。一旦匹配到了interrupt chip列表中的项次后，就会调用相应的初始化函数。如果CPU是S3C2416的话，匹配到的是irqchip的初始化函数是s3c2416\_init\_intc\_of。

OK，我们已经通过compatible属性找到了适合的interrupt controller，那么如何解析reg属性呢？我们知道，对于s3c2416的interrupt controller而言，其#interrupt-cells的属性值是4，定义为。每个域的解释如下：

（1）ctrl\_num表示使用哪一种类型的interrupt controller，其值的解释如下：

- 0 ... main controller   
- 1 ... sub controller   
- 2 ... second main controller

（2）parent\_irq。对于sub controller，parent\_irq标识了其在main controller的bit position。

（3）ctrl\_irq标识了在controller中的bit位置。

（4）type标识了该中断的trigger type，例如：上升沿触发还是电平触发。

为了更顺畅的描述后续的代码，我需要简单的介绍2416的中断控制器，其block diagram如下：

[![2416intc](/content/uploadfile/201406/af17f85d8a8d3d689caf5c62fcb8ea1420140606080340.gif "2416intc")](/content/uploadfile/201406/1fae6636c0a85be88e3177559936bad420140606080337.gif)

53个Samsung2416的中断源被分成两种类型，一种是需要sub寄存器进行控制的，例如DMA，系统中的8个DMA中断是通过两级识别的，先在SRCPND寄存器中得到是DMA中断的信息，具体是哪一个channel的DMA中断需要继续查询SUBSRC寄存器。那些不需要sub寄存器进行控制的，例如timer，5个timer的中断可以直接从SRCPND中得到。   
中断MASK寄存器可以控制产生的中断是否要报告给CPU，当一个中断被mask的时候，虽然SRCPND寄存器中，硬件会set该bit，但是不会影响到INTPND寄存器，从而不会向CPU报告该中断。对于SUBMASK寄存器，如果该bit被set，也就是该sub中断被mask了，那么即便产生了对应的sub中断，也不会修改SRCPND寄存器的内容，只是修改SUBSRCPND中寄存器的内容。

不过随着硬件的演化，更多的HW block加入到SOC中，这使得中断源不够用了，因此中断寄存器又被分成两个group，一个是group 1（开始地址是0X4A000000，也就是main controller了），另外一个是group2（开始地址是0X4A000040，叫做second main controller）。group 1中的sub寄存器的起始地址是0X4A000018（也就是sub controller）。

了解了上面的内容后，下面的定义就比较好理解了：

> static struct s3c24xx\_irq\_of\_ctrl s3c2416\_ctrl[] = {   
> {   
> .name = "intc", －－－－－－－－－－－main controller   
> .offset = 0,   
> }, {   
> .name = "subintc", －－－－－－－－－sub controller   
> .offset = 0x18,   
> .parent = &s3c\_intc[0],   
> }, {   
> .name = "intc2", －－－－－－－－－－second main controller   
> .offset = 0x40,   
> }   
> };

对于s3c2416而言，irqchip的初始化函数是s3c2416\_init\_intc\_of，s3c2416\_ctrl作为参数传递给了s3c\_init\_intc\_of，大部分的处理都是在s3c\_init\_intc\_of函数中完成的，由于这个函数和中断子系统非常相关，这里就不详述了，后续会有一份专门的文档描述之。

4、GPIO controller的处理

暂不描述，后续会有一份专门的文档描述GPIO sub system。

5、machine初始化

machine初始化的代码可以沿着start\_kernel->rest\_init->kernel\_init->kernel\_init\_freeable->do\_basic\_setup->do\_initcalls路径寻找。在do\_initcalls函数中，kernel会依次执行各个initcall函数，在这个过程中，会调用customize\_machine，具体如下：

> static int \_\_init customize\_machine(void)   
> {   
>   
> if (machine\_desc->init\_machine)   
> machine\_desc->init\_machine();   
> else   
> of\_platform\_populate(NULL, of\_default\_bus\_match\_table, NULL, NULL);   
>   
> return 0;   
> }   
> arch\_initcall(customize\_machine);

在这个函数中，一般会调用machine描述符中的init\_machine callback函数来把各种Device Tree中定义的platform device设备节点加入到系统（即platform bus的所有的子节点，对于device tree中其他的设备节点，需要在各自bus controller初始化的时候自行处理）。如果machine描述符中没有定义init\_machine函数，那么直接调用of\_platform\_populate把所有的platform device加入到kernel中。对于s3c2416，其machine描述符中的init\_machine callback函数就是s3c2416\_dt\_machine\_init，代码如下：

> static void \_\_init s3c2416\_dt\_machine\_init(void)   
> {   
> of\_platform\_populate(NULL, --------传入NULL参数表示从root node开始scan
>
> of\_default\_bus\_match\_table, s3c2416\_auxdata\_lookup, NULL);
>
> s3c\_pm\_init(); －－－－－－－－power management相关的初始化   
> }

由此可见，最终生成platform device的代码来自of\_platform\_populate函数。该函数的逻辑比较简单，遍历device node global list中所有的node，并调用of\_platform\_bus\_create处理，of\_platform\_bus\_create函数代码如下：

> static int of\_platform\_bus\_create(struct device\_node \*bus,-------------要创建的那个device node   
> const struct of\_device\_id \*matches,-------要匹配的list   
> const struct of\_dev\_auxdata \*lookup,------附属数据   
> struct device \*parent, bool strict)---------------parent指向父节点。strict是否要求完全匹配   
> {   
> const struct of\_dev\_auxdata \*auxdata;   
> struct device\_node \*child;   
> struct platform\_device \*dev;   
> const char \*bus\_id = NULL;   
> void \*platform\_data = NULL;   
> int rc = 0;
>
> 删除确保device node有compatible属性的代码。
>
> auxdata = of\_dev\_lookup(lookup, bus); 在传入的lookup table寻找和该device node匹配的附加数据   
> if (auxdata) {   
> bus\_id = auxdata->name;-----------------如果找到，那么就用附加数据中的静态定义的内容   
> platform\_data = auxdata->platform\_data;   
> }
>
> ARM公司提供了CPU core，除此之外，它设计了AMBA的总线来连接SOC内的各个block。符合这个总线标准的SOC上的外设叫做ARM Primecell Peripherals。如果一个device node的compatible属性值是arm,primecell的话，可以调用of\_amba\_device\_create来向amba总线上增加一个amba device。
>
> if (of\_device\_is\_compatible(bus, "arm,primecell")) {   
> of\_amba\_device\_create(bus, bus\_id, platform\_data, parent);   
> return 0;   
> }
>
> 如果不是ARM Primecell Peripherals，那么我们就需要向platform bus上增加一个platform device了
>
> dev = of\_platform\_device\_create\_pdata(bus, bus\_id, platform\_data, parent);   
> if (!dev || !of\_match\_node(matches, bus))   
> return 0;
>
> 一个device node可能是一个桥设备，因此要重复调用of\_platform\_bus\_create来把所有的device node处理掉。
>
> for\_each\_child\_of\_node(bus, child) {   
> pr\_debug(" create child: %s\n", child->full\_name);   
> rc = of\_platform\_bus\_create(child, matches, lookup, &dev->dev, strict);   
> if (rc) {   
> of\_node\_put(child);   
> break;   
> }   
> }   
> return rc;   
> }

具体增加platform device的代码在of\_platform\_device\_create\_pdata中，代码如下：

> static struct platform\_device \*of\_platform\_device\_create\_pdata(   
> struct device\_node \*np,   
> const char \*bus\_id,   
> void \*platform\_data,   
> struct device \*parent)   
> {   
> struct platform\_device \*dev;
>
> if (!of\_device\_is\_available(np))---------check status属性，确保是enable或者OK的。   
> return NULL;
>
> of\_device\_alloc除了分配struct platform\_device的内存，还分配了该platform device需要的resource的内存（参考struct platform\_device 中的resource成员）。当然，这就需要解析该device node的interrupt资源以及memory address资源。
>
> dev = of\_device\_alloc(np, bus\_id, parent);   
> if (!dev)   
> return NULL;
>
> 设定platform\_device 中的其他成员   
> dev->dev.coherent\_dma\_mask = DMA\_BIT\_MASK(32);   
> if (!dev->dev.dma\_mask)   
> dev->dev.dma\_mask = &dev->dev.coherent\_dma\_mask;   
> dev->dev.bus = &platform\_bus\_type;   
> dev->dev.platform\_data = platform\_data;
>
> if (of\_device\_add(dev) != 0) {------------------把这个platform device加入统一设备模型系统中   
> platform\_device\_put(dev);   
> return NULL;   
> }
>
> return dev;   
> }

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net。](/device_model/dt-code-analysis.html)
