---
title: "linux kernel的中断子系统之（七）：GIC代码分析"
date: 2014-09-04T16:59:06+08:00
url: "/irq_subsystem/gic_driver.html"
gid: "84"
emlog_type: "blog"
summary: "\r\n\t\r\n\r\n\r\n\tGIC（Generic Interrupt Controller）是ARM公司提供的一个通用的中断控制器，其architecture \r\nspecification目前有四个版本，V1～V4(V2最多支持8个ARM core，V3/V4支持更多的ARM \r\ncore，主要用于ARM64服务器系统结构）。目前在ARM官方网站只能下载到Version 2的GIC architect"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["GIC", "代码分析"]
views: 140487
comment_count: 111
aliases:
  - "/irq_subsystem/84.html"
  - "/84.html"
---

一、前言

GIC（Generic Interrupt Controller）是ARM公司提供的一个通用的中断控制器，其architecture specification目前有四个版本，V1～V4(V2最多支持8个ARM core，V3/V4支持更多的ARM core，主要用于ARM64服务器系统结构）。目前在ARM官方网站只能下载到Version 2的GIC architecture specification，因此，本文主要描述符合V2规范的GIC硬件及其驱动。

具体GIC硬件的实现形态有两种，一种是在ARM vensor研发自己的SOC的时候，会向ARM公司购买GIC的IP，这些IP包括的型号有：PL390，GIC-400，GIC-500。其中GIC-500最多支持128个 cpu core，它要求ARM core必须是ARMV8指令集的（例如Cortex-A57），符合GIC architecture specification version 3。另外一种形态是ARM vensor直接购买ARM公司的Cortex A9或者A15的IP，Cortex A9或者A15中会包括了GIC的实现，当然，这些实现也是符合GIC V2的规格。

本文在进行硬件描述的时候主要是以GIC-400为目标，当然，也会顺便提及一些Cortex A9或者A15上的GIC实现。

本文主要分析了linux kernel中GIC中断控制器的驱动代码（位于drivers/irqchip/irq-gic.c和irq-gic-common.c）。 irq-gic-common.c中是GIC V2和V3的通用代码，而irq-gic.c是V2 specific的代码，irq-gic-v3.c是V3 specific的代码，不在本文的描述范围。本文主要分成三个部分：第二章描述了GIC V2的硬件；第三章描述了GIC V2的初始化过程；第四章描述了底层的硬件call back函数。

注：具体的linux kernel的版本是linux-3.17-rc3。

二、GIC-V2的硬件描述

1、GIC-V2的输入和输出信号

（1）GIC-V2的输入和输出信号示意图

要想理解一个building block（无论软件还是硬件），我们都可以先把它当成黑盒子，只是研究其input，output。GIC-V2的输入和输出信号的示意图如下（注：我们以GIC-400为例，同时省略了clock，config等信号）：

[![gic-400](/content/uploadfile/201409/27eba98d637e10c5f8d6e0b4aebd5c4820140904115850.gif "gic-400")](/content/uploadfile/201409/645b571aed74ae33aca449e3b57420b820140904115848.gif)

（2）输入信号

上图中左边就是来自外设的interrupt source输入信号。分成两种类型，分别是PPI（Private Peripheral Interrupt）和SPI（Shared Peripheral Interrupt）。其实从名字就可以看出来两种类型中断信号的特点，PPI中断信号是CPU私有的，每个CPU都有其特定的PPI信号线。而SPI是所有CPU之间共享的。通过寄存器GICD\_TYPER可以配置SPI的个数（最多480个）。GIC-400支持多少个SPI中断，其输入信号线就有多少个SPI interrupt request signal。同样的，通过寄存器GICD\_TYPER也可以配置CPU interface的个数（最多8个），GIC-400支持多少个CPU interface，其输入信号线就提供多少组PPI中断信号线。一组PPI中断信号线包括6个实际的signal：

（a）nLEGACYIRQ信号线。对应interrupt ID 31，在bypass mode下（这里的bypass是指bypass GIC functionality，直接连接到某个processor上），nLEGACYIRQ可以直接连到对应CPU的nIRQCPU信号线上。在这样的设置下，该CPU不参与其他属于该CPU的PPI以及SPI中断的响应，而是特别为这一根中断线服务。

（b）nCNTPNSIRQ信号线。来自Non-secure physical timer的中断事件，对应interrupt ID 30。

（c）nCNTPSIRQ信号线。来自secure physical timer的中断事件，对应interrupt ID 29。

（d）nLEGACYFIQ信号线。对应interrupt ID 28。概念同nLEGACYIRQ信号线，不再描述。

（e）nCNTVIRQ信号线。对应interrupt ID 27。Virtual Timer Event，和虚拟化相关，这里不与描述。

（f）nCNTHPIRQ信号线。对应interrupt ID 26。Hypervisor Timer Event，和虚拟化相关，这里不与描述。

对于Cortex A15的GIC实现，其PPI中断信号线除了上面的6个，还有一个叫做Virtual Maintenance Interrupt，对应interrupt ID 25。

对于Cortex A9的GIC实现，其PPI中断信号线包括5根：

（a）nLEGACYIRQ信号线和nLEGACYFIQ信号线。对应interrupt ID 31和interrupt ID 28。这部分和上面一致。

（b）由于Cortext A9的每个处理器都有自己的Private timer和watch dog timer，这两个HW block分别使用了ID 29和ID 30

（c）Cortext A9内嵌一个global timer为系统内的所有processor共享，对应interrupt ID 27

关于private timer和global timer的描述，请参考时间子系统的相关文档。

关于一系列和虚拟化相关的中断，请参考虚拟化的系列文档。

（3）输出信号

所谓输出信号，其实就是GIC和各个CPU直接的接口，这些接口包括：

（a）触发CPU中断的信号。nIRQCPU和nFIQCPU信号线，熟悉ARM CPU的工程师对这两个信号线应该不陌生，主要用来触发ARM cpu进入IRQ mode和FIQ mode。

（b）Wake up信号。nFIQOUT和nIRQOUT信号线，去ARM CPU的电源管理模块，用来唤醒CPU的

（c）AXI slave interface signals。AXI（Advanced eXtensible Interface）是一种总线协议，属于AMBA规范的一部分。通过这些信号线，ARM CPU可以和GIC硬件block进行通信（例如寄存器访问）。

（4）中断号的分配

GIC-V2支持的中断类型有下面几种：

（a）外设中断（Peripheral interrupt）。有实际物理interrupt request signal的那些中断，上面已经介绍过了。

（b）软件触发的中断（SGI，Software-generated interrupt）。软件可以通过写GICD\_SGIR寄存器来触发一个中断事件，这样的中断，可以用于processor之间的通信。

（c）虚拟中断（Virtual interrupt）和Maintenance interrupt。这两种中断和本文无关，不再赘述。

为了标识这些interrupt source，我们必须要对它们进行编码，具体的ID分配情况如下：

（a）ID0~ID31是用于分发到一个特定的process的interrupt。标识这些interrupt不能仅仅依靠ID，因为各个interrupt source都用同样的ID0~ID31来标识，因此识别这些interrupt需要interrupt ID ＋ CPU interface number。ID0~ID15用于SGI，ID16~ID31用于PPI。PPI类型的中断会送到其私有的process上，和其他的process无关。SGI是通过写GICD\_SGIR寄存器而触发的中断。Distributor通过processor source ID、中断ID和target processor ID来唯一识别一个SGI。

（b）ID32~ID1019用于SPI。 这是GIC规范的最大size，实际上GIC-400最大支持480个SPI，Cortex-A15和A9上的GIC最多支持224个SPI。

2、GIC-V2的内部逻辑

（1）GIC的block diagram

GIC的block diagram如下图所示：

[![gic](/content/uploadfile/201409/049e88993db95cd9b35b6d9e8c1fa99920140904115854.gif "gic")](/content/uploadfile/201409/e1fbd5278ddff2a62b06d22df15848e920140904115852.gif)

GIC可以清晰的划分成两个block，一个block是Distributor（上图的左边的block），一个是CPU interface。CPU interface有两种，一种就是和普通processor接口，另外一种是和虚拟机接口的。Virtual CPU interface在本文中不会详细描述。

（2）Distributor 概述

Distributor的主要的作用是检测各个interrupt source的状态，控制各个interrupt source的行为，分发各个interrupt source产生的中断事件分发到指定的一个或者多个CPU interface上。虽然Distributor可以管理多个interrupt source，但是它总是把优先级最高的那个interrupt请求送往CPU interface。Distributor对中断的控制包括：

（1）中断enable或者disable的控制。Distributor对中断的控制分成两个级别。一个是全局中断的控制（GIC\_DIST\_CTRL）。一旦disable了全局的中断，那么任何的interrupt source产生的interrupt event都不会被传递到CPU interface。另外一个级别是对针对各个interrupt source进行控制（GIC\_DIST\_ENABLE\_CLEAR），disable某一个interrupt source会导致该interrupt event不会分发到CPU interface，但不影响其他interrupt source产生interrupt event的分发。

（2）控制将当前优先级最高的中断事件分发到一个或者一组CPU interface。当一个中断事件分发到多个CPU interface的时候，GIC的内部逻辑应该保证只assert 一个CPU。

（3）优先级控制。

（4）interrupt属性设定。例如是level-sensitive还是edge-triggered

（5）interrupt group的设定

Distributor可以管理若干个interrupt source，这些interrupt source用ID来标识，我们称之interrupt ID。

（3）CPU interface

CPU interface这个block主要用于和process进行接口。该block的主要功能包括：

（a）enable或者disable CPU interface向连接的CPU assert中断事件。对于ARM，CPU interface block和CPU之间的中断信号线是nIRQCPU和nFIQCPU。如果disable了中断，那么即便是Distributor分发了一个中断事件到CPU interface，但是也不会assert指定的nIRQ或者nFIQ通知processor。

（b）ackowledging中断。processor会向CPU interface block应答中断（应答当前优先级最高的那个中断），中断一旦被应答，Distributor就会把该中断的状态从pending状态修改成active或者pending and active（这是和该interrupt source的信号有关，例如如果是电平中断并且保持了该asserted电平，那么就是pending and active）。processor ack了中断之后，CPU interface就会deassert nIRQCPU和nFIQCPU信号线。

（c）中断处理完毕的通知。当interrupt handler处理完了一个中断的时候，会向写CPU interface的寄存器从而通知GIC CPU已经处理完该中断。做这个动作一方面是通知Distributor将中断状态修改为deactive，另外一方面，CPU interface会priority drop，从而允许其他的pending的interrupt向CPU提交。

（d）设定priority mask。通过priority mask，可以mask掉一些优先级比较低的中断，这些中断不会通知到CPU。

（e）设定preemption的策略

（f）在多个中断事件同时到来的时候，选择一个优先级最高的通知processor

（4）实例

我们用一个实际的例子来描述GIC和CPU接口上的交互过程，具体过程如下：

[![xxx](/content/uploadfile/201409/61d3821d475611cca3ba2fd66232a80820140904115900.gif "xxx")](/content/uploadfile/201409/f37480c353855439540d8fd7f514eb3320140904115856.gif)

（注：图片太长，因此竖着放，看的时候有点费劲，就当活动一下脖子吧）

首先给出前提条件：

（a）N和M用来标识两个外设中断，N的优先级大于M

（b）两个中断都是SPI类型，level trigger，active-high

（c）两个中断被配置为去同一个CPU

（d）都被配置成group 0，通过FIQ触发中断

下面的表格按照时间轴来描述交互过程：

|  |  |
| --- | --- |
| 时间 | 交互动作的描述 |
| T0时刻 | Distributor检测到M这个interrupt source的有效触发电平 |
| T2时刻 | Distributor将M这个interrupt source的状态设定为pending |
| T17时刻 | 大约15个clock之后，CPU interface拉低nFIQCPU信号线，向CPU报告M外设的中断请求。这时候，CPU interface的ack寄存器（GICC\_IAR）的内容会修改成M interrupt source对应的ID |
| T42时刻 | Distributor检测到N这个优先级更高的interrupt source的触发事件 |
| T43时刻 | Distributor将N这个interrupt source的状态设定为pending。同时，由于N的优先级更高，因此Distributor会标记当前优先级最高的中断 |
| T58时刻 | 大约15个clock之后，CPU interface拉低nFIQCPU信号线，向CPU报告N外设的中断请求。当然，由于T17时刻已经assert CPU了，因此实际的电平信号仍然保持asserted。这时候，CPU interface的ack寄存器（GICC\_IAR）的内容会被更新成N interrupt source的ID |
| T61时刻 | 软件通过读取ack寄存器的内容，获取了当前优先级最高的，并且状态是pending的interrupt ID（也就是N interrupt source对应的ID），通过读该寄存器，CPU也就ack了该interrupt source N。这时候，Distributor将N这个interrupt source的状态设定为pending and active（因为是电平触发，只要外部仍然有asserted的电平信号，那么一定就是pending的，而该中断是正在被CPU处理的中断，因此状态是pending and active）    注意：T61标识CPU开始服务该中断 |
| T64时刻 | 3个clock之后，由于CPU已经ack了中断，因此GIC中CPU interface模块 deassert nFIQCPU信号线，解除发向该CPU的中断请求 |
| T126时刻 | 由于中断服务程序操作了N外设的控制寄存器（ack外设的中断），因此N外设deassert了其interrupt request signal |
| T128时刻 | Distributor解除N外设的pending状态，因此N这个interrupt source的状态设定为active |
| T131时刻 | 软件操作End of Interrupt寄存器（向GICC\_EOIR寄存器写入N对应的interrupt ID），标识中断处理结束。Distributor将N这个interrupt source的状态修改为idle    注意：T61～T131是CPU服务N外设中断的的时间区域，这个期间，如果有高优先级的中断pending，会发生中断的抢占（硬件意义的），这时候CPU interface会向CPU assert 新的中断。 |
| T146时刻 | 大约15个clock之后，Distributor向CPU interface报告当前pending且优先级最高的interrupt source，也就是M了。漫长的pending之后，M终于迎来了春天。CPU interface拉低nFIQCPU信号线，向CPU报告M外设的中断请求。这时候，CPU interface的ack寄存器（GICC\_IAR）的内容会修改成M interrupt source对应的ID |
| T211时刻 | CPU ack M中断（通过读GICC\_IAR寄存器），开始处理低优先级的中断。 |

三、GIC-V2 irq chip driver的初始化过程

在linux-3.17-rc3\drivers\irqchip目录下保存在各种不同的中断控制器的驱动代码，这个版本的内核支持了GICV3。irq-gic-common.c是通用的GIC的驱动代码，可以被各个版本的GIC使用。irq-gic.c是用于V2版本的GIC controller，而irq-gic-v3.c是用于V3版本的GIC controller。

1、GIC的device node和GIC irq chip driver的匹配过程

（1）irq chip driver中的声明

在linux-3.17-rc3\drivers\irqchip目录下的irqchip.h文件中定义了IRQCHIP\_DECLARE宏如下：

> #define IRQCHIP\_DECLARE(name, compat, fn) OF\_DECLARE\_2(irqchip, name, compat, fn)
>
> #define OF\_DECLARE\_2(table, name, compat, fn) \   
> \_OF\_DECLARE(table, name, compat, fn, of\_init\_fn\_2)
>
> #define \_OF\_DECLARE(table, name, compat, fn, fn\_type) \   
> static const struct of\_device\_id \_\_of\_table\_##name \   
> \_\_used \_\_section(\_\_##table##\_of\_table) \   
> = { .compatible = compat, \   
> .data = (fn == (fn\_type)NULL) ? fn : fn }

这个宏其实就是初始化了一个struct of\_device\_id的静态常量，并放置在\_\_irqchip\_of\_table section中。irq-gic.c文件中使用IRQCHIP\_DECLARE来定义了若干个静态的struct of\_device\_id常量，如下：

> IRQCHIP\_DECLARE(gic\_400, "arm,gic-400", gic\_of\_init);   
> IRQCHIP\_DECLARE(cortex\_a15\_gic, "arm,cortex-a15-gic", gic\_of\_init);   
> IRQCHIP\_DECLARE(cortex\_a9\_gic, "arm,cortex-a9-gic", gic\_of\_init);   
> IRQCHIP\_DECLARE(cortex\_a7\_gic, "arm,cortex-a7-gic", gic\_of\_init);   
> IRQCHIP\_DECLARE(msm\_8660\_qgic, "qcom,msm-8660-qgic", gic\_of\_init);   
> IRQCHIP\_DECLARE(msm\_qgic2, "qcom,msm-qgic2", gic\_of\_init);

兼容GIC-V2的GIC实现有很多，不过其初始化函数都是一个。在linux kernel编译的时候，你可以配置多个irq chip进入内核，编译系统会把所有的IRQCHIP\_DECLARE宏定义的数据放入到一个特殊的section中（section name是\_\_irqchip\_of\_table），我们称这个特殊的section叫做irq chip table。这个table也就保存了kernel支持的所有的中断控制器的ID信息（最重要的是驱动代码初始化函数和DT compatible string）。我们来看看struct of\_device\_id的定义：

> struct of\_device\_id   
> {   
> char name[32];－－－－－－要匹配的device node的名字   
> char type[32];－－－－－－－要匹配的device node的类型   
> char compatible[128];－－－匹配字符串（DT compatible string），用来匹配适合的device node   
> const void \*data;－－－－－－－－对于GIC，这里是初始化函数指针   
> };

这个数据结构主要被用来进行Device node和driver模块进行匹配用的。从该数据结构的定义可以看出，在匹配过程中，device name、device type和DT compatible string都是考虑的因素。更细节的内容请参考\_\_of\_device\_is\_compatible函数。

（2）device node

不同的GIC-V2的实现总会有一些不同，这些信息可以通过Device tree的机制来传递。Device node中定义了各种属性，其中就包括了memory资源，IRQ描述等信息，这些信息需要在初始化的时候传递给具体的驱动，因此需要一个Device node和driver模块的匹配过程。在Device Tree模块中会包括系统中所有的device node，如果我们的系统使用了GIC-400，那么系统的device node数据库中会有一个node是GIC-400的，一个示例性的GIC-400的device node（我们以瑞芯微的RK3288处理器为例）定义如下：

> gic: interrupt-controller@ffc01000 {   
> compatible = "arm,gic-400";   
> interrupt-controller;   
> #interrupt-cells = <3>;   
> #address-cells = <0>;
>
> reg = <0xffc01000 0x1000="">,－－－－Distributor address range   
> <0xffc02000 0x1000="">,－－－－－CPU interface address range   
> <0xffc04000 0x2000="">,－－－－－Virtual interface control block   
> <0xffc06000 0x2000="">;－－－－－Virtual CPU interfaces   
> interrupts = ;   
> };

（3）device node和irq chip driver的匹配

在machine driver初始化的时候会调用irqchip\_init函数进行irq chip driver的初始化。在driver/irqchip/irqchip.c文件中定义了irqchip\_init函数，如下：

> void \_\_init irqchip\_init(void)   
> {   
> of\_irq\_init(\_\_irqchip\_begin);   
> }

\_\_irqchip\_begin就是内核irq chip table的首地址，这个table也就保存了kernel支持的所有的中断控制器的ID信息（用于和device node的匹配）。of\_irq\_init函数执行之前，系统已经完成了device tree的初始化，因此系统中的所有的设备节点都已经形成了一个树状结构，每个节点代表一个设备的device node。of\_irq\_init是在所有的device node中寻找中断控制器节点，形成树状结构（系统可以有多个interrupt controller，之所以形成中断控制器的树状结构，是为了让系统中所有的中断控制器驱动按照一定的顺序进行初始化）。之后，从root interrupt controller节点开始，对于每一个interrupt controller的device node，扫描irq chip table，进行匹配，一旦匹配到，就调用该interrupt controller的初始化函数，并把该中断控制器的device node以及parent中断控制器的device node作为参数传递给irq chip driver。。具体的匹配过程的代码属于Device Tree模块的内容，更详细的信息可以参考[Device Tree代码分析文档](/device_model/dt-code-analysis.html)。

2、GIC driver初始化代码分析

（1）gic\_of\_init的代码如下：

> int \_\_init gic\_of\_init(struct device\_node \*node, struct device\_node \*parent)   
> {   
> void \_\_iomem \*cpu\_base;   
> void \_\_iomem \*dist\_base;   
> u32 percpu\_offset;   
> int irq;
>
> dist\_base = of\_iomap(node, 0);----------------映射GIC Distributor的寄存器地址空间
>
> cpu\_base = of\_iomap(node, 1);----------------映射GIC CPU interface的寄存器地址空间
>
> if (of\_property\_read\_u32(node, "cpu-offset", &percpu\_offset))--------处理cpu-offset属性。   
> percpu\_offset = 0;
>
> gic\_init\_bases(gic\_cnt, -1, dist\_base, cpu\_base, percpu\_offset, node);))-----主处理过程，后面详述   
> if (!gic\_cnt)   
> gic\_init\_physaddr(node); -----对于不支持big.LITTLE switcher（CONFIG\_BL\_SWITCHER）的系统，该函数为空。
>
> if (parent) {--------处理interrupt级联   
> irq = irq\_of\_parse\_and\_map(node, 0); －－－解析second GIC的interrupts属性，并进行mapping，返回IRQ number   
> gic\_cascade\_irq(gic\_cnt, irq);   
> }   
> gic\_cnt++;   
> return 0;   
> }

我们首先看看这个函数的参数，node参数代表需要初始化的那个interrupt controller的device node，parent参数指向其parent。在映射GIC-400的memory map I/O space的时候，我们只是映射了Distributor和CPU interface的寄存器地址空间，和虚拟化处理相关的寄存器没有映射，因此这个版本的GIC driver应该是不支持虚拟化的（不知道后续版本是否支持，在一个嵌入式平台上支持虚拟化有实际意义吗？最先支持虚拟化的应该是ARM64+GICV3/4这样的平台）。

要了解cpu-offset属性，首先要了解什么是banked register。所谓banked register就是在一个地址上提供多个寄存器副本。比如说系统中有四个CPU，这些CPU访问某个寄存器的时候地址是一样的，但是对于banked register，实际上，不同的CPU访问的是不同的寄存器，虽然它们的地址是一样的。如果GIC没有banked register，那么需要提供根据CPU index给出一系列地址偏移，而地址偏移=cpu-offset \* cpu-nr。

interrupt controller可以级联。对于root GIC，其传入的parent是NULL，因此不会执行级联部分的代码。对于second GIC，它是作为其parent（root GIC）的一个普通的irq source，因此，也需要注册该IRQ的handler。由此可见，非root的GIC的初始化分成了两个部分：一部分是作为一个interrupt controller，执行和root GIC一样的初始化代码。另外一方面，GIC又作为一个普通的interrupt generating device，需要象一个普通的设备驱动一样，注册其中断handler。理解irq\_of\_parse\_and\_map需要irq domain的知识，请参考[linux kernel的中断子系统之（二）：irq domain介绍](/irq_subsystem/irq-domain.html)。

（2）gic\_init\_bases的代码如下：

> void \_\_init gic\_init\_bases(unsigned int gic\_nr, int irq\_start,   
> void \_\_iomem \*dist\_base, void \_\_iomem \*cpu\_base,   
> u32 percpu\_offset, struct device\_node \*node)   
> {   
> irq\_hw\_number\_t hwirq\_base;   
> struct gic\_chip\_data \*gic;   
> int gic\_irqs, irq\_base, i;
>
> gic = &gic\_data[gic\_nr];   
> gic->dist\_base.common\_base = dist\_base; －－－－省略了non banked的情况   
> gic->cpu\_base.common\_base = cpu\_base;   
> gic\_set\_base\_accessor(gic, gic\_get\_common\_base);
>
> for (i = 0; i < NR\_GIC\_CPU\_IF; i++) －－－后面会具体描述gic\_cpu\_map的含义   
> gic\_cpu\_map[i] = 0xff;
>
> if (gic\_nr == 0 && (irq\_start & 31) > 0) { －－－－－－－－－－－－－－－－－－－－（a）   
> hwirq\_base = 16;   
> if (irq\_start != -1)   
> irq\_start = (irq\_start & ~31) + 16;   
> } else {   
> hwirq\_base = 32;   
> }
>
> gic\_irqs = readl\_relaxed(gic\_data\_dist\_base(gic) + GIC\_DIST\_CTR) & 0x1f; －－－－（b）   
> gic\_irqs = (gic\_irqs + 1) \* 32;   
> if (gic\_irqs > 1020)   
> gic\_irqs = 1020;   
> gic->gic\_irqs = gic\_irqs;
>
> gic\_irqs -= hwirq\_base;－－－－－－－－－－－－－－－－－－－－－－－－－－－－（c）
>
> if (of\_property\_read\_u32(node, "arm,routable-irqs",－－－－－－－－－－－－－－－－（d）   
> &nr\_routable\_irqs)) {   
> irq\_base = irq\_alloc\_descs(irq\_start, 16, gic\_irqs, numa\_node\_id()); －－－－－－－（e）   
> if (IS\_ERR\_VALUE(irq\_base)) {   
> WARN(1, "Cannot allocate irq\_descs @ IRQ%d, assuming pre-allocated\n",   
> irq\_start);   
> irq\_base = irq\_start;   
> }
>
> gic->domain = irq\_domain\_add\_legacy(node, gic\_irqs, irq\_base, －－－－－－－（f）   
> hwirq\_base, &gic\_irq\_domain\_ops, gic);   
> } else {   
> gic->domain = irq\_domain\_add\_linear(node, nr\_routable\_irqs, －－－－－－－－（f）   
> &gic\_irq\_domain\_ops,   
> gic);   
> }
>
> if (gic\_nr == 0) { －－－只对root GIC操作，因为设定callback、注册Notifier只需要一次就OK了   
> #ifdef CONFIG\_SMP   
> set\_smp\_cross\_call(gic\_raise\_softirq);－－－－－－－－－－－－－－－－－－（g）   
> register\_cpu\_notifier(&gic\_cpu\_notifier);－－－－－－－－－－－－－－－－－－（h）   
> #endif   
> set\_handle\_irq(gic\_handle\_irq); －－－这个函数名字也不好，实际上是设定arch相关的irq handler   
> }
>
> gic\_chip.flags |= gic\_arch\_extn.flags;   
> gic\_dist\_init(gic);---------具体的硬件初始代码，参考下节的描述   
> gic\_cpu\_init(gic);   
> gic\_pm\_init(gic);   
> }

（a）gic\_nr标识GIC number，等于0就是root GIC。hwirq的意思就是GIC上的HW interrupt ID，并不是GIC上的每个interrupt ID都有map到linux IRQ framework中的一个IRQ number，对于SGI，是属于软件中断，用于CPU之间通信，没有必要进行HW interrupt ID到IRQ number的mapping。变量hwirq\_base表示该GIC上要进行map的base ID，hwirq\_base = 16也就意味着忽略掉16个SGI。对于系统中其他的GIC，其PPI也没有必要mapping，因此hwirq\_base = 32。

在本场景中，irq\_start ＝ -1，表示不指定IRQ number。有些场景会指定IRQ number，这时候，需要对IRQ number进行一个对齐的操作。

（b）变量gic\_irqs保存了该GIC支持的最大的中断数目。该信息是从GIC\_DIST\_CTR寄存器（这是V1版本的寄存器名字，V2中是GICD\_TYPER，Interrupt Controller Type Register,）的低五位ITLinesNumber获取的。如果ITLinesNumber等于N，那么最大支持的中断数目是32(N+1)。此外，GIC规范规定最大的中断数目不能超过1020，1020-1023是有特别用户的interrupt ID。

（c）减去不需要map（不需要分配IRQ）的那些interrupt ID，OK，这时候gic\_irqs的数值终于和它的名字一致了。gic\_irqs从字面上看不就是该GIC需要分配的IRQ number的数目吗？

（d）of\_property\_read\_u32函数把arm,routable-irqs的属性值读出到nr\_routable\_irqs变量中，如果正确返回0。在有些SOC的设计中，外设的中断请求信号线不是直接接到GIC，而是通过crossbar/multiplexer这个的HW block连接到GIC上。arm,routable-irqs这个属性用来定义那些不直接连接到GIC的中断请求数目。

（e）对于那些直接连接到GIC的情况，我们需要通过调用irq\_alloc\_descs分配中断描述符。如果irq\_start大于0，那么说明是指定IRQ number的分配，对于我们这个场景，irq\_start等于-1，因此不指定IRQ 号。如果不指定IRQ number的，就需要搜索，第二个参数16就是起始搜索的IRQ number。gic\_irqs指明要分配的irq number的数目。如果没有正确的分配到中断描述符，程序会认为可能是之前已经准备好了。

（f）这段代码主要是向系统中注册一个irq domain的数据结构。为何需要struct irq\_domain这样一个数据结构呢？从linux kernel的角度来看，任何外部的设备的中断都是一个异步事件，kernel都需要识别这个事件。在内核中，用IRQ number来标识某一个设备的某个interrupt request。有了IRQ number就可以定位到该中断的描述符（struct irq\_desc）。但是，对于中断控制器而言，它不并知道IRQ number，它只是知道HW interrupt number（中断控制器会为其支持的interrupt source进行编码，这个编码被称为Hardware interrupt number ）。不同的软件模块用不同的ID来识别interrupt source，这样就需要映射了。如何将Hardware interrupt number 映射到IRQ number呢？这需要一个translation object，内核定义为struct irq\_domain。

每个interrupt controller都会形成一个irq domain，负责解析其下游的interrut source。如果interrupt controller有级联的情况，那么一个非root interrupt controller的中断控制器也是其parent irq domain的一个普通的interrupt source。struct irq\_domain定义如下：

> struct irq\_domain {   
> ……   
> const struct irq\_domain\_ops \*ops;   
> void \*host\_data;
>
> ……   
> };

这个数据结构是属于linux kernel通用中断子系统的一部分，我们这里只是描述相关的数据成员。host\_data成员是底层interrupt controller的私有数据，linux kernel通用中断子系统不应该修改它。对于GIC而言，host\_data成员指向一个struct gic\_chip\_data的数据结构，定义如下：

> struct gic\_chip\_data {   
> union gic\_base dist\_base;－－－－－－－－－－－－－－－－－－GIC Distributor的基地址空间   
> union gic\_base cpu\_base;－－－－－－－－－－－－－－－－－－GIC CPU interface的基地址空间   
> #ifdef CONFIG\_CPU\_PM－－－－－－－－－－－－－－－－－－－－GIC 电源管理相关的成员   
> u32 saved\_spi\_enable[DIV\_ROUND\_UP(1020, 32)];   
> u32 saved\_spi\_conf[DIV\_ROUND\_UP(1020, 16)];   
> u32 saved\_spi\_target[DIV\_ROUND\_UP(1020, 4)];   
> u32 \_\_percpu \*saved\_ppi\_enable;   
> u32 \_\_percpu \*saved\_ppi\_conf;   
> #endif   
> struct irq\_domain \*domain;－－－－－－－－－－－－－－－－－该GIC对应的irq domain数据结构   
> unsigned int gic\_irqs;－－－－－－－－－－－－－－－－－－－GIC支持的IRQ的数目   
> #ifdef CONFIG\_GIC\_NON\_BANKED   
> void \_\_iomem \*(\*get\_base)(union gic\_base \*);   
> #endif   
> };

对于GIC支持的IRQ的数目，这里还要赘述几句。实际上并非GIC支持多少个HW interrupt ID，其就支持多少个IRQ。对于SGI，其处理比较特别，并不归入IRQ number中。因此，对于GIC而言，其SGI（从0到15的那些HW interrupt ID）不需要irq domain进行映射处理，也就是说SGI没有对应的IRQ number。如果系统越来越复杂，一个GIC不能支持所有的interrupt source（目前GIC支持1020个中断源，这个数目已经非常的大了），那么系统还需要引入secondary GIC，这个GIC主要负责扩展外设相关的interrupt source，也就是说，secondary GIC的SGI和PPI都变得冗余了（这些功能，primary GIC已经提供了）。这些信息可以协助理解代码中的hwirq\_base的设定。

在注册GIC的irq domain的时候还有一个重要的数据结构gic\_irq\_domain\_ops，其类型是struct irq\_domain\_ops ，对于GIC，其irq domain的操作函数是gic\_irq\_domain\_ops，定义如下：

> static const struct irq\_domain\_ops gic\_irq\_domain\_ops = {   
> .map = gic\_irq\_domain\_map,   
> .unmap = gic\_irq\_domain\_unmap,   
> .xlate = gic\_irq\_domain\_xlate,   
> };

irq domain的概念是一个通用中断子系统的概念，在具体的irq chip driver这个层次，我们需要一些解析GIC binding，创建IRQ number和HW interrupt ID的mapping的callback函数，更具体的解析参考后文的描述。

漫长的准备过程结束后，具体的注册比较简单，调用irq\_domain\_add\_legacy或者irq\_domain\_add\_linear进行注册就OK了。关于这两个接口请参考[linux kernel的中断子系统之（二）：irq domain介绍](/irq_subsystem/irq-domain.html)。

（g） 一个函数名字是否起的好足可以看出工程师的功力。set\_smp\_cross\_call这个函数看名字也知道它的含义，就是设定一个多个CPU直接通信的callback函数。当一个CPU core上的软件控制行为需要传递到其他的CPU上的时候（例如在某一个CPU上运行的进程调用了系统调用进行reboot），就会调用这个callback函数。对于GIC，这个callback定义为gic\_raise\_softirq。这个函数名字起的不好，直观上以为是和softirq相关，实际上其实是触发了IPI中断。

（h）在multi processor环境下，当processor状态发送变化的时候（例如online，offline），需要把这些事件通知到GIC。而GIC driver在收到来自CPU的事件后会对cpu interface进行相应的设定。

3、GIC硬件初始化

（1）Distributor初始化，代码如下：

> static void \_\_init gic\_dist\_init(struct gic\_chip\_data \*gic)   
> {   
> unsigned int i;   
> u32 cpumask;   
> unsigned int gic\_irqs = gic->gic\_irqs;－－－－－－－－－获取该GIC支持的IRQ的数目   
> void \_\_iomem \*base = gic\_data\_dist\_base(gic); －－－－获取该GIC对应的Distributor基地址
>
> writel\_relaxed(0, base + GIC\_DIST\_CTRL); －－－－－－－－－－－（a）
>
> cpumask = gic\_get\_cpumask(gic);－－－－－－－－－－－－－－－（b）   
> cpumask |= cpumask << 8;   
> cpumask |= cpumask << 16;－－－－－－－－－－－－－－－－－－（c）   
> for (i = 32; i < gic\_irqs; i += 4)   
> writel\_relaxed(cpumask, base + GIC\_DIST\_TARGET + i \* 4 / 4); －－（d）
>
> gic\_dist\_config(base, gic\_irqs, NULL); －－－－－－－－－－－－－－－（e）
>
> writel\_relaxed(1, base + GIC\_DIST\_CTRL);－－－－－－－－－－－－－（f）   
> }

（a）Distributor Control Register用来控制全局的中断forward情况。写入0表示Distributor不向CPU interface发送中断请求信号，也就disable了全部的中断请求（group 0和group 1），CPU interace再也收不到中断请求信号了。在初始化的最后，step（f）那里会进行enable的动作（这里只是enable了group 0的中断）。在初始化代码中，并没有设定interrupt source的group（寄存器是GIC\_DIST\_IGROUP），我相信缺省值就是设定为group 0的。

（b）我们先看看gic\_get\_cpumask的代码：

> static u8 gic\_get\_cpumask(struct gic\_chip\_data \*gic)   
> {   
> void \_\_iomem \*base = gic\_data\_dist\_base(gic);   
> u32 mask, i;
>
> for (i = mask = 0; i < 32; i += 4) {   
> mask = readl\_relaxed(base + GIC\_DIST\_TARGET + i);   
> mask |= mask >> 16;   
> mask |= mask >> 8;   
> if (mask)   
> break;   
> }
>
> return mask;   
> }

这里操作的寄存器是Interrupt Processor Targets Registers，该寄存器组中，每个GIC上的interrupt ID都有8个bit来控制送达的target CPU。我们来看看下面的图片：

[![cpu mask](/content/uploadfile/201409/b82a9c1eec7bfc66eed6ed4086d9d80420140904115902.gif "cpu mask")](/content/uploadfile/201409/eb40e557055dc9efc3633f73ff0ad3b520140904115901.gif)

GIC\_DIST\_TARGETn（Interrupt Processor Targets Registers）位于Distributor HW block中，能控制送达的CPU interface，并不是具体的CPU，如果具体的实现中CPU interface和CPU是严格按照上图中那样一一对应，那么GIC\_DIST\_TARGET送达了CPU Interface n，也就是送达了CPU n。当然现实未必如你所愿，那么怎样来获取这个CPU的mask呢？我们知道SGI和PPI不需要使用GIC\_DIST\_TARGET控制target CPU。SGI送达目标CPU有自己特有的寄存器来控制（Software Generated Interrupt Register），对于PPI，其是CPU私有的，因此不需要控制target CPU。GIC\_DIST\_TARGET0～GIC\_DIST\_TARGET7是控制0～31这32个interrupt ID（SGI和PPI）的target CPU的，但是实际上SGI和PPI是不需要控制target CPU的，因此，这些寄存器是read only的，读取这些寄存器返回的就是cpu mask值。假设CPU0接在CPU interface 4上，那么运行在CPU 0上的程序在读GIC\_DIST\_TARGET0～GIC\_DIST\_TARGET7的时候，返回的就是0b00010000。

当然，由于GIC-400只支持8个CPU，因此CPU mask值只需要8bit，但是寄存器GIC\_DIST\_TARGETn返回32个bit的值，怎么对应？很简单，cpu mask重复四次就OK了。了解了这些知识，回头看代码就很简单了。

（c）step （b）中获取了8个bit的cpu mask值，通过简单的copy，扩充为32个bit，每8个bit都是cpu mask的值，这么做是为了下一步设定所有IRQ（对于GIC而言就是SPI类型的中断）的CPU mask。

（d）设定每个SPI类型的中断都是只送达该CPU。

（e）配置GIC distributor的其他寄存器，代码如下：

> void \_\_init gic\_dist\_config(void \_\_iomem \*base, int gic\_irqs, void (\*sync\_access)(void))   
> {   
> unsigned int i;
>
> /\* Set all global interrupts to be level triggered, active low. \*/   
> for (i = 32; i < gic\_irqs; i += 16)   
> writel\_relaxed(0, base + GIC\_DIST\_CONFIG + i / 4);
>
> /\* Set priority on all global interrupts. \*/   
> for (i = 32; i < gic\_irqs; i += 4)   
> writel\_relaxed(0xa0a0a0a0, base + GIC\_DIST\_PRI + i);
>
> /\* Disable all interrupts. Leave the PPI and SGIs alone as they are enabled by redistributor registers. \*/   
> for (i = 32; i < gic\_irqs; i += 32)   
> writel\_relaxed(0xffffffff, base + GIC\_DIST\_ENABLE\_CLEAR + i / 8);
>
> if (sync\_access)   
> sync\_access();   
> }

程序的注释已经非常清楚了，这里就不细述了。需要注意的是：这里设定的都是缺省值，实际上，在各种driver的初始化过程中，还是有可能改动这些设置的（例如触发方式）。

（2）CPU interface初始化，代码如下：

> static void gic\_cpu\_init(struct gic\_chip\_data \*gic)   
> {   
> void \_\_iomem \*dist\_base = gic\_data\_dist\_base(gic);－－－－－－－Distributor的基地址空间   
> void \_\_iomem \*base = gic\_data\_cpu\_base(gic);－－－－－－－CPU interface的基地址空间   
> unsigned int cpu\_mask, cpu = smp\_processor\_id();－－－－－－获取CPU的逻辑ID   
> int i;
>
> cpu\_mask = gic\_get\_cpumask(gic);－－－－－－－－－－－－－（a）   
> gic\_cpu\_map[cpu] = cpu\_mask;
>
> for (i = 0; i < NR\_GIC\_CPU\_IF; i++)   
> if (i != cpu)   
> gic\_cpu\_map[i] &= ~cpu\_mask; －－－－－－－－－－－－（b）
>
> gic\_cpu\_config(dist\_base, NULL); －－－－－－－－－－－－－－（c）
>
> writel\_relaxed(0xf0, base + GIC\_CPU\_PRIMASK);－－－－－－－（d）   
> writel\_relaxed(1, base + GIC\_CPU\_CTRL);－－－－－－－－－－－（e）   
> }

（a）系统软件实际上是使用CPU 逻辑ID这个概念的，通过smp\_processor\_id可以获得本CPU的逻辑ID。gic\_cpu\_map这个全部lookup table就是用CPU 逻辑ID作为所以，去寻找其cpu mask，后续通过cpu mask值来控制中断是否送达该CPU。在gic\_init\_bases函数中，我们将该lookup table中的值都初始化为0xff，也就是说不进行mask，送达所有的CPU。这里，我们会进行重新修正。

（b）清除lookup table中其他entry中本cpu mask的那个bit。

（c）设定SGI和PPI的初始值。具体代码如下：

> void gic\_cpu\_config(void \_\_iomem \*base, void (\*sync\_access)(void))   
> {   
> int i;
>
> /\* Deal with the banked PPI and SGI interrupts - disable all   
> \* PPI interrupts, ensure all SGI interrupts are enabled. \*/   
> writel\_relaxed(0xffff0000, base + GIC\_DIST\_ENABLE\_CLEAR);   
> writel\_relaxed(0x0000ffff, base + GIC\_DIST\_ENABLE\_SET);
>
> /\* Set priority on PPI and SGI interrupts \*/   
> for (i = 0; i < 32; i += 4)   
> writel\_relaxed(0xa0a0a0a0, base + GIC\_DIST\_PRI + i \* 4 / 4);
>
> if (sync\_access)   
> sync\_access();   
> }

程序的注释已经非常清楚了，这里就不细述了。

（d）通过Distributor中的寄存器可以控制送达CPU interface，中断来到了GIC的CPU interface是否可以真正送达CPU呢？也不一定，还有一道关卡，也就是CPU interface中的Interrupt Priority Mask Register。这个寄存器设定了一个中断优先级的值，只有中断优先级高过该值的中断请求才会被送到CPU上去。我们在前面初始化的时候，给每个interrupt ID设定的缺省优先级是0xa0，这里设定的priority filter的优先级值是0xf0。数值越小，优先级越过。因此，这样的设定就是让所有的interrupt source都可以送达CPU，在CPU interface这里不做控制了。

（e）设定CPU interface的control register。enable了group 0的中断，disable了group 1的中断，group 0的interrupt source触发IRQ中断（而不是FIQ中断）。

（3）GIC电源管理初始化，代码如下：

> static void \_\_init gic\_pm\_init(struct gic\_chip\_data \*gic)   
> {   
> gic->saved\_ppi\_enable = \_\_alloc\_percpu(DIV\_ROUND\_UP(32, 32) \* 4, sizeof(u32));
>
> gic->saved\_ppi\_conf = \_\_alloc\_percpu(DIV\_ROUND\_UP(32, 16) \* 4, sizeof(u32));
>
> if (gic == &gic\_data[0])   
> cpu\_pm\_register\_notifier(&gic\_notifier\_block);   
> }

这段代码前面主要是分配两个per cpu的内存。这些内存在系统进入sleep状态的时候保存PPI的寄存器状态信息，在resume的时候，写回寄存器。对于root GIC，需要注册一个和电源管理的事件通知callback函数。不得不吐槽一下gic\_notifier\_block和gic\_notifier这两个符号的命名，看不出来和电源管理有任何关系。更优雅的名字应该包括pm这样的符号，以便让其他工程师看到名字就立刻知道是和电源管理相关的。

四、GIC callback函数分析

1、irq domain相关callback函数分析

irq domain相关callback函数包括：

（1）gic\_irq\_domain\_map函数：创建IRQ number和GIC hw interrupt ID之间映射关系的时候，需要调用该回调函数。具体代码如下：

> static int gic\_irq\_domain\_map(struct irq\_domain \*d, unsigned int irq, irq\_hw\_number\_t hw)   
> {   
> if (hw < 32) {－－－－－－－－－－－－－－－－－－SGI或者PPI   
> irq\_set\_percpu\_devid(irq);－－－－－－－－－－－－－－－－－－－－－－－－－－（a）   
> irq\_set\_chip\_and\_handler(irq, &gic\_chip, handle\_percpu\_devid\_irq);－－－－－－－（b）   
> set\_irq\_flags(irq, IRQF\_VALID | IRQF\_NOAUTOEN);－－－－－－－－－－－－－－（c）   
> } else {   
> irq\_set\_chip\_and\_handler(irq, &gic\_chip, handle\_fasteoi\_irq);－－－－－－－－－－（d）   
> set\_irq\_flags(irq, IRQF\_VALID | IRQF\_PROBE);
>
> gic\_routable\_irq\_domain\_ops->map(d, irq, hw);－－－－－－－－－－－－－－－－（e）   
> }   
> irq\_set\_chip\_data(irq, d->host\_data);－－－－－设定irq chip的私有数据   
> return 0;   
> }

（a）SGI或者PPI和SPI最大的不同是per cpu的，SPI是所有CPU共享的，因此需要分配per cpu的内存，设定一些per cpu的flag。

（b）设定该中断描述符的irq chip和high level的handler

（c）设定irq flag是有效的（因为已经设定好了chip和handler了），并且request后不是auto enable的。

（d）对于SPI，设定的high level irq event handler是handle\_fasteoi\_irq。对于SPI，是可以probe，并且request后是auto enable的。

（e）有些SOC会在各种外设中断和GIC之间增加cross bar（例如TI的OMAP芯片），这里是为那些ARM SOC准备的

（2）gic\_irq\_domain\_unmap是gic\_irq\_domain\_map的逆过程也就是解除IRQ number和GIC hw interrupt ID之间映射关系的时候，需要调用该回调函数。

（3）gic\_irq\_domain\_xlate函数：除了标准的属性之外，各个具体的interrupt controller可以定义自己的device binding。这些device bindings都需在irq chip driver这个层面进行解析。要给定某个外设的device tree node 和interrupt specifier，该函数可以解码出该设备使用的hw interrupt ID和linux irq type value 。具体的代码如下：

> static int gic\_irq\_domain\_xlate(struct irq\_domain \*d,   
> struct device\_node \*controller,   
> const u32 \*intspec, unsigned int intsize,－－－－－－－－输入参数   
> unsigned long \*out\_hwirq, unsigned int \*out\_type)－－－－输出参数   
> {   
> unsigned long ret = 0;   
> \*out\_hwirq = intspec[1] + 16; －－－－－－－－－－－－－－－－－－－－－（a）
>
> \*out\_type = intspec[2] & IRQ\_TYPE\_SENSE\_MASK; －－－－－－－－－－－（b）
>
> return ret;   
> }

（a）根据gic binding文档的描述，其interrupt specifier包括3个cell，分别是interrupt type（0 表示SPI，1表示PPI），interrupt number（对于PPI，范围是[0-15]，对于SPI，范围是[0-987]），interrupt flag（触发方式）。GIC interrupt specifier中的interrupt number需要加上16（也就是加上SGI的那些ID号），才能转换成GIC的HW interrupt ID。

（b）取出bits[3:0]的信息，这些bits保存了触发方式的信息

2、电源管理的callback函数

TODO

3、irq chip回调函数分析

（1）gic\_mask\_irq函数

这个函数用来mask一个interrupt source。代码如下：

> static void gic\_mask\_irq(struct irq\_data \*d)   
> {   
> u32 mask = 1 << (gic\_irq(d) % 32);
>
> raw\_spin\_lock(&irq\_controller\_lock);   
> writel\_relaxed(mask, gic\_dist\_base(d) + GIC\_DIST\_ENABLE\_CLEAR + (gic\_irq(d) / 32) \* 4);   
> if (gic\_arch\_extn.irq\_mask)   
> gic\_arch\_extn.irq\_mask(d);   
> raw\_spin\_unlock(&irq\_controller\_lock);   
> }

GIC有若干个叫做Interrupt Clear-Enable Registers（具体数目是和GIC支持的hw interrupt数目相关，我们前面说过的，GIC是一个高度可配置的interrupt controller）。这些Interrupt Clear-Enable Registers寄存器的每个bit可以控制一个interrupt source是否forward到CPU interface，写入1表示Distributor不再forward该interrupt，因此CPU也就感知不到该中断，也就是mask了该中断。特别需要注意的是：写入0无效，而不是unmask的操作。

由于不同的SOC厂商在集成GIC的时候可能会修改，也就是说，也有可能mask的代码要微调，这是通过gic\_arch\_extn这个全局变量实现的。在gic-irq.c中这个变量的全部成员都设定为NULL，各个厂商在初始中断控制器的时候可以设定其特定的操作函数。

（2）gic\_unmask\_irq函数

这个函数用来unmask一个interrupt source。代码如下：

> static void gic\_unmask\_irq(struct irq\_data \*d)   
> {   
> u32 mask = 1 << (gic\_irq(d) % 32);
>
> raw\_spin\_lock(&irq\_controller\_lock);   
> if (gic\_arch\_extn.irq\_unmask)   
> gic\_arch\_extn.irq\_unmask(d);   
> writel\_relaxed(mask, gic\_dist\_base(d) + GIC\_DIST\_ENABLE\_SET + (gic\_irq(d) / 32) \* 4);   
> raw\_spin\_unlock(&irq\_controller\_lock);   
> }

GIC有若干个叫做Interrupt Set-Enable Registers的寄存器。这些寄存器的每个bit可以控制一个interrupt source。当写入1的时候，表示Distributor会forward该interrupt到CPU interface，也就是意味这unmask了该中断。特别需要注意的是：写入0无效，而不是mask的操作。

（3）gic\_eoi\_irq函数

当processor处理中断的时候就会调用这个函数用来结束中断处理。代码如下：

> static void gic\_eoi\_irq(struct irq\_data \*d)   
> {   
> if (gic\_arch\_extn.irq\_eoi) {   
> raw\_spin\_lock(&irq\_controller\_lock);   
> gic\_arch\_extn.irq\_eoi(d);   
> raw\_spin\_unlock(&irq\_controller\_lock);   
> }
>
> writel\_relaxed(gic\_irq(d), gic\_cpu\_base(d) + GIC\_CPU\_EOI);   
> }

对于GIC而言，其中断状态有四种：

|  |  |
| --- | --- |
| 中断状态 | 描述 |
| Inactive | 中断未触发状态，该中断即没有Pending也没有Active |
| Pending | 由于外设硬件产生了中断事件（或者软件触发）该中断事件已经通过硬件信号通知到GIC，等待GIC分配的那个CPU进行处理 |
| Active | CPU已经应答（acknowledge）了该interrupt请求，并且正在处理中 |
| Active and Pending | 当一个中断源处于Active状态的时候，同一中断源又触发了中断，进入pending状态 |

processor ack了一个中断后，该中断会被设定为active。当处理完成后，仍然要通知GIC，中断已经处理完毕了。这时候，如果没有pending的中断，GIC就会将该interrupt设定为inactive状态。操作GIC中的End of Interrupt Register可以完成end of interrupt事件通知。

（4）gic\_set\_type函数

这个函数用来设定一个interrupt source的type，例如是level sensitive还是edge triggered。代码如下：

> static int gic\_set\_type(struct irq\_data \*d, unsigned int type)   
> {   
> void \_\_iomem \*base = gic\_dist\_base(d);   
> unsigned int gicirq = gic\_irq(d);   
> u32 enablemask = 1 << (gicirq % 32);   
> u32 enableoff = (gicirq / 32) \* 4;   
> u32 confmask = 0x2 << ((gicirq % 16) \* 2);   
> u32 confoff = (gicirq / 16) \* 4;   
> bool enabled = false;   
> u32 val;
>
> /\* Interrupt configuration for SGIs can't be changed \*/   
> if (gicirq < 16)   
> return -EINVAL;
>
> if (type != IRQ\_TYPE\_LEVEL\_HIGH && type != IRQ\_TYPE\_EDGE\_RISING)   
> return -EINVAL;
>
> raw\_spin\_lock(&irq\_controller\_lock);
>
> if (gic\_arch\_extn.irq\_set\_type)   
> gic\_arch\_extn.irq\_set\_type(d, type);
>
> val = readl\_relaxed(base + GIC\_DIST\_CONFIG + confoff);   
> if (type == IRQ\_TYPE\_LEVEL\_HIGH)   
> val &= ~confmask;   
> else if (type == IRQ\_TYPE\_EDGE\_RISING)   
> val |= confmask;
>
> /\*   
> \* As recommended by the spec, disable the interrupt before changing   
> \* the configuration   
> \*/   
> if (readl\_relaxed(base + GIC\_DIST\_ENABLE\_SET + enableoff) & enablemask) {   
> writel\_relaxed(enablemask, base + GIC\_DIST\_ENABLE\_CLEAR + enableoff);   
> enabled = true;   
> }
>
> writel\_relaxed(val, base + GIC\_DIST\_CONFIG + confoff);
>
> if (enabled)   
> writel\_relaxed(enablemask, base + GIC\_DIST\_ENABLE\_SET + enableoff);
>
> raw\_spin\_unlock(&irq\_controller\_lock);
>
> return 0;   
> }

对于SGI类型的interrupt，是不能修改其type的，因为GIC中SGI固定就是edge-triggered。对于GIC，其type只支持高电平触发（IRQ\_TYPE\_LEVEL\_HIGH）和上升沿触发（IRQ\_TYPE\_EDGE\_RISING）的中断。另外需要注意的是，在更改其type的时候，先disable，然后修改type，然后再enable。

（5）gic\_retrigger

这个接口用来resend一个IRQ到CPU。

> static int gic\_retrigger(struct irq\_data \*d)   
> {   
> if (gic\_arch\_extn.irq\_retrigger)   
> return gic\_arch\_extn.irq\_retrigger(d);
>
> /\* the genirq layer expects 0 if we can't retrigger in hardware \*/   
> return 0;   
> }

看起来这是功能不是通用GIC拥有的功能，各个厂家在集成GIC的时候，有可能进行功能扩展。

（6）gic\_set\_affinity

在多处理器的环境下，外部设备产生了一个中断就需要送到一个或者多个处理器去，这个设定是通过设定处理器的affinity进行的。具体代码如下：

> static int gic\_set\_affinity(struct irq\_data \*d, const struct cpumask \*mask\_val, bool force)   
> {   
> void \_\_iomem \*reg = gic\_dist\_base(d) + GIC\_DIST\_TARGET + (gic\_irq(d) & ~3);   
> unsigned int cpu, shift = (gic\_irq(d) % 4) \* 8;   
> u32 val, mask, bit;
>
> if (!force)   
> cpu = cpumask\_any\_and(mask\_val, cpu\_online\_mask);－－－随机选取一个online的cpu   
> else   
> cpu = cpumask\_first(mask\_val); －－－－－－－－选取mask中的第一个cpu，不管是否online
>
> raw\_spin\_lock(&irq\_controller\_lock);   
> mask = 0xff << shift;   
> bit = gic\_cpu\_map[cpu] << shift;－－－－－－－将CPU的逻辑ID转换成要设定的cpu mask   
> val = readl\_relaxed(reg) & ~mask;   
> writel\_relaxed(val | bit, reg);   
> raw\_spin\_unlock(&irq\_controller\_lock);
>
> return IRQ\_SET\_MASK\_OK;   
> }

GIC Distributor中有一个寄存器叫做Interrupt Processor Targets Registers，这个寄存器用来设定制定的中断送到哪个process去。由于GIC最大支持8个process，因此每个hw interrupt ID需要8个bit来表示送达的process。每一个Interrupt Processor Targets Registers由32个bit组成，因此每个Interrupt Processor Targets Registers可以表示4个HW interrupt ID的affinity，因此上面的代码中的shift就是计算该HW interrupt ID在寄存器中的偏移。

（7）gic\_set\_wake

这个接口用来设定唤醒CPU的interrupt source。对于GIC，代码如下：

> static int gic\_set\_wake(struct irq\_data \*d, unsigned int on)   
> {   
> int ret = -ENXIO;
>
> if (gic\_arch\_extn.irq\_set\_wake)   
> ret = gic\_arch\_extn.irq\_set\_wake(d, on);
>
> return ret;   
> }

设定唤醒的interrupt和具体的厂商相关，这里不再赘述。

4、BSP（bootstrap processor）之外，其他CPU的callback函数

对于multi processor系统，不可能初始化代码在所有的processor上都执行一遍，实际上，系统的硬件会选取一个processor作为引导处理器，我们称之BSP。这个processor会首先执行，其他的CPU都是处于reset状态，等到BSP初始化完成之后，release所有的non-BSP，这时候，系统中的各种外设硬件条件和软件条件（例如per CPU变量）都准备好了，各个non-BSP执行自己CPU specific的初始化就OK了。

上面描述的都是BSP的初始化过程，具体包括：

> ……   
> gic\_dist\_init(gic);－－－－－－初始化GIC的Distributor   
> gic\_cpu\_init(gic);－－－－－－初始化BSP的CPU interface   
> gic\_pm\_init(gic);－－－－－－初始化GIC的Power management   
> ……

对于GIC的Distributor和Power management，这两部分是全局性的，BSP执行初始化一次就OK了。对于CPU interface，每个processor负责初始化自己的连接的那个CPU interface HW block。我们用下面这个图片来描述这个过程：

[![booting](/content/uploadfile/201409/cdec2bc26e9fb0e1a7b3d29389896b5420140909083806.gif "booting")](/content/uploadfile/201409/f9b5b82dcfa88ba9503bb8c835da63c420140909083805.gif)

假设CPUx被选定为BSP，那么第三章描述的初始化过程在该CPU上欢畅的执行。这时候，被初始化的GIC硬件包括：root GIC的Distributor、root GIC CPU Interface x（连接BSP的那个CPU interface）以及其他的级联的非root GIC（上图中绿色block，当然，我偷懒，没有画non-root GIC）。

BSP初始化完成之后，各个其他的CPU运行起来，会发送CPU\_STARTING消息给关注该消息的模块。毫无疑问，GIC driver模块当然要关注这样的消息，在初始化过程中会注册callback函数如下：

> register\_cpu\_notifier(&gic\_cpu\_notifier);

GIC相关的回调函数定义如下：

> static struct notifier\_block gic\_cpu\_notifier = {   
> .notifier\_call = gic\_secondary\_init,   
> .priority = 100,   
> };
>
> static int gic\_secondary\_init(struct notifier\_block \*nfb, unsigned long action, void \*hcpu)   
> {   
> if (action == CPU\_STARTING || action == CPU\_STARTING\_FROZEN)   
> gic\_cpu\_init(&gic\_data[0]);－－－－－－－－－初始化那些非BSP的CPU interface   
> return NOTIFY\_OK;   
> }

因此，当non-BSP booting up的时候，发送CPU\_STARTING消息，调用GIC的callback函数，对上图中的紫色的CPU Interface HW block进行初始化，这样，就完成了全部GIC硬件的初始化过程。

Change log：  
11月3号，修改包括：  
1、使用GIC-V2这样更通用的描述，而不是仅仅GIC-400

*原创文章，转发请注明出处。蜗窝科技，[/irq_subsystem/gic_driver.html](/irq_subsystem/gic_driver.html)*
