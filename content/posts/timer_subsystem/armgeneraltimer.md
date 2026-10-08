---
title: "Linux时间子系统之（十七）：ARM generic timer驱动代码分析"
date: 2014-12-02T10:47:58+08:00
url: "/timer_subsystem/armgeneraltimer.html"
gid: "115"
emlog_type: "blog"
summary: "\r\n\t关注ARM平台上timer driver（clocksource chip driver和clockevent chip \r\ndriver）的驱动工程师应该会注意到timer硬件的演化过程。在单核时代，各个SOC vendor厂商购买ARM \r\ncore的IP，然后自己设计SOC上的peripherals，这里面就包括了timer的硬件。由于没有统一的标准，各个厂商的设计各不相同，这给驱\r\n"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["armv7-timer", "arm_arch_timer"]
views: 74645
comment_count: 76
aliases:
  - "/timer_subsystem/115.html"
  - "/115.html"
---

一、前言

关注ARM平台上timer driver（clocksource chip driver和clockevent chip driver）的驱动工程师应该会注意到timer硬件的演化过程。在单核时代，各个SOC vendor厂商购买ARM core的IP，然后自己设计SOC上的peripherals，这里面就包括了timer的硬件。由于没有统一的标准，各个厂商的设计各不相同，这给驱动工程师带来了工作量。然而，如果仅仅是工作量的话就还好，实际上，不仅仅如此。linux的时间子系统要求硬件timer提供下面两种能力：一是free running的counter，此外需要能够在指定的counter值上产生中断的能力。有些硬件厂商会考虑到软件的需求（例如：PXA270的timer硬件），但是有些硬件厂商做的就不够，例如：S3C2451的timer硬件。我们在写PXA270的timer硬件驱动的时候是毫无压力的，而在写S3C2451的timer的驱动的时候，最大的愿望就是把三星的HW timer的设计人员拉出来打一顿。

进入多核时代后，ARM公司提供了timer的硬件设计，集成在了自己的多核结构中。例如：在Cortex A15 MPcore的硬件体系结构中有一个HW block叫做Generic Timer（该硬件取代了A9中的global timer、private timer的功能），为系统提供了计时以及触发timer event的功能。

本文主要描述了Generic Timer的相关硬件知识以及在linux kernel中如何驱动该硬件。Generic Timer的代码位于linux-3.14/drivers/clocksource/目录下，该目录保存了所有clock source相关的driver，arm\_arch\_timer.c就是驱动Cortex A15 MPcore的Generic Timer的。

二、硬件描述

1、block diagram

ARM generic timer相关的硬件block如下图所示（用绿色标记）：

[![gtimer](/content/uploadfile/201412/06ad52a8cb19cbde0df7b108604ca42320141202024530.gif "gtimer")](/content/uploadfile/201412/5267fe0047e416ccfce1c675a69b1f0a20141202024428.gif)

ARM generic timer的硬件block主要是SOC上的System counter（多个process共享，用来记录时间的流逝）以及附着在各个processor上的Timer（用于触发timer event）组成，其他的generic timer的硬件电路主要是用来进行交流generic time event的。例如各个processor中的timer和system counter外设进行交互，各个processor中的timer进行信息交互。System counter的功能很简单，就是计算输入时钟已经过了多少个clock，开始的时候是0，每一个clock，System counter会加一。System counter的counter value需要分发到各个timer中，也就是说，从各个timer的角度看，system counter value应该是一致的。Timer其实就是定时器，它可以定义一段指定的时间，当时间到了，就会assert一个外部的输出信号（可以输出到GIC，作为一个interrupt source）。

从power domain来看，ARM generic timer分成两个部分：System counter和各个Multiprocessor系统中的Timer\_x、接口电路等。之所以这么分原因很明显：功耗方面（电源管理）的考量。在power saving mode下，可以shutdown各个processor系统的供电，但是可以保持system counter的供电，这样，至少系统时间可以保持住。

和power domain类似，clock domain也是不同的，system counter和processor工作在不同的clock下，软件修改了CPU的频率也不会影响system counter的工作节奏，从而也不会改变timer的行为。

2、System counter

关于System Counter的规格整理如下：

|  |  |
| --- | --- |
| 规格 | 描述 |
| System counter的计数器有多少bit？ | 至少56个bit，和具体的实现相关。 |
| 输入频率的范围为何？ | 典型值是1M～50MHz |
| 操作模式为何？ | 正常的时候，每个clock都会加一，但是，在power saving mode的时候，我们希望功耗可以更低一些，这时候会考虑将system clock的输入频率降低下来，例如降低4倍。为了保证system counter的计时是准确的，可以设定每个clock增加4，而不是加1，这样system counter的计时仍然保持准确。 |
| 溢出时间 | 至少40年 |
| 精度要求为何？ | 未规定，推荐是每24小时在正负10秒的误差 |
| reset值为何？ | 0 |
| 是否支持debug？ | 可以设定enable halt-on-debug。这个和JTAG调试相关。如果你使用JTAG调试，在单步运行的时候当然系统counter停下来，否则timer的中断就会来了，导致你无法正常的进行程序代码跟踪。 |

除了基本的计时功能，system count还提供了event stream的功能。我们知道，ARMv7的处理器提供了wait for event的机制，该机制允许processor进入low power state并等待event的到来。这个event可能是来自另外的process的send event指令，也可能是外部HW block产生的event，比如来自system counter的wake-up event。软件可以配置system counter产生周期性的event，具体可以配置的参数包括：

（1）指定产生event的bit。我们可以选择system counter中的低16bit。

（2）选定的bit当发生0到1的迁移（或是1到0的迁移）产生event

经过配置后，实际上system counter产生的是一个event stream，event产生的频率是由选定的bit位置决定的。设定bit 0会产出频率非常高的event stream，而设定15bit会产生频率最慢的event stream，因为system counter的值不断累加，直到bit 15发生翻转才会触发一个event。

3、Timers

各个cpu的timer是根据system counter的值来触发timer event的，因此，系统中一定有一个机制让System counter的值广播到各个CPU的timer HW block上，同时运行在各个processor上的软件可以通过接口获取System counter的值。

处理器可以通过CNTPCT寄存器来获取system counter的当前值，我们称之physical counter。有physical就有virtual，processor可以通过CNTVCT寄存器访问virtual counter，不过，对于不支持security extension和virtualization extension的系统，virtual counter和physical counter是一样的值。

系统中每个processor都会附着多个timer，具体如下：

（1）对于不支持security extension的SOC（不支持security extension也就意味着 不支持virtualization extension），timer实际上有两个，一个是physical timer，另外一个是virtual timer。虽然有两个，不过从行为上看，virtual timer和physical timer行为一致

（2）对于支持security extension但不支持virtualization extension的SOC，每个cpu有三个timer：Non-secure physical timer，Secure physical timer和virtual timer

（3）对于支持virtualization extension的SOC，每个cpu有四个timer：Non-secure PL1 physical timer，Secure PL1 physical timer，Non-secure PL2 physical timer和virtual timer

每个timer都会有三个寄存器（我们用physical timer为例描述）：

（1）64-bit CompareValue register。该寄存器配合system counter可以实现一个64 bit unsigned upcounter。如果physical counter - CompareValue >= 0的话，触发中断。也就是说，CompareValue register其实就是一个64比特的upcounter，设定为一个比当前system counter要大的值，随着system counter的不断累加，当system counter value触及CompareValue register设定的值的时候，便会向GIC触发中断。

（2）32-bit TimerValue register。该寄存器配合system counter可以实现一个32 bit signed downcounter（有的时候，使用downcounter会让软件逻辑更容易，看ARM generic timer的设计人员考虑的多么周到）。开始的时候，我们可以设定TimerValue寄存器的值为1000（假设我们想down count 1000，然后触发中断），向该寄存器写入1000实际上也就是设定了CompareValue register的值是system counter值加上1000。随着system counter的值不断累加，TimerValue register的值在递减，当值<=0的时候，便会向GIC触发中断

（3）32-bit控制寄存器。该寄存器主要对timer进行控制，具体包括：enable或是disable该timer，mask或者unmask该timer的output signal（timer interrupt）

各个processor的各个Timer都可以产生中断，因此它和GIC有接口。当然，由于timer的中断是属于各个CPU的，因此使用PPI类型的中断，具体可以参考GIC文档。当然，如果让timer触发中断，当然要确保该timer是enable并且是umask的。

4、软件编程接口

由上面的描述可知，ARM generic timer的硬件包括两个部分：一个是per cpu的timer硬件，另外一个就是system level的counter硬件。对于per cpu的timer硬件，使用system control register（CP15）来访问是最合适的，而且速度也快。要访问system level的counter硬件，当然使用memory mapped IO的形式（请注意block diagram中的APB总线，很多system level的外设都是通过APB访问的）。

三、初始化

1、Generic Timer的device node和Generic Timer clocksource driver的匹配过程

（1）clock source driver中的声明

在linux/include/linux/clocksource.h目录下的clocksource.h文件中定义了CLOCKSOURCE\_OF\_DECLARE宏如下：

> #define CLOCKSOURCE\_OF\_DECLARE(name, compat, fn) \   
> static const struct of\_device\_id \_\_clksrc\_of\_table\_##name \   
> \_\_used \_\_section(\_\_clksrc\_of\_table) \   
> = { .compatible = compat, \   
> .data = (fn == (clocksource\_of\_init\_fn)NULL) ? fn : fn }

CLOCKSOURCE\_OF\_DECLARE这个宏其实就是初始化了一个struct of\_device\_id的静态常量，并放置在\_\_clksrc\_of\_table section中。arm\_arch\_timer.c文件中使用CLOCKSOURCE\_OF\_DECLARE这个宏定义了若干个静态的struct of\_device\_id常量，如下：

> CLOCKSOURCE\_OF\_DECLARE(armv7\_arch\_timer, "arm,armv7-timer", arch\_timer\_init);   
> CLOCKSOURCE\_OF\_DECLARE(armv8\_arch\_timer, "arm,armv8-timer", arch\_timer\_init);
>
> CLOCKSOURCE\_OF\_DECLARE(armv7\_arch\_timer\_mem, "arm,armv7-timer-mem",   
> arch\_timer\_mem\_init);

这里compatible的名字使用了armv7、armv8这样的字样而不是Cortex A15，我猜测ARM公司是认为这样的generic timer的硬件block是ARMv7或者v8指令集的特性，所有使用这些指令集的core都应该使用这样的generic timer的硬件结构。不论是v7还是v8，其初始化函数都是一个arch\_timer\_init。从这个角度看，把ARM的generic timer的驱动放到drivers的目录下更合理（原来是放在arch目录下），这样多个arch（ARM和ARM64）可以共享一个ARM ARCH timer的驱动程序。

这里还有一个疑问是："arm,armv7-timer"和"arm,armv7-timer-mem"有什么不同？实际上访问ARM generic timer有两种形式，一种是通过协处理器CP15访问timer的寄存器，我们称之CP15 timer。另外一种是通过寄存器接口访问timer，也就是说，generic timer的控制寄存器被memory map到CPU的地址空间，这种我们称之memory mapped timer。arch\_timer\_mem\_init是for memory mapped timer类型的驱动初始化的，arch\_timer\_init是for CP15 timer类型的驱动进行初始化的。

Travelhop同学在他的[程序员的“纪律性”](/tech_discuss/109.html)文章中说到：有技术追求的年轻人要多问几个为什么？因此，我们这里再追问一个问题：为何要有CP15 timer和memory mapped timer呢？都能完成对ARM generic timer的控制，为什么要提供两种方式呢？其实最开始的时候，driver只支持CP15 type的timer访问形态，毕竟这种方式比memory mapped register的访问速度要更快一些。但是，这种方式不能控制system level的counter硬件部分（只能使用memory mapped IO形式访问），因此功能受限。比如：system counter可以提供一组frequency table，可以让软件设定当然counter的输入频率以及每个clock下counter增加的数目。这样的设定可以让system counter的硬件在不同的输入频率下工作，有更好的电源管理特性。

此外，有些系统不支持协处理的访问，这种情况下又想给系统增加ARM generic timer的功能，这时候必须使用memory mapped register的方式来访问ARM generic timer的所有硬件block（包括system counter和per cpu的timer）。这时候，在访问timer硬件的时候虽然性能不佳，但总是好过功能丧失。

在linux kernel编译的时候，你可以配置多个clocksource进入内核，编译系统会把所有的CLOCKSOURCE\_OF\_DECLARE宏定义的数据放入到一个特殊的section中（section name是\_\_clksrc\_of\_table），我们称这个特殊的section叫做clock source table。这个table也就保存了kernel支持的所有的clock source的ID信息（最重要的是驱动代码初始化函数和DT compatible string）。我们来看看struct of\_device\_id的定义：

> struct of\_device\_id   
> {   
> char name[32];－－－－－－要匹配的device node的名字   
> char type[32];－－－－－－－要匹配的device node的类型   
> char compatible[128];－－－匹配字符串（DT compatible string），用来匹配适合的device node   
> const void \*data;－－－－－－－－对于clock source，这里是初始化函数指针   
> };

这个数据结构主要被用来进行Device node和driver模块进行匹配用的。从该数据结构的定义可以看出，在匹配过程中，device name、device type和DT compatible string都是考虑的因素。更细节的内容请参考\_\_of\_device\_is\_compatible函数。

（2）device node

一个示例性的Generic Timer（CP15 type的timer）的device node（我们以瑞芯微的RK3288处理器为例）定义如下：

> timer {  
> compatible = "arm,armv7-timer";  
> interrupts = <GIC\_PPI 13 (GIC\_CPU\_MASK\_SIMPLE(4) | IRQ\_TYPE\_LEVEL\_HIGH)>,  
> <GIC\_PPI 14 (GIC\_CPU\_MASK\_SIMPLE(4) | IRQ\_TYPE\_LEVEL\_HIGH)>,  
> <GIC\_PPI 11 (GIC\_CPU\_MASK\_SIMPLE(4) | IRQ\_TYPE\_LEVEL\_HIGH)>,  
> <GIC\_PPI 10 (GIC\_CPU\_MASK\_SIMPLE(4) | IRQ\_TYPE\_LEVEL\_HIGH)>;  
> clock-frequency = <24000000>;  
> };

Generic Timer这个HW block的Device node中定义了各种属性，其中就包括了System counter的输入clock frequency，中断资源描述等信息。compatible 属性用于驱动匹配的，在系统启动的时候，系统中的所有的device node形成一个树状结构，在clock source初始化的时候进行device node和driver匹配（compatible 字符串的比对），device node携带的信息会在初始化的时候传递给具体的驱动。该节点的各个属性的具体含义后面会详细描述。

MMIO type的timer的device node（我们以高通的msm8974处理器为例）定义如下：

> timer@f9020000 {   
> #address-cells = <1>;   
> #size-cells = <1>;   
> ranges;   
> compatible = "arm,armv7-timer-mem";   
> reg = <0xf9020000 0x1000>;－－－－－－－－system counter的寄存器   
> clock-frequency = <19200000>;
>
> frame@f9021000 {－－－－－－－－－－－percpu的timer的定义，目前最大支持8个frame   
> frame-number = <0>;   
> interrupts = <0 8 0x4>, －－－－－－－physical timer的中断   
> <0 7 0x4>; －－－－－－－－－－virtual timer的中断   
> reg = <0xf9021000 0x1000>,－－－－－first view base address   
> <0xf9022000 0x1000>;－－－－－－second view base address
>
> };
>
> ……
>
> };

（3）device node和clock source driver的匹配

在系统初始化的时候start\_kernel函数会调用time\_init进行时间子系统的初始化，代码如下：

> void \_\_init time\_init(void)   
> {   
> if (machine\_desc->init\_time) {   
> machine\_desc->init\_time();   
> } else {   
> #ifdef CONFIG\_COMMON\_CLK   
> of\_clk\_init(NULL);   
> #endif   
> clocksource\_of\_init();   
> }   
> }

clock source的初始化有两种形态，一种是调用machine driver的init\_time函数，另外一种是调用clocksource\_of\_init，使用device tree形式的初始化。具体使用哪种形态的初始化是和系统设计相关的，我们这里来看看device tree形式的初始化，毕竟device tree是未来的方向。具体代码如下：

> void \_\_init clocksource\_of\_init(void)   
> {   
> struct device\_node \*np;   
> const struct of\_device\_id \*match;   
> clocksource\_of\_init\_fn init\_func;   
> unsigned clocksources = 0;
>
> for\_each\_matching\_node\_and\_match(np, \_\_clksrc\_of\_table, &match) {   
> if (!of\_device\_is\_available(np))   
> continue;
>
> init\_func = match->data;   
> init\_func(np);   
> clocksources++;   
> }   
> if (!clocksources)   
> pr\_crit("%s: no matching clocksources found\n", \_\_func\_\_);   
> }

\_\_clksrc\_of\_table就是内核的clock source table，这个table也就保存了kernel支持的所有的clock source driver的ID信息（用于和device node的匹配）。clocksource\_of\_init函数执行之前，系统已经完成了device tree的初始化，因此系统中的所有的设备节点都已经形成了一个树状结构，每个节点代表一个设备的device node。clocksource\_of\_init是针对系统中的所有的device node，扫描clock source table，进行匹配，一旦匹配到，就调用该clock source driver的初始化函数，并把该timer硬件的device node作为参数传递给clocksource driver。

2、CP15 Timer初始化代码分析

CP15 Timer初始化代码如下所示：

> static void \_\_init arch\_timer\_init(struct device\_node \*np)   
> {   
> int i;
>
> if (arch\_timers\_present & ARCH\_CP15\_TIMER) {－－－－－－－－－－－－－－－－（1）   
> pr\_warn("arch\_timer: multiple nodes in dt, skipping\n");   
> return;   
> }
>
> arch\_timers\_present |= ARCH\_CP15\_TIMER;
>
> for (i = PHYS\_SECURE\_PPI; i < MAX\_TIMER\_PPI; i++)－－－－－－－－－－－－－－（2）   
> arch\_timer\_ppi[i] = irq\_of\_parse\_and\_map(np, i);
>
> arch\_timer\_detect\_rate(NULL, np); －－－－－－－－－－－－－－－－－－－－－－－－（3）
>
> if (is\_hyp\_mode\_available() || !arch\_timer\_ppi[VIRT\_PPI]) {－－－－－－－－－－－－－（4）   
> arch\_timer\_use\_virtual = false;
>
> if (!arch\_timer\_ppi[PHYS\_SECURE\_PPI] ||   
> !arch\_timer\_ppi[PHYS\_NONSECURE\_PPI]) {   
> pr\_warn("arch\_timer: No interrupt available, giving up\n");   
> return;   
> }   
> }
>
> arch\_timer\_register(); －－－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> arch\_timer\_common\_init(); －－－－－－－－－－－－－－－－－－－－－－－－（6）   
> }

（1）arch\_timers\_present用来记录系统中的timer情况，定义如下：

> #define ARCH\_CP15\_TIMER BIT(0)   
> #define ARCH\_MEM\_TIMER BIT(1)   
> static unsigned arch\_timers\_present \_\_initdata;

该变量只有两个bit有效，bit 0标识是否有CP15 timer，bit 1标识memory mapped timer是否已经初始化。

如果在调用arch\_timer\_init之前，ARCH\_CP15\_TIMER已经置位，说明之前已经有一个ARM arch timer的device node进行了初始化的动作，这多半是由于device tree的database中有两个或者多个cp15 timer的节点，这时候，我们初始化一个就OK了。

（2）这部分的代码是分配IRQ。ARM generic timer使用4个PPI的中断，对于Cortex A15，和timer相关的PPI包括：

> Secure Physical Timer event (ID 29，也就是上面device node中的13，29 = 16 + 13)   
> Non-secure Physical Timer event (ID 30，也就是上面device node中的14，30 = 16 + 14)   
> Virtual Timer event (ID 27)   
> Hypervisor Timer event (ID 26)

函数irq\_of\_parse\_and\_map对该device node中的interrupt属性进行分析，并分配IRQ number，建立HW interrupt ID和该IRQ number的映射。irq\_of\_parse\_and\_map这个函数在中断子系统中已经详细描述过了，这里不再赘述。至此，arch\_timer\_ppi数组中保存了ARM generic timer使用IRQ number。

（3）arch\_timer\_detect\_rate这个函数用来确定system counter的输入clock频率，具体实现如下：

> static void arch\_timer\_detect\_rate(void \_\_iomem \*cntbase, struct device\_node \*np)   
> {   
> if (of\_property\_read\_u32(np, "clock-frequency", &arch\_timer\_rate)) {   
> if (cntbase)   
> arch\_timer\_rate = readl\_relaxed(cntbase + CNTFRQ);   
> else   
> arch\_timer\_rate = arch\_timer\_get\_cntfrq();   
> }   
> }

arch\_timer\_rate这个全局变量用来保存system counter的输入频率，基本上，这个数据有两个可能的来源：

（a）device tree node中的clock-frequency属性

（b）寄存器CNTFRQ

我们优先考虑从clock-frequency属性中获取该数据，如果device node中没有定义该属性，那么从CNTFRQ寄存器中读取。访问CNTFRQ寄存器有两种形态，如果cntbase是NULL的话，说明是CP15 timer，可以通过协处理器来获取该值（调用arch\_timer\_get\_cntfrq函数）。如果给出了cntbase的值，说明是memory mapped的方式来访问CNTFRQ寄存器（直接使用readl\_relaxed函数）。

（4）如果没有定义virtual timer的中断（arch\_timer\_ppi[VIRT\_PPI]==0），那么我们只能是使用physical timer的，这时候，需要设定arch\_timer\_use\_virtual这个全局变量为false。arch\_timer\_use\_virtual这个变量名字已经说明的很清楚了，它标识系统是否使用virtual timer。ok，既然使用physical timer，那么需要定义physical timer中断，包括secure和non-secure physical timer event PPI。只要有一个没有定义，那么就出错退出了。

如果系统支持虚拟化，那么CPU会处于HYP mode，这时候，我们也是应该使用physical timer的，virtual timer是guest OS需要访问的。

（5） arch\_timer\_register的代码如下：

> static int \_\_init arch\_timer\_register(void)   
> {   
> int err;   
> int ppi;
>
> arch\_timer\_evt = alloc\_percpu(struct clock\_event\_device);－－－－－－－－－－－－（a）
>
> if (arch\_timer\_use\_virtual) {－－－－－－－－－－－－－－－－－－－－－－－－－－（b）   
> ppi = arch\_timer\_ppi[VIRT\_PPI];   
> err = request\_percpu\_irq(ppi, arch\_timer\_handler\_virt,   
> "arch\_timer", arch\_timer\_evt);   
> } else {   
> ppi = arch\_timer\_ppi[PHYS\_SECURE\_PPI];   
> err = request\_percpu\_irq(ppi, arch\_timer\_handler\_phys,   
> "arch\_timer", arch\_timer\_evt);   
> if (!err && arch\_timer\_ppi[PHYS\_NONSECURE\_PPI]) {   
> ppi = arch\_timer\_ppi[PHYS\_NONSECURE\_PPI];   
> err = request\_percpu\_irq(ppi, arch\_timer\_handler\_phys,   
> "arch\_timer", arch\_timer\_evt);   
>   
> }   
> }
>
> err = register\_cpu\_notifier(&arch\_timer\_cpu\_nb);－－－－－－－－－－－－－－－－（c）
>
> err = arch\_timer\_cpu\_pm\_init();－－－－－－－－－－－－－－－－－－－－－－－（d）
>
> arch\_timer\_setup(this\_cpu\_ptr(arch\_timer\_evt)); －－－－－－－－－－－－－－－－（e）
>
> return 0;
>
> }

（a）分配一个类型是struct clock\_event\_device的per cpu变量。struct clock\_event\_device是对一个能够触发timer event的设备进行抽象。对于ARM generic timer而言，每个CPU都有一个timer硬件block，就是一个clock event device。

（b）根据当前是使用physical timer还是virtual timer，分别注册一个per cpu的IRQ。如果使用physical timer的话，需要注册secure和non-secure physical timer event PPI。如果使用virtual timer的话，需要注册virtual timer中断。

（c）这里的代码主要是formulti core系统的，用于non-BSP上的generic timer硬件的初始化，其概念类似[GIC driver的初始化](/irq_subsystem/gic_driver.html)，这里就不再具体描述了。

（d）这里主要是注册一个回调函数，在processor进入和退出low power state的时候会调用该回调函数进行电源管理相关的处理。

（e）初始化BSP上的timer硬件对应的clock event device，并调用clockevents\_register\_device函数将该clock event device注册到linux kernel的时间子系统中。non-BSP的timer硬件的setup是通过event notifier机制完成的，具体请参考步骤c。

（6）CP15 timer和memory mapped timer虽然接口形态不一样，但是总是有共同的部分，这些代码被封装到arch\_timer\_common\_init函数中，具体如下：

> static void \_\_init arch\_timer\_common\_init(void)   
> {   
> unsigned mask = ARCH\_CP15\_TIMER | ARCH\_MEM\_TIMER; －－－－－－－－－（a）   
> if ((arch\_timers\_present & mask) != mask) {   
> if (of\_find\_matching\_node(NULL, arch\_timer\_mem\_of\_match) &&   
> !(arch\_timers\_present & ARCH\_MEM\_TIMER))   
> return;   
> if (of\_find\_matching\_node(NULL, arch\_timer\_of\_match) &&   
> !(arch\_timers\_present & ARCH\_CP15\_TIMER))   
> return;   
> }
>
> arch\_timer\_banner(arch\_timers\_present);－－－－－－－－－－－－－－－－－（b）   
> arch\_counter\_register(arch\_timers\_present);－－－－－－－－－－－－－－－－（c）   
> arch\_timer\_arch\_init();－－－－－－－－－－－－－－－－－－－－－－－－－－（d）   
> }

（a）实际上，即便是系统中存在两种timer，这个函数的代码执行一次就OK了。这很好理解，例如arch\_counter\_register函数用来注册system count，而实际上，无论是CP15 timer还是memory mapped的timer，system counter是system level的，只有一个，注册一次就OK了。

明白了上面的思路后，这段代码就比较简单了。在系统中存在两种timer的时候，要等到后一个timer初始化的时候再执行后面具体的arch\_timer\_banner到arch\_timer\_arch\_init部分的代码。

（b）输出ARM generic timer的相关信息到控制台

（c）向linux kernel的时间子系统注册clock source、timer counter、shed clock设备。

（d）主要是注册delay timer（忙等待那种）。

3、memory mapped Timer初始化代码分析

TODO

四、和linux kernel时间子系统的接口

linux的时间子系统需要两种时间相关的硬件：一个是free running的counter（system counter），抽象为clock source device，另外一个就是能够产生中断的能力的timer（per cpu timer），抽象为clock event device。对于ARM generic timer driver而言，我们需要定义linux kernel时间子系统的clock source和clock event device并注册到系统。

1、定义clocksource并注册到系统

ARM generic timer中的system counter硬件block对应的clock source定义如下：

> static struct clocksource clocksource\_counter = {   
> .name = "arch\_sys\_counter",   
> .rating = 400,   
> .read = arch\_counter\_read,   
> .mask = CLOCKSOURCE\_MASK(56),   
> .flags = CLOCK\_SOURCE\_IS\_CONTINUOUS | CLOCK\_SOURCE\_SUSPEND\_NONSTOP,   
> };

（这里顺便吐槽一下clocksource\_counter这个变量名，实在是太差了）rating标识该clock source的精度等级，数字越大，精度等级越高。read函数用来读取当前counter的值。在ARM generic timer驱动初始化的过程中会调用arch\_counter\_register函数注册该clock source：

> static void \_\_init arch\_counter\_register(unsigned type)   
> {   
> u64 start\_count;
>
> if (type & ARCH\_CP15\_TIMER)－－－－－－－－－－－－－－－－－－－－（1）   
> arch\_timer\_read\_counter = arch\_counter\_get\_cntvct;   
> else   
> arch\_timer\_read\_counter = arch\_counter\_get\_cntvct\_mem;
>
> start\_count = arch\_timer\_read\_counter();   
> clocksource\_register\_hz(&clocksource\_counter, arch\_timer\_rate);－－－－－－（2）   
> cyclecounter.mult = clocksource\_counter.mult;   
> cyclecounter.shift = clocksource\_counter.shift;   
> timecounter\_init(&timecounter, &cyclecounter, start\_count); －－－－－－－－－（3）
>
> /\* 56 bits minimum, so we assume worst case rollover \*/   
> sched\_clock\_register(arch\_timer\_read\_counter, 56, arch\_timer\_rate);－－－－－－（4）   
> }

（1）在定义ARM generic timer的clock source的时候，read函数被设定成arch\_counter\_read，该函数会调用arch\_timer\_read\_counter 函数，而这个函数指针会在初始化的时候根据timer的类型进行设定。

（2）向系统注册一个clock soure（也就是一个free running的counter），并给出counter的工作频率作为传入的参数。linux时间子系统的clock source模块会根据counter的工作频率设定struct clocksource的各个成员，例如mult和shitf等

（3）clocksource模块是为timekeeping模块提供服务的，但是其他的驱动模块也有一些计时需求，这时候可以考虑使用timercounter。ARM generic timer静态定义了一个timercounter的全局变量，其他模块可以通过arch\_timer\_get\_timecounter获取timercounter，并可以调用timecounter\_read获取一个纳秒值。

（4）TODO

2、定义clock\_event\_device并注册到系统

和clocksource不同，ARM generic timer是由alloc\_percpu动态分配的。考虑到system counter只有一个，而timer是附着在各个CPU上，这样的分配也是合理的。在driver的初始化过程中（先是BSP初始化，然后其他CPU的初始化是通过event notifier机制完成），会调用arch\_timer\_setup来初始化clock\_event\_device数据结构并注册到系统中。

> static int arch\_timer\_setup(struct clock\_event\_device \*clk)   
> {   
> \_\_arch\_timer\_setup(ARCH\_CP15\_TIMER, clk); －－－－初始化clock event device并注册到系统
>
> if (arch\_timer\_use\_virtual)－－－－－－－－－－enable timer interrupt   
> enable\_percpu\_irq(arch\_timer\_ppi[VIRT\_PPI], 0);   
> else {   
> enable\_percpu\_irq(arch\_timer\_ppi[PHYS\_SECURE\_PPI], 0);   
> if (arch\_timer\_ppi[PHYS\_NONSECURE\_PPI])   
> enable\_percpu\_irq(arch\_timer\_ppi[PHYS\_NONSECURE\_PPI], 0);   
> }
>
> arch\_counter\_set\_user\_access();   
> if (IS\_ENABLED(CONFIG\_ARM\_ARCH\_TIMER\_EVTSTREAM))－－－判断是否enable了timer event   
> arch\_timer\_configure\_evtstream(); －－－－－－－配置并enable timer event
>
> return 0;   
> }

TODO：这里等到完成clockevent文档之后再来更新。

*原创文章，转发请注明出处。蜗窝科技*

[/linux_kenrel/arm-generic-timer.html](/linux_kenrel/arm-generic-timer.html)
