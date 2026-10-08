---
title: "Linux kernel的中断子系统之（二）：IRQ Domain介绍"
date: 2014-08-19T18:46:30+08:00
url: "/irq_subsystem/irq-domain.html"
gid: "78"
emlog_type: "blog"
summary: "\r\n\t在linux kernel中，我们使用下面两个ID来标识一个来自外设的中断：\r\n\r\n\r\n\t1、IRQ number。CPU需要为每一个外设中断编号，我们称之IRQ Number。这个IRQ number是一个虚拟的interrupt ID，和硬件无关，仅仅是被CPU用来标识一个外设中断。\r\n\r\n\r\n\t2、\r\nHW interrupt ID。对于interrupt controller而言，它"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["irq_domain"]
views: 152412
comment_count: 80
aliases:
  - "/irq_subsystem/78.html"
  - "/78.html"
---

一、概述

在linux kernel中，我们使用下面两个ID来标识一个来自外设的中断：

1、IRQ number。CPU需要为每一个外设中断编号，我们称之IRQ Number。这个IRQ number是一个虚拟的interrupt ID，和硬件无关，仅仅是被CPU用来标识一个外设中断。

2、HW interrupt ID。对于interrupt controller而言，它收集了多个外设的interrupt request line并向上传递，因此，interrupt controller需要对外设中断进行编码。Interrupt controller用HW interrupt ID来标识外设的中断。在interrupt controller级联的情况下，仅仅用HW interrupt ID已经不能唯一标识一个外设中断，还需要知道该HW interrupt ID所属的interrupt controller（HW interrupt ID在不同的Interrupt controller上是会重复编码的）。

这样，CPU和interrupt controller在标识中断上就有了一些不同的概念，但是，对于驱动工程师而言，我们和CPU视角是一样的，我们只希望得到一个IRQ number，而不关系具体是那个interrupt controller上的那个HW interrupt ID。这样一个好处是在中断相关的硬件发生变化的时候，驱动软件不需要修改。因此，linux kernel中的中断子系统需要提供一个将HW interrupt ID映射到IRQ number上来的机制，这就是本文主要的内容。

二、历史

关于HW interrupt ID映射到IRQ number上 这事，在过去系统只有一个interrupt controller的时候还是很简单的，中断控制器上实际的HW interrupt line的编号可以直接变成IRQ number。例如我们大家都熟悉的SOC内嵌的interrupt controller，这种controller多半有中断状态寄存器，这个寄存器可能有64个bit（也可能更多），每个bit就是一个IRQ number，可以直接进行映射。这时候，GPIO的中断在中断控制器的状态寄存器中只有一个bit，因此所有的GPIO中断只有一个IRQ number，在该通用GPIO中断的irq handler中进行deduplex，将各个具体的GPIO中断映射到其相应的IRQ number上。如果你是一个足够老的工程师，应该是经历过这个阶段的。

随着linux kernel的发展，将interrupt controller抽象成irqchip这个概念越来越流行，甚至GPIO controller也可以被看出一个interrupt controller chip，这样，系统中至少有两个中断控制器了，一个传统意义的中断控制器，一个是GPIO controller type的中断控制器。随着系统复杂度加大，外设中断数据增加，实际上系统可以需要多个中断控制器进行级联，面对这样的趋势，linux kernel工程师如何应对？答案就是irq domain这个概念。

我们听说过很多的domain，power domain，clock domain等等，所谓domain，就是领域，范围的意思，也就是说，任何的定义出了这个范围就没有意义了。系统中所有的interrupt controller会形成树状结构，对于每个interrupt controller都可以连接若干个外设的中断请求（我们称之interrupt source），interrupt controller会对连接其上的interrupt source（根据其在Interrupt controller中物理特性）进行编号（也就是HW interrupt ID了）。但这个编号仅仅限制在本interrupt controller范围内。

三、接口

1、向系统注册irq domain

具体如何进行映射是interrupt controller自己的事情，不过，有软件架构思想的工程师更愿意对形形色色的interrupt controller进行抽象，对如何进行HW interrupt ID到IRQ number映射关系上进行进一步的抽象。因此，通用中断处理模块中有一个irq domain的子模块，该模块将这种映射关系分成了三类：

（1）线性映射。其实就是一个lookup table，HW interrupt ID作为index，通过查表可以获取对应的IRQ number。对于Linear map而言，interrupt controller对其HW interrupt ID进行编码的时候要满足一定的条件：hw ID不能过大，而且ID排列最好是紧密的。对于线性映射，其接口API如下：

> static inline struct irq\_domain \*irq\_domain\_add\_linear(struct device\_node \*of\_node,   
> unsigned int size,－－－－－－－－－该interrupt domain支持多少IRQ   
> const struct irq\_domain\_ops \*ops,－－－callback函数   
> void \*host\_data)－－－－－driver私有数据   
> {   
> return \_\_irq\_domain\_add(of\_node, size, size, 0, ops, host\_data);   
> }

（2）Radix Tree map。建立一个Radix Tree来维护HW interrupt ID到IRQ number映射关系。HW interrupt ID作为lookup key，在Radix Tree检索到IRQ number。如果的确不能满足线性映射的条件，可以考虑Radix Tree map。实际上，内核中使用Radix Tree map的只有powerPC和MIPS的硬件平台。对于Radix Tree map，其接口API如下：

> static inline struct irq\_domain \*irq\_domain\_add\_tree(struct device\_node \*of\_node,   
> const struct irq\_domain\_ops \*ops,   
> void \*host\_data)   
> {   
> return \_\_irq\_domain\_add(of\_node, 0, ~0, 0, ops, host\_data);   
> }

（3）no map。有些中断控制器很强，可以通过寄存器配置HW interrupt ID而不是由物理连接决定的。例如PowerPC 系统使用的MPIC (Multi-Processor Interrupt Controller)。在这种情况下，不需要进行映射，我们直接把IRQ number写入HW interrupt ID配置寄存器就OK了，这时候，生成的HW interrupt ID就是IRQ number，也就不需要进行mapping了。对于这种类型的映射，其接口API如下：

> static inline struct irq\_domain \*irq\_domain\_add\_nomap(struct device\_node \*of\_node,   
> unsigned int max\_irq,   
> const struct irq\_domain\_ops \*ops,   
> void \*host\_data)   
> {   
> return \_\_irq\_domain\_add(of\_node, 0, max\_irq, max\_irq, ops, host\_data);   
> }

这类接口的逻辑很简单，根据自己的映射类型，初始化struct irq\_domain中的各个成员，调用\_\_irq\_domain\_add将该irq domain挂入irq\_domain\_list的全局列表。

2、为irq domain创建映射

上节的内容主要是向系统注册一个irq domain，具体HW interrupt ID和IRQ number的映射关系都是空的，因此，具体各个irq domain如何管理映射所需要的database还是需要建立的。例如：对于线性映射的irq domain，我们需要建立线性映射的lookup table，对于Radix Tree map，我们要把那个反应IRQ number和HW interrupt ID的Radix tree建立起来。创建映射有四个接口函数：

（1）调用irq\_create\_mapping函数建立HW interrupt ID和IRQ number的映射关系。该接口函数以irq domain和HW interrupt ID为参数，返回IRQ number（这个IRQ number是动态分配的）。该函数的原型定义如下：

> extern unsigned int irq\_create\_mapping(struct irq\_domain \*host,   
> irq\_hw\_number\_t hwirq);

驱动调用该函数的时候必须提供HW interrupt ID，也就是意味着driver知道自己使用的HW interrupt ID，而一般情况下，HW interrupt ID其实对具体的driver应该是不可见的，不过有些场景比较特殊，例如GPIO类型的中断，它的HW interrupt ID和GPIO有着特定的关系，driver知道自己使用那个GPIO，也就是知道使用哪一个HW interrupt ID了。

（2）irq\_create\_strict\_mappings。这个接口函数用来为一组HW interrupt ID建立映射。具体函数的原型定义如下：

> extern int irq\_create\_strict\_mappings(struct irq\_domain \*domain,   
> unsigned int irq\_base,   
> irq\_hw\_number\_t hwirq\_base, int count);

（3）irq\_create\_of\_mapping。看到函数名字中的of（open firmware），我想你也可以猜到了几分，这个接口当然是利用device tree进行映射关系的建立。具体函数的原型定义如下：

> extern unsigned int irq\_create\_of\_mapping(struct of\_phandle\_args \*irq\_data);

通常，一个普通设备的device tree node已经描述了足够的中断信息，在这种情况下，该设备的驱动在初始化的时候可以调用irq\_of\_parse\_and\_map这个接口函数进行该device node中和中断相关的内容（interrupts和interrupt-parent属性）进行分析，并建立映射关系，具体代码如下：

> unsigned int irq\_of\_parse\_and\_map(struct device\_node \*dev, int index)   
> {   
> struct of\_phandle\_args oirq;
>
> if (of\_irq\_parse\_one(dev, index, &oirq))－－－－分析device node中的interrupt相关属性   
> return 0;
>
> return irq\_create\_of\_mapping(&oirq);－－－－－创建映射，并返回对应的IRQ number   
> }

对于一个使用Device tree的普通驱动程序（我们推荐这样做），基本上初始化需要调用irq\_of\_parse\_and\_map获取IRQ number，然后调用request\_threaded\_irq申请中断handler。

（4）irq\_create\_direct\_mapping。这是给no map那种类型的interrupt controller使用的，这里不再赘述。

四、数据结构描述

1、irq domain的callback接口

struct irq\_domain\_ops抽象了一个irq domain的callback函数，定义如下：

> struct irq\_domain\_ops {   
> int (\*match)(struct irq\_domain \*d, struct device\_node \*node);   
> int (\*map)(struct irq\_domain \*d, unsigned int virq, irq\_hw\_number\_t hw);   
> void (\*unmap)(struct irq\_domain \*d, unsigned int virq);   
> int (\*xlate)(struct irq\_domain \*d, struct device\_node \*node,   
> const u32 \*intspec, unsigned int intsize,   
> unsigned long \*out\_hwirq, unsigned int \*out\_type);   
> };

我们先看xlate函数，语义是翻译（translate）的意思，那么到底翻译什么呢？在DTS文件中，各个使用中断的device node会通过一些属性（例如interrupts和interrupt-parent属性）来提供中断信息给kernel以便kernel可以正确的进行driver的初始化动作。这里，interrupts属性所表示的interrupt specifier只能由具体的interrupt controller（也就是irq domain）来解析。而xlate函数就是将指定的设备（node参数）上若干个（intsize参数）中断属性（intspec参数）翻译成HW interrupt ID（out\_hwirq参数）和trigger类型（out\_type）。

match是判断一个指定的interrupt controller（node参数）是否和一个irq domain匹配（d参数），如果匹配的话，返回1。实际上，内核中很少定义这个callback函数，实际上struct irq\_domain中有一个of\_node指向了对应的interrupt controller的device node，因此，如果不提供该函数，那么default的匹配函数其实就是判断irq domain的of\_node成员是否等于传入的node参数。

map和unmap是操作相反的函数，我们描述其中之一就OK了。调用map函数的时机是在创建（或者更新）HW interrupt ID（hw参数）和IRQ number（virq参数）关系的时候。其实，从发生一个中断到调用该中断的handler仅仅调用一个request\_threaded\_irq是不够的，还需要针对该irq number设定：

（1）设定该IRQ number对应的中断描述符（struct irq\_desc）的irq chip

（2）设定该IRQ number对应的中断描述符的highlevel irq-events handler

（3）设定该IRQ number对应的中断描述符的 irq chip data

这些设定不适合由具体的硬件驱动来设定，因此在Interrupt controller，也就是irq domain的callback函数中设定。

2、irq domain

在内核中，irq domain的概念由struct irq\_domain表示：

> struct irq\_domain {   
> struct list\_head link;   
> const char \*name;   
> const struct irq\_domain\_ops \*ops; －－－－callback函数   
> void \*host\_data;
>
> /\* Optional data \*/   
> struct device\_node \*of\_node; －－－－该interrupt domain对应的interrupt controller的device node   
> struct irq\_domain\_chip\_generic \*gc; －－－generic irq chip的概念，本文暂不描述
>
> /\* reverse map data. The linear map gets appended to the irq\_domain \*/   
> irq\_hw\_number\_t hwirq\_max; －－－－该domain中最大的那个HW interrupt ID   
> unsigned int revmap\_direct\_max\_irq; －－－－   
> unsigned int revmap\_size; －－－线性映射的size，for Radix Tree map和no map，该值等于0   
> struct radix\_tree\_root revmap\_tree; －－－－Radix Tree map使用到的radix tree root node   
> unsigned int linear\_revmap[]; －－－－－线性映射使用的lookup table   
> };

linux内核中，所有的irq domain被挂入一个全局链表，链表头定义如下：

> static LIST\_HEAD(irq\_domain\_list);

struct irq\_domain中的link成员就是挂入这个队列的节点。通过irq\_domain\_list这个指针，可以获取整个系统中HW interrupt ID和IRQ number的mapping DB。host\_data定义了底层interrupt controller使用的私有数据，和具体的interrupt controller相关（对于GIC，该指针指向一个struct gic\_chip\_data数据结构）。

对于线性映射：

（1）linear\_revmap保存了一个线性的lookup table，index是HW interrupt ID，table中保存了IRQ number值

（2）revmap\_size等于线性的lookup table的size。

（3）hwirq\_max保存了最大的HW interrupt ID

（4）revmap\_direct\_max\_irq没有用，设定为0。revmap\_tree没有用。

对于Radix Tree map：

（1）linear\_revmap没有用，revmap\_size等于0。

（2）hwirq\_max没有用，设定为一个最大值。

（3）revmap\_direct\_max\_irq没有用，设定为0。

（4）revmap\_tree指向Radix tree的root node。

五、中断相关的Device Tree知识回顾

想要进行映射，首先要了解interrupt controller的拓扑结构。系统中的interrupt controller的拓扑结构以及其interrupt request line的分配情况（分配给哪一个具体的外设）都在Device Tree Source文件中通过下面的属性给出了描述。这些内容在Device Tree的三份文档中给出了一些描述，这里简单总结一下：

对于那些产生中断的外设，我们需要定义interrupt-parent和interrupts属性：

（1）interrupt-parent。表明该外设的interrupt request line物理的连接到了哪一个中断控制器上

（2）interrupts。这个属性描述了具体该外设产生的interrupt的细节信息（也就是传说中的interrupt specifier）。例如：HW interrupt ID（由该外设的device node中的interrupt-parent指向的interrupt controller解析）、interrupt触发类型等。

对于Interrupt controller，我们需要定义interrupt-controller和#interrupt-cells的属性：

（1）interrupt-controller。表明该device node就是一个中断控制器

（2）#interrupt-cells。该中断控制器用多少个cell（一个cell就是一个32-bit的单元）描述一个外设的interrupt request line。？具体每个cell表示什么样的含义由interrupt controller自己定义。

（3）interrupts和interrupt-parent。对于那些不是root 的interrupt controller，其本身也是作为一个产生中断的外设连接到其他的interrupt controller上，因此也需要定义interrupts和interrupt-parent的属性。

六、Mapping DB的建立

1、概述

系统中HW interrupt ID和IRQ number的mapping DB是在整个系统初始化的过程中建立起来的，过程如下：

（1）DTS文件描述了系统中的interrupt controller以及外设IRQ的拓扑结构，在linux kernel启动的时候，由bootloader传递给kernel（实际传递的是DTB）。

（2）在Device Tree初始化的时候，形成了系统内所有的device node的树状结构，当然其中包括所有和中断拓扑相关的数据结构（所有的interrupt controller的node和使用中断的外设node）

（3）在machine driver初始化的时候会调用of\_irq\_init函数，在该函数中会扫描所有interrupt controller的节点，并调用适合的interrupt controller driver进行初始化。毫无疑问，初始化需要注意顺序，首先初始化root，然后first level，second level，最好是leaf node。在初始化的过程中，一般会调用上节中的接口函数向系统增加irq domain。有些interrupt controller会在其driver初始化的过程中创建映射

（4）在各个driver初始化的过程中，创建映射

2、 interrupt controller初始化的过程中，注册irq domain

我们以GIC的代码为例。具体代码在gic\_of\_init->gic\_init\_bases中，如下：

> void \_\_init gic\_init\_bases(unsigned int gic\_nr, int irq\_start,   
> void \_\_iomem \*dist\_base, void \_\_iomem \*cpu\_base,   
> u32 percpu\_offset, struct device\_node \*node)   
> {   
> irq\_hw\_number\_t hwirq\_base;   
> struct gic\_chip\_data \*gic;   
> int gic\_irqs, irq\_base, i;
>
> ……   
> 对于root GIC   
> hwirq\_base = 16;   
> gic\_irqs = 系统支持的所有的中断数目－16。之所以减去16主要是因为root GIC的0～15号HW interrupt 是for IPI的，因此要去掉。也正因为如此hwirq\_base从16开始
>
> irq\_base = irq\_alloc\_descs(irq\_start, 16, gic\_irqs, numa\_node\_id());申请gic\_irqs个IRQ资源，从16号开始搜索IRQ number。由于是root GIC，申请的IRQ基本上会从16号开始
>
> gic->domain = irq\_domain\_add\_legacy(node, gic\_irqs, irq\_base,   
> hwirq\_base, &gic\_irq\_domain\_ops, gic);－－－向系统注册irq domain并创建映射
>
> ……   
> }

很遗憾，在GIC的代码中没有调用标准的注册irq domain的接口函数。要了解其背后的原因，我们需要回到过去。在旧的linux kernel中，ARM体系结构的代码不甚理想。在arch/arm目录充斥了很多board specific的代码，其中定义了很多具体设备相关的静态表格，这些表格规定了各个device使用的资源，当然，其中包括IRQ资源。在这种情况下，各个外设的IRQ是固定的（如果作为驱动程序员的你足够老的话，应该记得很长篇幅的针对IRQ number的宏定义），也就是说，HW interrupt ID和IRQ number的关系是固定的。一旦关系固定，我们就可以在interupt controller的代码中创建这些映射关系。具体代码如下：

> struct irq\_domain \*irq\_domain\_add\_legacy(struct device\_node \*of\_node,   
> unsigned int size,   
> unsigned int first\_irq,   
> irq\_hw\_number\_t first\_hwirq,   
> const struct irq\_domain\_ops \*ops,   
> void \*host\_data)   
> {   
> struct irq\_domain \*domain;
>
> domain = \_\_irq\_domain\_add(of\_node, first\_hwirq + size,－－－－注册irq domain   
> first\_hwirq + size, 0, ops, host\_data);   
> if (!domain)   
> return NULL;
>
> irq\_domain\_associate\_many(domain, first\_irq, first\_hwirq, size); －－－创建映射
>
> return domain;   
> }

这时候，对于这个版本的GIC driver而言，初始化之后，HW interrupt ID和IRQ number的映射关系已经建立，保存在线性lookup table中，size等于GIC支持的中断数目，具体如下：

index 0～15对应的IRQ无效

16号IRQ <------------------>16号HW interrupt ID

17号IRQ <------------------>17号HW interrupt ID

……

如果想充分发挥Device Tree的威力，3.14版本中的GIC 代码需要修改。

3、在各个硬件外设的驱动初始化过程中，创建HW interrupt ID和IRQ number的映射关系

我们上面的描述过程中，已经提及：设备的驱动在初始化的时候可以调用irq\_of\_parse\_and\_map这个接口函数进行该device node中和中断相关的内容（interrupts和interrupt-parent属性）进行分析，并建立映射关系，具体代码如下：

> unsigned int irq\_of\_parse\_and\_map(struct device\_node \*dev, int index)   
> {   
> struct of\_phandle\_args oirq;
>
> if (of\_irq\_parse\_one(dev, index, &oirq))－－－－分析device node中的interrupt相关属性   
> return 0;
>
> return irq\_create\_of\_mapping(&oirq);－－－－－创建映射   
> }

我们再来看看irq\_create\_of\_mapping函数如何创建映射：

> unsigned int irq\_create\_of\_mapping(struct of\_phandle\_args \*irq\_data)   
> {   
> struct irq\_domain \*domain;   
> irq\_hw\_number\_t hwirq;   
> unsigned int type = IRQ\_TYPE\_NONE;   
> unsigned int virq;
>
> domain = irq\_data->np ? irq\_find\_host(irq\_data->np) : irq\_default\_domain;－－A   
> if (!domain) {   
> return 0;   
> }
>
> if (domain->ops->xlate == NULL)－－－－－－－－－－－－－－B   
> hwirq = irq\_data->args[0];   
> else {   
> if (domain->ops->xlate(domain, irq\_data->np, irq\_data->args,－－－－C   
> irq\_data->args\_count, &hwirq, &type))   
> return 0;   
> }
>
> /\* Create mapping \*/   
> virq = irq\_create\_mapping(domain, hwirq);－－－－－－－－D   
> if (!virq)   
> return virq;
>
> /\* Set type if specified and different than the current one \*/   
> if (type != IRQ\_TYPE\_NONE &&   
> type != irq\_get\_trigger\_type(virq))   
> irq\_set\_irq\_type(virq, type);－－－－－－－－－E   
> return virq;   
> }

A：这里的代码主要是找到irq domain。这是根据传递进来的参数irq\_data的np成员来寻找的，具体定义如下：

> struct of\_phandle\_args {   
> struct device\_node \*np;－－－指向了外设对应的interrupt controller的device node   
> int args\_count;－－－－－－－该外设定义的interrupt相关属性的个数   
> uint32\_t args[MAX\_PHANDLE\_ARGS];－－－－具体的interrupt相当属性的定义   
> };

B：如果没有定义xlate函数，那么取interrupts属性的第一个cell作为HW interrupt ID。

C：解铃还需系铃人，interrupts属性最好由interrupt controller（也就是irq domain）解释。如果xlate函数能够完成属性解析，那么将输出参数hwirq和type，分别表示HW interrupt ID和interupt type（触发方式等）。

D：解析完了，最终还是要调用irq\_create\_mapping函数来创建HW interrupt ID和IRQ number的映射关系。

E：如果有需要，调用irq\_set\_irq\_type函数设定trigger type

irq\_create\_mapping函数建立HW interrupt ID和IRQ number的映射关系。该接口函数以irq domain和HW interrupt ID为参数，返回IRQ number。具体的代码如下：

> unsigned int irq\_create\_mapping(struct irq\_domain \*domain,   
> irq\_hw\_number\_t hwirq)   
> {   
> unsigned int hint;   
> int virq;
>
> 如果映射已经存在，那么不需要映射，直接返回   
> virq = irq\_find\_mapping(domain, hwirq);   
> if (virq) {   
> return virq;   
> }
>
> hint = hwirq % nr\_irqs;－－－－－－－分配一个IRQ 描述符以及对应的irq number   
> if (hint == 0)   
> hint++;   
> virq = irq\_alloc\_desc\_from(hint, of\_node\_to\_nid(domain->of\_node));   
> if (virq <= 0)   
> virq = irq\_alloc\_desc\_from(1, of\_node\_to\_nid(domain->of\_node));   
> if (virq <= 0) {   
> pr\_debug("-> virq allocation failed\n");   
> return 0;   
> }
>
> if (irq\_domain\_associate(domain, virq, hwirq)) {－－－建立mapping   
> irq\_free\_desc(virq);   
> return 0;   
> }
>
> return virq;   
> }

对于分配中断描述符这段代码，后续的文章会详细描述。这里简单略过，反正，指向完这段代码，我们就可以或者一个IRQ number以及其对应的中断描述符了。程序注释中没有使用IRQ number而是使用了virtual interrupt number这个术语。virtual interrupt number还是重点理解“virtual”这个词，所谓virtual，其实就是说和具体的硬件连接没有关系了，仅仅是一个number而已。具体建立映射的函数是irq\_domain\_associate函数，代码如下：

> int irq\_domain\_associate(struct irq\_domain \*domain, unsigned int virq,   
> irq\_hw\_number\_t hwirq)   
> {   
> struct irq\_data \*irq\_data = irq\_get\_irq\_data(virq);   
> int ret;
>
> mutex\_lock(&irq\_domain\_mutex);   
> irq\_data->hwirq = hwirq;   
> irq\_data->domain = domain;   
> if (domain->ops->map) {   
> ret = domain->ops->map(domain, virq, hwirq);－－－调用irq domain的map callback函数   
> }
>
> if (hwirq < domain->revmap\_size) {   
> domain->linear\_revmap[hwirq] = virq;－－－－填写线性映射lookup table的数据   
> } else {   
> mutex\_lock(&revmap\_trees\_mutex);   
> radix\_tree\_insert(&domain->revmap\_tree, hwirq, irq\_data);－－向radix tree插入一个node   
> mutex\_unlock(&revmap\_trees\_mutex);   
> }   
> mutex\_unlock(&irq\_domain\_mutex);
>
> irq\_clear\_status\_flags(virq, IRQ\_NOREQUEST); －－－该IRQ已经可以申请了，因此clear相关flag
>
> return 0;   
> }

七、将HW interrupt ID转成IRQ number

创建了庞大的HW interrupt ID到IRQ number的mapping DB，最终还是要使用。具体的使用场景是在CPU相关的处理函数中，程序会读取硬件interrupt ID，并转成IRQ number，调用对应的irq event handler。在本章中，我们以一个级联的GIC系统为例，描述转换过程

1、GIC driver初始化

上面已经描述了root GIC的的初始化，我们再来看看second GIC的初始化。具体代码在gic\_of\_init->gic\_init\_bases中，如下：

> void \_\_init gic\_init\_bases(unsigned int gic\_nr, int irq\_start,   
> void \_\_iomem \*dist\_base, void \_\_iomem \*cpu\_base,   
> u32 percpu\_offset, struct device\_node \*node)   
> {   
> irq\_hw\_number\_t hwirq\_base;   
> struct gic\_chip\_data \*gic;   
> int gic\_irqs, irq\_base, i;
>
> ……   
> 对于second GIC   
> hwirq\_base = 32;   
> gic\_irqs = 系统支持的所有的中断数目－32。之所以减去32主要是因为对于second GIC，其0～15号HW interrupt 是for IPI的，因此要去掉。而16～31号HW interrupt 是for PPI的，也要去掉。也正因为如此hwirq\_base从32开始
>
> irq\_base = irq\_alloc\_descs(irq\_start, 16, gic\_irqs, numa\_node\_id());申请gic\_irqs个IRQ资源，从16号开始搜索IRQ number。由于是second GIC，申请的IRQ基本上会从root GIC申请的最后一个IRQ号＋1开始
>
> gic->domain = irq\_domain\_add\_legacy(node, gic\_irqs, irq\_base,   
> hwirq\_base, &gic\_irq\_domain\_ops, gic);－－－向系统注册irq domain并创建映射
>
> ……   
> }

second GIC初始化之后，该irq domain的HW interrupt ID和IRQ number的映射关系已经建立，保存在线性lookup table中，size等于GIC支持的中断数目，具体如下：

index 0～32对应的IRQ无效

root GIC申请的最后一个IRQ号＋1 <------------------>32号HW interrupt ID

root GIC申请的最后一个IRQ号＋2 <------------------>33号HW interrupt ID

……

OK，我们回到gic的初始化函数，对于second GIC，还有其他部分的初始化内容：

> int \_\_init gic\_of\_init(struct device\_node \*node, struct device\_node \*parent)   
> {
>
> ……
>
> if (parent) {   
> irq = irq\_of\_parse\_and\_map(node, 0);－－解析second GIC的interrupts属性，并进行mapping，返回IRQ number   
> gic\_cascade\_irq(gic\_cnt, irq);－－－设置handler   
> }   
> ……   
> }

上面的初始化函数去掉和级联无关的代码。对于root GIC，其传入的parent是NULL，因此不会执行级联部分的代码。对于second GIC，它是作为其parent（root GIC）的一个普通的irq source，因此，也需要注册该IRQ的handler。由此可见，非root的GIC的初始化分成了两个部分：一部分是作为一个interrupt controller，执行和root GIC一样的初始化代码。另外一方面，GIC又作为一个普通的interrupt generating device，需要象一个普通的设备驱动一样，注册其中断handler。

irq\_of\_parse\_and\_map函数相信大家已经熟悉了，这里不再描述。gic\_cascade\_irq函数如下：

> void \_\_init gic\_cascade\_irq(unsigned int gic\_nr, unsigned int irq)   
> {   
> if (irq\_set\_handler\_data(irq, &gic\_data[gic\_nr]) != 0)－－－设置handler data   
> BUG();   
> irq\_set\_chained\_handler(irq, gic\_handle\_cascade\_irq);－－－设置handler   
> }

2、具体如何在中断处理过程中，将HW interrupt ID转成IRQ number

在系统的启动过程中，经过了各个interrupt controller以及各个外设驱动的努力，整个interrupt系统的database（将HW interrupt ID转成IRQ number的数据库，这里的数据库不是指SQL lite或者oracle这样通用数据库软件）已经建立。一旦发生硬件中断，经过CPU architecture相关的中断代码之后，会调用irq handler，该函数的一般过程如下：

（1）首先找到root interrupt controller对应的irq domain。

（2）根据HW 寄存器信息和irq domain信息获取HW interrupt ID

（3）调用irq\_find\_mapping找到HW interrupt ID对应的irq number

（4）调用handle\_IRQ（对于ARM平台）来处理该irq number

对于级联的情况，过程类似上面的描述，但是需要注意的是在步骤4中不是直接调用该IRQ的hander来处理该irq number因为，这个irq需要各个interrupt controller level上的解析。举一个简单的二阶级联情况：假设系统中有两个interrupt controller，A和B，A是root interrupt controller，B连接到A的13号HW interrupt ID上。在B interrupt controller初始化的时候，除了初始化它作为interrupt controller的那部分内容，还有初始化它作为root interrupt controller A上的一个普通外设这部分的内容。最重要的是调用irq\_set\_chained\_handler设定handler。这样，在上面的步骤4的时候，就会调用13号HW interrupt ID对应的handler（也就是B的handler），在该handler中，会重复上面的（1）～（4）。

*原创文章，转发请注明出处。蜗窝科技。[/irq_subsystem/irq-domain.html](/irq_subsystem/irq-domain.html)*
