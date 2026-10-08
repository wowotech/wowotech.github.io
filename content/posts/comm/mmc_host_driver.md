---
title: "Linux MMC framework(2)_host controller driver"
date: 2017-03-08T21:33:47+08:00
url: "/comm/mmc_host_driver.html"
gid: "383"
emlog_type: "blog"
summary: "本文是Linux MMC framework的第二篇，将从驱动工程师的角度，介绍MMC host controller \r\ndriver有关的知识，学习并掌握如何在MMC \r\nframework的框架下，编写MMC控制器的驱动程序。同时，通过本篇文章，我们会进一步的理解MMC、SD、SDIO等有关的基础知识。"
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "Kernel", "内核", "driver", "mmc", "host"]
views: 27531
comment_count: 10
aliases:
  - "/comm/383.html"
  - "/383.html"
---

## 1. 前言

本文是Linux MMC framework的第二篇，将从驱动工程师的角度，介绍MMC host controller
driver有关的知识，学习并掌握如何在MMC
framework的框架下，编写MMC控制器的驱动程序。同时，通过本篇文章，我们会进一步的理解MMC、SD、SDIO等有关的基础知识。

## 2. MMC host驱动介绍

MMC的host driver，是用于驱动MMC
host控制器的程序，位于“drivers/mmc/host”目录。从大的流程上看，编写一个这样的驱动非常简单，只需要三步：

> 1）调用mmc\_alloc\_host，分配一个struct
> mmc\_host类型的变量，用于描述某一个具体的MMC host控制器。
>
> 2）根据MMC host控制器的硬件特性，填充struct mmc\_host变量的各个字段，例如MMC类型、电压范围、操作函数集等等。
>
> 3）调用mmc\_add\_host接口，将正确填充的MMC host注册到MMC core中。

当然，看着简单，一牵涉到实现细节，还是很麻烦的，后面我们会慢慢分析。

注1：分析MMC host driver的时候，Linux
kernel中有大把大把的例子（例如drivers/mmc/host/pxamci.c），大家可尽情参考、学习，不必谦虚（这是学习Linux的最佳方法）。

注2：由于MMC host
driver牵涉到具体的硬件controller，分析的过程中需要一些具体的硬件辅助理解，本文将以“[X
Project](/sort/x_project)”所使用Bubblegum-96平台为例，具体的硬件spec可参考[1]。

## 3. 主要数据结构

#### 3.1 struct mmc\_host

MMC core使用struct mmc\_host结构抽象具体的MMC host
controller，该结构的定义位于“include/linux/mmc/host.h”中，它既可以用来描述MMC控制器所具有的特性、能力（host
driver关心的内容），也保存了host driver运行过程中的一些状态、参数（MMC core关心的内容）。需要host
driver关心的部分的具体的介绍如下：

> parent，一个struct device类型的指针，指向该MMC host的父设备，一般是注册该host的那个platform设备；
>
> class\_dev，一个struct device类型的变量，是该MMC
> host在设备模型中作为一个“设备”的体现。当然，人如其名，该设备从属于某一个class（mmc\_host\_class）；
>
> ops，一个struct mmc\_host\_ops类型的指针，保存了该MMC host有关的操作函数集，具体可参考3.2小节的介绍；
>
> pwrseq，一个struct mmc\_pwrseq类型的指针，保存了该MMC host电源管理有关的操作函数集，具体可参考3.2小节的介绍；
>
> f\_min、f\_max、f\_init，该MMC host支持的时钟频率范围，最小频率、最大频率以及初始频率；
>
> ocr\_avail，该MMC host可支持的操作电压范围（具体可参考include/linux/mmc/host.h中MMC\_VDD\_开头的定义）；   
> 注3：OCR（Operating Conditions
> Register）是MMC/SD/SDIO卡的一个32-bit的寄存器，其中有些bit指明了该卡的操作电压。MMC
> host在驱动这些卡的时候，需要和Host自身所支持的电压范围匹配之后，才能正常操作，这就是ocr\_avail的存在意义。
>
> ocr\_avail\_sdio、ocr\_avail\_sd、ocr\_avail\_mmc，如果MMC
> host针对SDIO、SD、MMC等不同类型的卡，所支持的电压范围不同的话，需要通过这几个字段特别指定。否则，不需要赋值（初始化为0）；
>
> pm\_notify，一个struct notifier\_block类型的变量，用于支持power management有关的notify实现；
>
> max\_current\_330、max\_current\_300、max\_current\_180，当工作电压分别是3.3v、3v以及1.8v的时候，所支持的最大操作电流（如果MMC
> host没有特别的限制，可以不赋值）；
>
> caps、caps2，指示该MMC host所支持的功能特性，具体可参考3.4小节的介绍；
>
> pm\_caps，mmc\_pm\_flag\_t类型的变量，指示该MMC host所支持的电源管理特性；
>
> max\_seg\_size、max\_segs、max\_req\_size、max\_blk\_size、max\_blk\_count、max\_busy\_timeout，和块设备（如MMC、SD、eMMC等）有关的参数，在古老的磁盘时代，这些参数比较重要。对基于MMC技术的块设备来说，硬件的性能大大提升，这些参数就没有太大的意义了。具体可参考5.2章节有关MMC数据传输的介绍；
>
> lock，一个spin lock，是MMC host driver的私有变量，可用于保护host driver的临界资源；
>
> ios，一个struct mmc\_ios类型的变量，用于保存MMC bus的当前配置，具体可参考3.5小节的介绍；
>
> supply，一个struct mmc\_supply类型的变量，用于描述MMC系统中的供电信息，具体可参考3.6小节的介绍；
>
> ……
>
> private，一个0长度的数组，可以在mmc\_alloc\_host时指定长度，由host controller
> driver自行支配。

#### 3.2 struct mmc\_host\_ops

struct mmc\_host\_ops抽象并集合了MMC host controller所有的操作函数集，包括：

1）数据传输有关的函数

> /\*   
> \* It is optional for the host to implement pre\_req and post\_req in   
> \* order to support double buffering of requests (prepare one   
> \* request
> while another request is active).   
> \* pre\_req() must always be followed by a
> post\_req().   
> \* To undo a call made to pre\_req(), call post\_req() with   
> \* a
> nonzero err condition.   
> \*/   
> void (\*post\_req)(struct mmc\_host \*host,
> struct mmc\_request \*req,   
> int err);   
> void
> (\*pre\_req)(struct mmc\_host \*host, struct mmc\_request \*req,   
> bool is\_first\_req);   
> void (\*request)(struct
> mmc\_host \*host, struct mmc\_request \*req);

pre\_req和post\_req是非必需的，host driver可以利用它们实现诸如双buffer之类的高级功能。

数据传输的主题是struct mmc\_request类型的指针，具体可参考3.7小节的介绍。

2）总线参数的配置以及卡状态的获取函数

> /\*   
> \* Avoid calling these three functions too often or in a "fast path",   
> \* since underlaying controller might implement them in an expensive   
> \*
> and/or slow way.   
> \*   
> \* Also note that these functions might sleep, so
> don't call them   
> \* in the atomic contexts!   
> \*   
> \* Return values for the
> get\_ro callback should be:   
> \* 0 for a read/write card   
> \* 1 for a
> read-only card   
> \* -ENOSYS when not supported (equal to NULL callback)   
> \* or a negative errno value when something bad happened   
> \*   
> \* Return
> values for the get\_cd callback should be:   
> \* 0 for a absent card   
> \* 1
> for a present card   
> \* -ENOSYS when not supported (equal to NULL callback)   
> \* or a negative errno value when something bad happened   
> \*/   
> void
> (\*set\_ios)(struct mmc\_host \*host, struct mmc\_ios \*ios);   
> int
> (\*get\_ro)(struct mmc\_host \*host);   
> int (\*get\_cd)(struct mmc\_host \*host);

set\_ios用于设置bus的参数（ios，可参考3.5小节的介绍）；get\_ro可获取card的读写状态（具体可参考上面的注释）；get\_cd用于检测卡的存在状态。

注4：注释中特别说明了，这几个函数可以sleep，耗时较长，没事别乱用。

3）其它一些非主流函数，都是optional的，用到的时候再去细看即可。

#### 3.3 struct mmc\_pwrseq

MMC framework的power sequence是一个比较有意思的功能，它提供一个名称为struct
mmc\_pwrseq\_ops的操作函数集，集合了power on、power off等操作函数，用于控制MMC系统的供电，如下：

> struct mmc\_pwrseq\_ops {   
> void (\*pre\_power\_on)(struct mmc\_host
> \*host);   
> void (\*post\_power\_on)(struct mmc\_host \*host);   
> void (\*power\_off)(struct mmc\_host \*host);   
> void (\*free)(struct
> mmc\_host \*host);   
> };
>
> struct mmc\_pwrseq {   
> const struct mmc\_pwrseq\_ops \*ops;   
> };

与此同时，MMC
core提供了一个通用的pwrseq的管理模块（drivers/mmc/core/pwrseq.c），以及一些简单的pwrseq策略（如drivers/mmc/core/pwrseq\_simple.c、drivers/mmc/core/pwrseq\_emmc.c），最终的目的是，通过一些简单的dts配置，即可正确配置MMC的供电，例如：

> /\* arch/arm/boot/dts/omap3-igep0020.dts \*/   
> mmc2\_pwrseq: mmc2\_pwrseq {   
> compatible = "mmc-pwrseq-simple";   
> reset-gpios =
> <&gpio5 11 GPIO\_ACTIVE\_LOW>, /\* gpio\_139 - RESET\_N\_W \*/   
> <&gpio5 10 GPIO\_ACTIVE\_LOW>; /\*
> gpio\_138 - WIFI\_PDN \*/   
> };
>
> /\* arch/arm/boot/dts/rk3288-veyron.dtsi \*/   
> emmc\_pwrseq: emmc-pwrseq {   
> compatible = "mmc-pwrseq-emmc";   
> pinctrl-0 =
> <&emmc\_reset>;   
> pinctrl-names = "default";   
> reset-gpios = <&gpio2 9 GPIO\_ACTIVE\_HIGH>;   
> };

具体的细节，在需要的时候，阅读代码即可，这里不再赘述。

#### 3.4 Host capabilities

通过的caps和caps2两个字段，MMC host driver可以告诉MMC
core控制器的一些特性、能力，包括（具体可参考include/linux/mmc/host.h中相关的宏定义，更为细致的使用场景和指南，需要结合实际的硬件，具体分析）：

> MMC\_CAP\_4\_BIT\_DATA，支持4-bit的总线传输；   
> MMC\_CAP\_MMC\_HIGHSPEED，支持“高速MMC时序”；   
> MMC\_CAP\_SD\_HIGHSPEED，支持“高速SD时序”；   
> MMC\_CAP\_SDIO\_IRQ，可以产生SDIO有关的中断；   
> MMC\_CAP\_SPI，仅仅支持SPI协议（可参考“drivers/mmc/host/mmc\_spi.c”中有关的实现）；   
> MMC\_CAP\_NEEDS\_POLL，表明需要不停的查询卡的插入状态（如果需要支持热拔插的卡，则需要设置该feature）；   
> MMC\_CAP\_8\_BIT\_DATA，支持8-bit的总线传输；   
> MMC\_CAP\_AGGRESSIVE\_PM，支持比较积极的电源管理策略（kernel的注释为“Suspend (e)MMC/SD at idle”）；   
> MMC\_CAP\_NONREMOVABLE，表明该MMC控制器所连接的卡是不可拆卸的，例如eMMC；   
> MMC\_CAP\_WAIT\_WHILE\_BUSY，表面Host controller在向卡发送命令时，如果卡处于busy状态，是否等待。如果不等待，MMC
> core在一些流程中（如查询busy状态），需要额外做一些处理；   
> MMC\_CAP\_ERASE，表明该MMC控制器允许执行擦除命令；   
> MMC\_CAP\_1\_8V\_DDR，支持工作电压为1.8v的DDR（Double Data Rate）mode[3]；   
> MMC\_CAP\_1\_2V\_DDR，支持工作电压为1.2v的DDR（Double Data Rate）mode[3]；   
> MMC\_CAP\_POWER\_OFF\_CARD，可以在启动之后，关闭卡的供电（一般只有在SDIO的应用场景中才可能用到，因为SDIO所连接的设备可能是一个独立的设备）；   
> MMC\_CAP\_BUS\_WIDTH\_TEST，支持通过CMD14和CMD19进行总线宽度的测试，以便选择一个合适的总线宽度进行通信；   
> MMC\_CAP\_UHS\_SDR12、MMC\_CAP\_UHS\_SDR25、MMC\_CAP\_UHS\_SDR50、MMC\_CAP\_UHS\_SDR104，它们是SD3.0的速率模式，分别表示支持25MHz、50MHz、100MHz和208MHz的SDR（Single
> Data Rate，相对[3]中的DDR）模式；   
> MMC\_CAP\_UHS\_DDR50，它也是SD3.0的速率模式，表示支持50MHz的DDR（Double Data
> Rate[3]）模式；   
> MMC\_CAP\_DRIVER\_TYPE\_A、MMC\_CAP\_DRIVER\_TYPE\_C、MMC\_CAP\_DRIVER\_TYPE\_D，分别表示支持A/C/D类型的driver
> strength（驱动能力，具体可参考相应的spec）；   
> MMC\_CAP\_CMD23，表示该controller支持multiblock
> transfers（通过CMD23）；   
> MMC\_CAP\_HW\_RESET，支持硬件reset；
>
> MMC\_CAP2\_FULL\_PWR\_CYCLE，表示该controller支持从power off到power on的完整的power cycle；   
> MMC\_CAP2\_HS200\_1\_8V\_SDR、MMC\_CAP2\_HS200\_1\_2V\_SDR，HS200是eMMC5.0支持的一种速率模式，200是200MHz的缩写，分别表示支持1.8v和1.2v的SDR模式；   
> MMC\_CAP2\_HS200，表示同时支持MMC\_CAP2\_HS200\_1\_8V\_SDR和MMC\_CAP2\_HS200\_1\_2V\_SDR；   
> MMC\_CAP2\_HC\_ERASE\_SZ，支持High-capacity erase size；   
> MMC\_CAP2\_CD\_ACTIVE\_HIGH，CD（Card-detect）信号高有效；   
> MMC\_CAP2\_RO\_ACTIVE\_HIGH，RO（Write-protect）信号高有效；   
> MMC\_CAP2\_PACKED\_RD、MMC\_CAP2\_PACKED\_WR，允许packed read、packed write；   
> MMC\_CAP2\_PACKED\_CMD，同时支持DMMC\_CAP2\_PACKED\_RD和MMC\_CAP2\_PACKED\_WR；   
> MMC\_CAP2\_NO\_PRESCAN\_POWERUP，在scan之前不要上电；   
> MMC\_CAP2\_HS400\_1\_8V、MMC\_CAP2\_HS400\_1\_2V，HS400是eMMC5.0支持的一种速率模式，400是400MHz的缩写，分别表示支持1.8v和1.2v的HS400模式；   
> MMC\_CAP2\_HS400，同时支持MMC\_CAP2\_HS400\_1\_8V和MMC\_CAP2\_HS400\_1\_2V；   
> MMC\_CAP2\_HSX00\_1\_2V，同时支持MMC\_CAP2\_HS200\_1\_2V\_SDR和MMC\_CAP2\_HS400\_1\_2V；   
> MMC\_CAP2\_SDIO\_IRQ\_NOTHREAD，SDIO的IRQ的处理函数，不能在线程里面执行；   
> MMC\_CAP2\_NO\_WRITE\_PROTECT，没有物理的RO管脚，意味着任何时候都是可以读写的；   
> MMC\_CAP2\_NO\_SDIO，在初始化的时候，不会发送SDIO相关的命令（也就是说不支持SDIO模式）。

#### 3.5 struct mmc\_ios

struct mmc\_ios中保存了MMC总线当前的配置情况，包括如下信息：

1）clock，时钟频率。

2）vdd，卡的供电电压，通过“1 <<
vdd”可以得到MMC\_VDD\_x\_x（具体可参考include/linux/mmc/host.h中MMC\_VDD\_开头的定义），进而得到电压信息。

3）bus\_mode，两种信号模式，open-drain（MMC\_BUSMODE\_OPENDRAIN）和push-pull（MMC\_BUSMODE\_PUSHPULL），对应不同的高低电平（可参考相应的spec，例如[2]）。

4）chip\_select，只针对SPI模式，指定片选信号的有效模式，包括没有片选信号（MMC\_CS\_DONTCARE）、高电平有效（MMC\_CS\_HIGH）、低电平有效（MMC\_CS\_LOW）。

5）power\_mode，当前的电源状态，包括MMC\_POWER\_OFF、MMC\_POWER\_UP、MMC\_POWER\_ON和MMC\_POWER\_UNDEFINED。

6）bus\_width，总线的宽度，包括1-bit（MMC\_BUS\_WIDTH\_1）、4-bit（MMC\_BUS\_WIDTH\_4）和8-bit（MMC\_BUS\_WIDTH\_8）。

7）timing，符合哪一种总线时序（大多对应某一类MMC规范），包括：

> MMC\_TIMING\_LEGACY，旧的、不再使用的规范；   
> MMC\_TIMING\_MMC\_HS，High speed
> MMC规范（具体可参考相应的spec，这里不再详细介绍，下同）；   
> MMC\_TIMING\_SD\_HS，High speed SD；   
> MMC\_TIMING\_UHS\_SDR12；   
> MMC\_TIMING\_UHS\_SDR25   
> MMC\_TIMING\_UHS\_SDR50   
> MMC\_TIMING\_UHS\_SDR104   
> MMC\_TIMING\_UHS\_DDR50   
> MMC\_TIMING\_MMC\_DDR52   
> MMC\_TIMING\_MMC\_HS200   
> MMC\_TIMING\_MMC\_HS400

8）signal\_voltage，总线信号使用哪一种电压，3.3v（MMC\_SIGNAL\_VOLTAGE\_330）、1.8v（MMC\_SIGNAL\_VOLTAGE\_180）或者1.2v（MMC\_SIGNAL\_VOLTAGE\_120）。

9）drv\_type，驱动能力，包括：

> MMC\_SET\_DRIVER\_TYPE\_B   
> MMC\_SET\_DRIVER\_TYPE\_A   
> MMC\_SET\_DRIVER\_TYPE\_C   
> MMC\_SET\_DRIVER\_TYPE\_D

#### 3.6 struct mmc\_supply

struct mmc\_supply中保存了两个struct
regulator指针（如下），用于控制MMC子系统有关的供电（vmmc和vqmmc）。

> struct mmc\_supply {   
> struct regulator \*vmmc; /\* Card power
> supply \*/   
> struct regulator \*vqmmc; /\* Optional Vccq supply \*/   
> };

关于vmmc和vqmmc，说明如下：

> vmmc是卡的供电电压，一般连接到卡的VDD管脚上。而vqmmc则用于上拉信号线（CMD、CLK和DATA[6]）。
>
> 通常情况下vqmmc使用和vmmc相同的regulator，同时供电即可。
>
> 后来，一些高速卡（例如UHS
> SD）要求在高速模式下，vmmc为3.3v，vqmmc为1.8v，这就需要两个不同的regulator独立控制。

#### 3.7 struct mmc\_request

struct mmc\_request封装了一次传输请求，定义如下：

> /\* include/linux/mmc/core.h \*/
>
> struct mmc\_request {   
> struct mmc\_command \*sbc; /\*
> SET\_BLOCK\_COUNT for multiblock \*/   
> struct mmc\_command \*cmd;   
> struct mmc\_data \*data;   
> struct mmc\_command
> \*stop;
>
> struct completion completion;   
> void (\*done)(struct mmc\_request \*);/\* completion function \*/   
> struct mmc\_host \*host;   
> };

要理解这个数据结构，需要先了解MMC的总线协议（bus
protocol），这里以eMMC[2]为例进行简单的介绍（更为详细的解释，可参考相应的spec以及本站的文章--“[eMMC 原理 4
：总线协议](/basic_tech/emmc_bus_protocol.html)[7]”）。

**3.7.1 MMC bus protocol**

在eMMC的spec中，称总线协议为“message-based MultiMediaCard bus
protocol”，这里的message由三种信标（token）组成：

> Command，用于启动（或者停止）一次传输，由Host通过CMD
> line向Card发送；
>
> Response，用于应答上一次的Command，由Card通过CMD line想Host发送；
>
> Data，传输数据，由Host（或者Card）通过DATA lines向Card（或者Host发送）。

以上token除了Command之外，剩余的两个（Response和Data）都是非必需的，也就是说，一次传输可以是：不需要应答、不需要数据传输的Command；需要应答、不需要数据传输的Command；不需要应答、需要数据传输的Command；不需要应答、不需要数据传输的Command。

Command token的格式只有一种（具体可参考[2]中“Command token format”有关的表述），长度为48bits，包括Start
bit(0)、Transmitter bit(1, host command)、Content(38bits)、CRC checksum(7bits)、Stop
bit(1)。

根据内容的不同，Response
token的格式有5中，分别简称为R1/R3/R4/R5/R2，其中R1/R3/R4/R5的长度为48bits，R2为136bits（具体可参考[2]中“Response
token format”有关的表述）。

对于包含了Data token的Command，有两种类型：

> Sequential commands，发送Start command之后，数据以stream的形式传输，直到Stop
> command为止。这种方式只支持1-bit总线模式，主要为了兼容旧的技术，一般不使用；
>
> Block-oriented commands，发送Start
> command之后，数据以block的形式传输（每个block的大小是固定的，且都由CRC保护）。

最后，以block为单位的传输，大体上也分为两类：

> 在传输开始的时候（Start command），没有指定需要传输的block数目，直到发送Stop
> command为止。这种方法在spec中称作“Open-ended”；
>
> 在传输开始的时候（Start command），指定需要传输的block数据，当达到数据之后，Card会自动停止传输，这样可以省略Stop
> command。这种方法在spec中称作pre-defined block count。

**3.7.2 struct mmc\_request**

了解MMC bus protocol之后，再来看一次MMC传输请求（struct mmc\_request ）所包含的内容：

> cmd，Start command，为struct
> mmc\_command类型（具体请参考3.7.3中的介绍）的指针，在一次传输的过程中是必须的；
>
> data，传输的数据，为struct mmc\_data类型（具体请参考3.7.4中的介绍）的指针，不是必须要的；
>
> stop、sbc，如果需要进行数据传输，根据数据传输的方式（参考3.7.1中的介绍）：如果是“Open-ended”，则需要stop命令（stop指针，或者data->stop指针）；如果是pre-defined
> block count，则需要sbc指针（用于发送SET\_BLOCK\_COUNT--CMD23命令）；
>
> completion，一个struct completion变量，用于等待此次传输完成，host controller
> driver可以根据需要使用；
>
> done，传输完成时的回调，用于通知传输请求的发起者；
>
> host，对应的mmc host controller指针。

**3.7.3 struct mmc\_command**

struct mmc\_command结构抽象了一个MMC command，包括如下内容：

> /\* include/linux/mmc/core.h
> \*/
>
> opcode，Command的操作码，用于标识该命令是哪一个命令，具体可参考相应的spec（例如[2]）；
>
> arg，一个Command可能会携带参数，具体可参考相应的spec（例如[2]）；
>
> resp[4]，Command发出后，如果需要应答，结果保存在resp数组中，该数组是32-bit的，因此最多可以保存128bits的应答；
>
> flags，是一个bitmap，保存该命令所期望的应答类型，例如：   
> MMC\_RSP\_PRESENT（1 <<
> 0)，是否需要应答，如果该bit为0，则表示该命令不需要应答，否则，需要应答；   
> MMC\_RSP\_136（1 <<
> 1），如果为1，表示需要136bits的应答；   
> MMC\_RSP\_CRC（1 << 2），如果为1，表示需要对该命令进行CRC校验；   
> 等等，具体可参考include/linux/mmc/core.h中“MMC\_RSP\_”开头的定义；
>
> retries，如果命令发送出错，可以重新发送，该字段向host driver指明最多可重发的次数；
>
> error，如果最终还是出错，host
> driver需要通过该字段返回错误的原因，kernel定义了一些标准错误，例如ETIMEDOUT、EILSEQ、EINVAL、ENOMEDIUM等，具体含义可参考include/linux/mmc/core.h中注释；
>
> busy\_timeout，如果card具有busy检测的功能，该字段指定等待card返回busy状态的超时时间，单位为ms；
>
> data，和该命令对应的struct mmc\_data指针；
>
> mrq，和该命令对应的struct mmc\_request指针。

**3.7.4 struct mmc\_data**

struct mmc\_data结构包含了数据传输有关的内容：

> /\* include/linux/mmc/core.h \*/
>
> timeout\_ns、timeout\_clks，这一笔数据传输的超时时间（单位分别为ns和clks），如果超过这个时间host
> driver还无法成功发送，则要将状态返回给mmc core；
>
> blksz、blocks，该笔数据包含多少block（blocks），每个block的size多大（blksz），这两个值不会大于struct
> mmc\_host中上报的max\_blk\_size和max\_blk\_count；
>
> error，如果数据传输出错，错误值保存在该字段，具体意义和struct mmc\_command中的一致；
>
> flags，一个bitmap，指明该笔传说的方向（MMC\_DATA\_WRITE或者MMC\_DATA\_READ）；
>
> sg，一个struct scatterlist类型的数组，保存了需要传输的数据（可以通过dma\_相关的接口，获得相应的物理地址）；   
> sg\_len，sg数组的size；   
> sg\_count，通过sg
> map出来的实际的entry的个数（可能由于物理地址的连续、IOMMU的干涉等，map出来的entry的个数，可能会小于sg的size）；   
> 注5：有关scatterlist的介绍，可参考本站另外的文章（TODO）。有关struct
> mmc\_data的使用场景，可参考5.2小节的介绍；
>
> host\_cookie，host driver的私有数据，怎么用由host driver自行决定。

## 4. 主要API

第3章花了很大的篇幅介绍了用于抽象MMC host的数据结构----struct mmc\_host，并详细说明了和mmc\_host相关的mmc
request、mmc command、mmc data等结构。基于这些知识，本章将介绍MMC core提供的和struct
mmc\_host有关的操作函数，主要包括如下几类。

#### 4.1 向MMC host controller driver提供的用于操作struct mmc\_host的API

包括：

|  |
| --- |
| struct mmc\_host \*mmc\_alloc\_host(int extra, struct device \*);    int mmc\_add\_host(struct mmc\_host \*);    void mmc\_remove\_host(struct mmc\_host \*);    void mmc\_free\_host(struct mmc\_host \*);    int mmc\_of\_parse(struct mmc\_host \*host);    static inline void \*mmc\_priv(struct mmc\_host \*host) {    return (void \*)host->private;    } |

> mmc\_alloc\_host，动态分配一个struct
> mmc\_host变量。extra是私有数据的大小，可通过host->private指针访问（也可通过mmc\_priv接口直接获取）。mmc\_free\_host执行相反动作。
>
> mmc\_add\_host，将已初始化好的host变量注册到kernel中。mmc\_remove\_host执行相反动作。
>
> 为了方便，host controller
> driver可以在dts中定义host的各种特性，然后在代码中调用mmc\_of\_parse解析并填充到struct
> mmc\_host变量中。dts属性关键字可参考mmc\_of\_parse的source
> code（drivers/mmc/core/host.c），并结合第三章的内容自行理解。

|  |
| --- |
| int mmc\_power\_save\_host(struct mmc\_host \*host);    int mmc\_power\_restore\_host(struct mmc\_host \*host); |

> 从mmc host的角度进行电源管理，进入/退出power save状态。

|  |
| --- |
| void mmc\_detect\_change(struct mmc\_host \*, unsigned long delay); |

> 当host driver检测到总线上的设备有变动的话（例如卡的插入和拔出等），需要调用这个接口，让MMC
> core帮忙做后续的工作，例如检测新插入的卡到底是个什么东东……
>
> 另外，可以通过delay参数告诉MMC
> core延时多久（单位为jiffies）开始处理，通常可以用来对卡的拔插进行去抖动。

|  |
| --- |
| void mmc\_request\_done(struct mmc\_host \*, struct mmc\_request \*); |

> 当host driver处理完成一个mmc request之后,需要调用该函数通知MMC core，MMC
> core会进行一些善后的操作，例如校验结果、调用mmc request的.done回调等等。

|  |
| --- |
| static inline void mmc\_signal\_sdio\_irq(struct mmc\_host \*host)    void sdio\_run\_irqs(struct mmc\_host \*host); |

> 对于SDIO类型的总线，这两个函数用于操作SDIO irqs，后面用到的时候再分析。

|  |
| --- |
| int mmc\_regulator\_get\_ocrmask(struct regulator \*supply);    int mmc\_regulator\_set\_ocr(struct mmc\_host \*mmc,    struct regulator \*supply,    unsigned short vdd\_bit);    int mmc\_regulator\_set\_vqmmc(struct mmc\_host \*mmc, struct mmc\_ios \*ios);    int mmc\_regulator\_get\_supply(struct mmc\_host \*mmc); |

> regulator有关的辅助函数：
>
> mmc\_regulator\_get\_ocrmask可根据传入的regulator指针，获取该regulator支持的所有电压值，并以此推导出对应的ocr
> mask（可参考3.1中的介绍）。
>
> mmc\_regulator\_set\_ocr用于设置host controller为某一个操作电压（vdd\_bit），该接口会调用regulator
> framework的API，进行具体的电压切换。
>
> mmc\_regulator\_set\_vqmmc可根据struct mmc\_ios信息，自行调用regulator
> framework的接口，设置vqmmc的电压。
>
> 最后，mmc\_regulator\_get\_supply可以帮忙从dts的vmmc、vqmmc属性值中，解析出对应的regulator指针，以便后面使用。

#### 4.2 用于判断MMC host controller所具备的能力的API

比较简单，可结合第3章的介绍理解：

|  |
| --- |
| #define mmc\_host\_is\_spi(host) ((host)->caps & MMC\_CAP\_SPI)    static inline int mmc\_card\_is\_removable(struct mmc\_host \*host)    static inline int mmc\_card\_keep\_power(struct mmc\_host \*host)    static inline int mmc\_card\_wake\_sdio\_irq(struct mmc\_host \*host)    static inline int mmc\_host\_cmd23(struct mmc\_host \*host)    static inline int mmc\_boot\_partition\_access(struct mmc\_host \*host)    static inline int mmc\_host\_uhs(struct mmc\_host \*host)    static inline int mmc\_host\_packed\_wr(struct mmc\_host \*host)    static inline int mmc\_card\_hs(struct mmc\_card \*card)    static inline int mmc\_card\_uhs(struct mmc\_card \*card)    static inline bool mmc\_card\_hs200(struct mmc\_card \*card)    static inline bool mmc\_card\_ddr52(struct mmc\_card \*card)    static inline bool mmc\_card\_hs400(struct mmc\_card \*card)    static inline void mmc\_retune\_needed(struct mmc\_host \*host)    static inline void mmc\_retune\_recheck(struct mmc\_host \*host) |

## 5. MMC host驱动的编写步骤

经过上面章节的描述，相信大家对MMC controller
driver有了比较深的理解，接下来驱动的编写就是一件水到渠成的事情了。这里简要描述一下驱动编写步骤，也顺便为本文做一个总结。

#### 5.1 struct mmc\_host的填充和注册

编写MMC host驱动的所有工作，都是围绕struct mmc\_host结构展开的。在对应的platform
driver的probe函数中，通过mmc\_alloc\_host分配一个mmc host后，我们需要根据controller的实际情况，填充对应的字段。

mmc
host中大部分和controller能力/特性有关的字段，可以通过dts配置（然后在代码中调用mmc\_of\_parse自动解析并填充），举例如下（注意其中红色的部分，都是MMC
framework的标准字段）：

> /\* arch/arm/boot/dts/exynos5420-peach-pit.dts \*/
>
> &mmc\_1 {   
> status = "okay";   
> num-slots = <1>;   
> non-removable;   
> cap-sdio-irq;  
> keep-power-in-suspend;   
> clock-frequency = <400000000>;  
> samsung,dw-mshc-ciu-div = <1>;   
> samsung,dw-mshc-sdr-timing = <0 1>;   
> samsung,dw-mshc-ddr-timing
> = <0 2>;   
> pinctrl-names = "default";   
> pinctrl-0 =
> <&sd1\_clk>, <&sd1\_cmd>, <&sd1\_int>,
> <&sd1\_bus1>,   
> <&sd1\_bus4>,
> <&sd1\_bus8>, <&wifi\_en>;   
> bus-width = <4>;  
> cap-sd-highspeed;  
> mmc-pwrseq =
> <&mmc1\_pwrseq>;  
> vqmmc-supply = <&buck10\_reg>;   
> };

#### 5.2 数据传输的实现

填充struct mmc\_host变量的过程中，工作量最大的，就是对struct mmc\_host\_ops的实现（毫无疑问！所有MMC
host的操作逻辑都封在这里呢！！）。这里简单介绍一下相关的概念，具体的驱动编写步骤，后面文章会结合“[X Project](/sort/x_project)”详细描述。

**5.2.1 Sectors（扇区）、Blocks（块）以及Segments（段）的理解**

我们在3.1小节介绍struct
mmc\_host的时候，提到了max\_seg\_size、max\_segs、max\_req\_size、max\_blk\_size、max\_blk\_count等参数。这和磁盘设备（块设备）中Sectors、Blocks、Segments等概念有关，下面简单介绍一下：

1）Sectors

> Sectors是存储设备访问的基本单位。
>
> 对磁盘、NAND等块设备来说，Sector的size是固定的，例如512、2048等。
>
> 对存储类的MMC设备来说，按理说也应有固定size的sector。但因为有MMC协议的封装，host驱动以及上面的块设备驱动，不需要关注物理的size。它们需要关注的就是bus上的数据传输单位（具体可参考MMC
> protocol的介绍[7]）。
>
> 最后，对那些非存储类的MMC设备来说，完全没有sector的概念了。

2） Blocks

> Blocks是数据传输的基本单位，是VFS（虚拟文件系统）抽象出来的概念，是纯软件的概念，和硬件无关。它必须是2的整数倍、不能大于Sectors的单位、不能大于page的长度，一般为512B、2048B或者4096B。
>
> 对MMC设备来说，由于协议的封装，淡化了Sector的概念，或者说，MMC设备可以支持一定范围内的任意的Block size。Block
> size的范围，由两个因素决定：   
> a）host controller的能力，这反映在struct mmc\_host结构的max\_blk\_size字段上。   
> b）卡的能力，这可以通过MMC command从卡的CSD（Card-Specific Data）寄存器中读出。

3）Segments[8]

> 块设备的数据传输，本质上是设备上相邻扇区与内存之间的数据传输。通常情况下，为了提升性能，数据传输通过DMA方式。
>
> 在磁盘控制器的旧时代，DMA操作都比较简单，每次传输，数据在内存中必须是连续的。现在则不同，很多SOC都支持“分散/聚合”（scatter-gather）DMA操作，这种操作模式下，数据传输可以在多个非连续的内存区域中进行。
>
> 对于每个“分散/聚合”DMA操作，块设备驱动需要向控制器发送：   
> a）初始扇区号和传输的总共扇区数   
> b）内存区域的描述链表，每个描述都包含一个地址和长度。不同的描述之间，可以在物理上连续，也可以不连续。
>
> 控制器来管理整个数据传输，例如：在读操作中，控制器从块设备相邻的扇区上读取数据，然后将数据分散存储在内存的不同区域。
>
> 这里的每个内存区域描述（物理连续的一段内存，可以是一个page，也可以是page的一部分），就称作Segment。一个Segment包含多个相邻扇区。
>
> 最后，利用“分散/聚合”的DMA操作，一次数据传输可以会涉及多个segments。

理解了Segment的概念之后，max\_seg\_size和max\_segs两个字段就好理解了：

> 虽然控制器支持“分散/聚合”的DMA操作，但物理硬件总有限制，例如最大的Segment
> size（也即一个内存描述的最大长度），最多支持的segment个数（max\_segs）等。

**5.2.2 struct mmc\_data中的sg**

我们在3.7.4小节介绍struct mmc\_data时，提到了scatterlist的概念。结合上面Segment的解释，就很好理解了：

> MMC core提交给MMC host
> driver的数据传输请求，是一个struct
> scatterlist链表（也即内存区域的描述链表），也可以理解为是一个个的Segment（Segment的个数保存在sg\_len变量中了）。
>
> 每个Segment是一段物理地址连续的内存区域，所有的Segments对应了MMC设备中连续的Sector（或者说Block，初始扇区号和传输的总共扇区数已经在之前的MMC
> command中指定了。
>
> host driver在接收到这样的数据传输请求之后，需要调用dma\_map\_sg将这些Segment映射出来（获得相应的物理地址），以便交给MMC
> controller传输。
>
> 当然，相邻两个Segment的物理地址可能是连续（或者其它原因），map的时候可能会将两个Segment合成一个。因此可供MMC
> controller传输的内存片可能少于sg\_len（具体要看dma\_map\_sg的返回值，可将结果保存在sg\_count中）。
>
> 最后，如何实施传输，则要看具体的MMC controller的硬件实现（可能涉及DMA操作），后面文章再详细介绍。

## 6. 参考文档

[1] [SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/Schematics_Bubblegum96.pdf)

[2] [JESD84-A44.pdf](http://rere.qmqm.pl/~mirq/JESD84-A44.pdf)

[3] DDR mode, [https://en.wikipedia.org/wiki/Double\_data\_rate](https://en.wikipedia.org/wiki/Double_data_rate "https://en.wikipedia.org/wiki/Double_data_rate")

[4] [http://www.hjreggel.net/cardspeed/cs\_sdxc.html](http://www.hjreggel.net/cardspeed/cs_sdxc.html "http://www.hjreggel.net/cardspeed/cs_sdxc.html")

[5] regulator framework，[/tag/regulator](/tag/regulator "/tag/regulator")

[6] [MMC/SD/SDIO介绍](/basic_tech/mmc_sd_sdio_intro.html)

[7] [eMMC
原理 4 ：总线协议](/basic_tech/emmc_bus_protocol.html)

[8] [http://www.ilinuxkernel.com/files/Linux.Generic.Block.Layer.pdf](http://www.ilinuxkernel.com/files/Linux.Generic.Block.Layer.pdf "http://www.ilinuxkernel.com/files/Linux.Generic.Block.Layer.pdf")

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/mmc_host_driver.html)。
