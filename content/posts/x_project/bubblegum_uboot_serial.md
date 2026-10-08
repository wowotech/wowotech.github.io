---
title: "X-004-UBOOT-串口驱动移植(Bubblegum-96平台)"
date: 2016-06-18T09:56:02+08:00
url: "/x_project/bubblegum_uboot_serial.html"
gid: "312"
emlog_type: "blog"
summary: "\r\n\t话说现在的u-boot长得和linux kernel越来越像，设备模型（driver model）、device \r\ntree、各种framework（gpio、pinctrl、clock、i2c、regulator、等等），各种概念，均和linux \r\nkernel保持一致。这对工程师（特别是linux驱动工程师）来说，是一个利好，因为熟悉了linux \r\nkernel相关子系统之后，去搞"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["uart", "x", "project", "u-boot", "uboot", "porting", "serial"]
views: 16655
comment_count: 10
aliases:
  - "/x_project/312.html"
  - "/312.html"
---

#### 1. 前言

话说现在的u-boot长得和linux kernel越来越像，设备模型（driver model）、device tree、各种framework（gpio、pinctrl、clock、i2c、regulator、等等），各种概念，均和linux kernel保持一致。这对工程师（特别是linux驱动工程师）来说，是一个利好，因为熟悉了linux kernel相关子系统之后，去搞u-boot基本上就毫无压力了。

不过，对“蜗窝”来说，压力（或者说矛盾）就来了：要不要为u-boot中相关的子系统写分析文章？写吧，实在提不起兴趣，毕竟和kernel类似，我们的重点又在kernel分析上。不写吧，不符合我们的风格啊！

最后，鉴于时间的压力，只能选一个折衷方案：

> 对于“[X Project](/forum/)” u-boot移植过程所涉及的driver模块，只写一篇移植说明，至于其它的，只能战略性放弃（当然，如果有同学有兴趣帮忙补上，我们还是很欢迎的）。

本文是这类文章的第一篇，介绍串口驱动（serial driver）的移植过程。因为u-boot跑起来之后，第一件事就是要把串口输出（console）准备好，以便后续模块的debug。

#### 2. 硬件信息汇整

老规矩，编写设备驱动之前，我们需要罗列该设备和软件有关的硬件信息，这次以问答（当然是自问自答）的形式吧。问题如下：

> 板子上有哪些串口资源，对外的连接方式如何？
>
> 每个串口都有哪些信号，这些信号连接到CPU的哪些管脚上了，管脚的复用情况如何，使用哪些寄存器控制？
>
> 串口控制器的power、clock、reset等资源是否可以单独控制，相应的子系统是否已经提供标准的控制接口了，如果没有，由哪些寄存器控制？
>
> 串口控制器的寄存器说明，主要包括数据位、校验位、停止位、流控等信息的控制，数据的收发等。

下面我们将分节解答以上问题。

注1：为了节省篇幅，我尽可能的直接给出结论，具体的推导过程，大家可以根据自己板子实际情况，自行揣摩。

注2：u-boot中的串口，主要用作控制台，因此本文只会介绍和控制台相关的串口信息，其它的，大家触类旁通即可。

##### 2.1 板子上有哪些串口资源，对外的连接方式如何？

由“Bubblegum 96boards硬件手册[2]”和“Bubblegum 96boards原理图[3]”的描述可知，Bubblegum-96开发板上有两个串口可用于控制台输出：

1）UART5

> 位于J2（一个40pin的双排插座）上，pin11和pin13分别是TX和RX（相对于CPU来说）；
>
> 直接和S900 CPU连接，电平是1.8v；
>
> 由于UART接口的工作电平是3.3v，因此要使用特殊的串口子板进行电平转换后，才能通过串口线和PC连接。因此，通常的连接方式是：   
> S900<-------->串口子板(1.8/3.3转换)<-------->USB转串口<-------->PC(USB接口)   
> 或者   
> S900<-------->串口子板(1.8/3.3转换)<-------->电平转换接口(3.3/5转换)<-------->串口线<-------->PC

具体的连接图片，以及串口子板的使用方法，我就不在这里列出了。

2）UART2

> 额外的UART测试点，包括3V、TX、RX、GND 4个信号，位于板子的USB接口旁边；
>
> 由于只有测试点，需要动下手，焊接一些测试用的PIN脚；
>
> 已经包含了1.8/3.3转换电路，不再需要串口子板。因此通常的连接方式是：   
> S900<-------->USB转串口<-------->PC(USB接口)   
> 或者   
> S900<-------->电平转换接口(3.3/5转换)<-------->串口线<-------->PC

由于开发板都配置了串口子板，因此UART2接口可以暂时忽略。

##### 2.2 每个串口都有哪些信号，这些信号连接到CPU的哪些管脚上了，管脚的复用情况如何，使用哪些寄存器控制？

由“Bubblegum 96boards原理图[3]“可知：

> UART5的两个信号名称为“GPIOA25/UART5\_RX”和“GPIOA27/UART5\_TX”，分别连接到S900的A7和D8两个管脚上。这两个管脚在原理图中的名称分别为“GPIOA25/UART5\_RX/SENS0\_VSYNC/PWM2”和“GPIOA27/UART5\_TX/SENS0\_HSYNC/PWM2”，说明它们和GPIOA25、GPIOA27、SENS0\_VSYNC、SENS0\_HSYNC、PWM2等功能复用。
>
> UART2的两个信号名称为“GPIO\_UART2\_RX”和“GPIO\_UART2\_TX”，经过一个电平转换芯片，分别连接到S900的B22和A22两个管脚上。这两个管脚在原理图中的名称分别为“GPIOD0/UART2\_RX/OEP”和“GPIOD1/UART2\_TX/OEN”，说明它们和GPIOD0、GPIOD1、OEP、OEN等功能复用。

然后参考“S900 IC Spec[1]”，可以知道，上面UART5和UART2的管脚复用都可以通过MFP\_CTL1（0xE01B0044）寄存器控制：

> MFP\_CTL1的bit25:23为100b时，使能UART5\_TX，MFP\_CTL1的bit28:26为001b时，使能UART5\_RX。
>
> MFP\_CTL1的bit22为1时，使能UART2\_TX和UART2\_RX。

##### 2.3 串口控制器的power、clock、reset等资源是否可以单独控制，相应的子系统是否已经提供标准的控制接口了，如果没有，由哪些寄存器控制？

从bubblegum-96公开发布的资料上，找不到任何关于clock、reset等信息。不过还好，我们可以从其kernel的source code中倒推，如下：

> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi") \*/
>
> ```
> 	serial2: uart@e0124000 {

> 		…

> 		clocks = <&clock CLK_UART2>;

> 		clock-names = "uart";

> 		resets = <&reset RESET_UART2>;

> 		…

> 	};
> ```
>
> ```
> 	serial5: uart@e012a000 {

> 		…

> 		clocks = <&clock CLK_UART5>;

> 		clock-names = "uart";

> 		resets = <&reset RESET_UART5>;

> 	};
> ```

可知：UART2的控制器，由RESET\_UART2控制reset，CLK\_UART2控制clock；UART5的控制器，由RESET\_UART5控制reset，CLK\_UART5控制clock。

结合如下三个文件中有关reset的定义：

> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi") \*/
>
> ```
> 	reset: reset-controller@e01600a8 {

> 		compatible = "actions,s900-reset";

> 		reg = <0 0="" 0xe01600a8="" 0x8="">;

> 		#reset-cells = <1>;

> 	};
> ```
>
> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/include/dt-bindings/reset/reset-s900.h](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/include/dt-bindings/reset/reset-s900.h "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/include/dt-bindings/reset/reset-s900.h") \*/
>
> ```
> #define RESET_UART2				39

> …

> #define RESET_UART5				49
> ```
>
> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/reset/reset-owl.c](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/reset/reset-owl.c "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/reset/reset-owl.c") \*/
>
> ```
> static int owl_clk_reset_assert(struct reset_controller_dev *rcdev,

> 			unsigned long id)

> {

> 	…

> 	reg = reset->base + (id / 32) * 4;

> 

> 	spin_lock_irqsave(&reset->lock, flags);

> 

> 	val = readl(reg);

> 	val &= ~BIT(id % 32);

> 	writel(val, reg);

> 

> 	…

> }
> ```

可知UART2和UART5的reset分别由0xe01600ac（0xe01600a8 + 0x4）的bit7和bit17控制，该寄存器的名称也称作CMU\_DEVRST1（可参考[https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c")中有关的定义）。

同时，结合如下三个文件有关clock的定义：

> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi") \*/
>
> ```
> 	clock: clock-controller@e0160000 {

> 		compatible = "actions,s900-clock";

> 		reg = <0 0="" 0xe0160000="" 0x1000="">;

> 		#clock-cells = <1>;

> 	};
> ```
>
> /\* [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/drivers/clk/owl/clk-s900.c") \*/
>
> ```
> static const char *uart_clk_mux_p[] __initdata = { "hosc", "dev_pll"};
> ```
>
> ```
> COMP_DIV_CLK(CLK_UART2, "uart2", 0,

> 	C_MUX(uart_clk_mux_p, CMU_UART2CLK, 16, 1, 0),

> 	C_GATE(CMU_DEVCLKEN1, 8, 0),

> 	C_DIVIDER(CMU_UART2CLK, 0, 8, NULL, CLK_DIVIDER_ROUND_CLOSEST)),
> ```
>
> ```
> COMP_DIV_CLK(CLK_UART5, "uart5", 0,

> 	C_MUX(uart_clk_mux_p, CMU_UART5CLK, 16, 1, 0),

> 	C_GATE(CMU_DEVCLKEN1, 21, 0),

> 	C_DIVIDER(CMU_UART5CLK, 0, 8, NULL, CLK_DIVIDER_ROUND_CLOSEST)),
> ```

可知：

> UART2和UART5的时钟源有两个：hosc和dev\_pll(uart\_clk\_mux\_p)，由CMU\_UART2CLK/CMU\_UART5CLK的bit16控制，0为hosc，1为dev\_pll；
>
> 由于u-boot中clock driver还没有做，为了简单，可以先使用hosc为时钟源，由“Bubblegum 96boards原理图[3]”的描述可知，HOSC的频率为24MHz；
>
> UART2和UART5的时钟大小，由CMU\_UART2CLK/CMU\_UART5CLK中的bit8:0控制，即：uart clock = clock source / ([bit8:0] + 1)；
>
> 最后，UART2和UART5控制器的clock，还可以通过CMU\_DEVCLKEN1寄存器的bit8和bit21开关；
>
> 以上涉及的寄存器地址分别为：   
> CMU\_DEVCLKEN1 0xE01600A4   
> CMU\_UART2CLK 0xE0160064   
> CMU\_UART5CLK 0xE01600B8

##### 2.4 串口控制器的寄存器说明，主要包括数据位、校验位、停止位、流控等信息的控制，数据的收发等

参考“S900 IC Spec[1]”，再结合“[https://github.com/96boards-bubblegum/u-boot/blob/bubblegum96-2015.07/drivers/serial/serial\_owl.c](https://github.com/96boards-bubblegum/u-boot/blob/bubblegum96-2015.07/drivers/serial/serial_owl.c "https://github.com/96boards-bubblegum/u-boot/blob/bubblegum96-2015.07/drivers/serial/serial_owl.c")”，可以得知：

> UART2和UART5的寄存器基址分别为UART2\_BASE(0xE0124000)和UART5\_BASE(0xE012a000)；
>
> UART\_CTL(0x0)可以控制串口的数据位(bit1:0)、校验位(bit6:4)、停止位(bit2)、流控(bit12)等信息；
>
> UART\_CTL(0x0)的bit15可以控制串口的使能；
>
> UART\_RXDAT(0x4)和UART\_TXDAT(0x8)可用于数据的收发；
>
> UART\_STAT(0xc)指示fifo的状态。

#### 3. 串口驱动的软件框架

移植开始之前，有必要先简单了解一下u-boot中串口驱动有关的软件框架，如下：

[![u-boot_serial_driver_architecture](/content/uploadfile/201606/73c84211f8a63899b1e9226e6712c3e720160618015928.gif "u-boot_serial_driver_architecture")](/content/uploadfile/201606/3e37412d48402458101d9968dcee3e1820160618015928.gif)

图片1 u-boot\_serial\_driver\_architecture

由上图可知：

> 对下，串口驱动依赖driver model、device tree、clock driver、pinctrl driver等基础模块。
>
> 对上，串口驱动向u-boot的console模块提供接口，进而为lib中的printf等提供接口。
>
> 另外，为了简化串口驱动的编写，u-boot将串口有关的共性实现，抽象出来并封装在serial uclass中，我们编写驱动的时候，只需要按照serial uclass的规则，填充执行的serial ops即可。具体可以参考后续的说明。

注3：写篇文章的时候，“[X Project](/forum/)”的u-boot仅仅完成了启动部分的移植，所有的基础模块都没有实现。因此，串口驱动的移植的过程中，所涉及到的基础操作，如clock、pinmux等，暂时只能通过寄存器操作代替。与此同时，device tree暂未支持，我们只能使用传统的driver、device注册方式。

#### 4. 串口驱动移植过程

##### 4.1 修改版型的配置文件，使u-boot可以正确启动

我们在“[【任务1】启动过程-Boot from USB](/forum/15.html)”中，以U-boot SPL为例，介绍并移植了基于SPL的启动过程。由于串口驱动没有必要在SPL中使用，所以我们需要比照SPL的移植过程，将u-boot run起来。

移植的过程比较简单，只需要修改“include/configs/bubblegum.h”中相应的配置项即可，具体过程和SPL类似，这里不再详细描述，感兴趣的同学可以参考这个patch：

> [https://github.com/wowotechX/u-boot/commit/f5f3d1c1a34dc9291838cfe7dbf97e5f0cba99b1](https://github.com/wowotechX/u-boot/commit/f5f3d1c1a34dc9291838cfe7dbf97e5f0cba99b1 "https://github.com/wowotechX/u-boot/commit/f5f3d1c1a34dc9291838cfe7dbf97e5f0cba99b1")

##### 4.2 在drivers/serial目录中，添加串口驱动

步骤如下：

> 1）在drivers/serial中创建serial\_owl.c文件（owl的命名是从bubblegum-96board的官方github[4]上抄来的,不太清楚原因，可以是SOC的系列名称，后续的driver开发，也会遵守该命名规范）。
>
> 2）修改drivers/serial/Kconfig和drivers/serial/Makefile两个文件，将serial\_owl.c添加进去。

具体可参考如下patch：

> [https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2](https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2 "https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2")

##### 4.3 配置u-boot，使能DM、使能DM\_SERIAL、使能OWL\_SERIAL

> cd ./x\_project/build
>
> make uboot-config
>
> …

具体可参考如下patch：

> [https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2](https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2 "https://github.com/wowotechX/u-boot/commit/713a4100338554befc573f7b52c5f36b2e763ec2")

##### 4.4 利用serial uclass提供的接口，编写串口驱动

1）在drivers/serial/serial\_owl.c中，调用U\_BOOT\_DRIVER，定义serial driver，如下：

> U\_BOOT\_DRIVER(serial\_owl) = {   
> .name = "serial\_owl",   
> .id = UCLASS\_SERIAL,   
> .probe = owl\_serial\_probe,   
> .ops = &owl\_serial\_ops,   
> .flags = DM\_FLAG\_PRE\_RELOC,   
> };

该driver的name为“serial\_owl”（用于device的bind），id为UCLASS\_SERIAL，DM\_FLAG\_PRE\_RELOC表示在relocation[5]之前可能会使用，其它字段后面会详细介绍。

2）调用U\_BOOT\_DEVICE，静态定义serial device

由于此时device tree没有ready，暂时使用静态定义的方式，如下：

> /\* TODO \*/   
> U\_BOOT\_DEVICE(stm32\_serials) = {   
> .name = "serial\_owl",   
> };

3）实现driver的probe接口

serial driver和serial device绑定的时候，会调用probe函数（owl\_serial\_probe），该函数需要完成串口有关的初始化操作，包括：

> 管脚复用的配置；
>
> 串口控制器的总线时钟、reset等配置；
>
> 串口参数的配置（波特率、停止位、校验位等）；
>
> 串口的使能。
>
> 具体可参考“[https://github.com/wowotechX/u-boot/blob/x\_integration/drivers/serial/serial\_owl.c](https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c "https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c")”

4）实现owl\_serial\_ops

u-boot的driver model，比较依赖class的概念，对serial而言，serial uclass通过struct dm\_serial\_ops 数据结构，将串口有关的通用操作封装在一起，因此串口驱动的开发，从论述题转变为了填空题（填充struct dm\_serial\_ops）。struct dm\_serial\_ops的定义可参考下面文件（u-boot的注释写的很好，点赞！！）：

> [https://github.com/wowotechX/u-boot/blob/x\_integration/include/serial.h](https://github.com/wowotechX/u-boot/blob/x_integration/include/serial.h "https://github.com/wowotechX/u-boot/blob/x_integration/include/serial.h")

对“x project”的使用场景来说，实现putc、pending、getc、setbrg四个回调函数即可，如下：

> static const struct dm\_serial\_ops owl\_serial\_ops = {   
> .putc = owl\_serial\_putc,   
> .pending = owl\_serial\_pending,   
> .getc = owl\_serial\_getc,   
> .setbrg = owl\_serial\_setbrg,   
> };
>
> 具体可参考“[https://github.com/wowotechX/u-boot/blob/x\_integration/drivers/serial/serial\_owl.c](https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c "https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c")”。

5）串口波特率的计算

对串口驱动来说，需要注意波特率的计算，公式如下：

> int divider;
>
> divider = HOSC\_FREQ / (baudrate \* 8);   
> if (divider > 0)   
> divider--;
>
> clrsetbits\_le32(CMU\_UART5CLK, 0x1f, divider);

##### 4.5 编译后，验证是否okay

编译成功后，将bubblegum-96 board通过串口子板，以串口线（或USB转串口），和PC连接后，使用下面命令将u-boot上传到SRAM中执行，在控制台上应该就可以看到u-boot的输出信息了：

> `sudo ../tools/dfu/dfu bubblegum 0xe406b200 out/u-boot/u-boot.bin 1`

#### 5. 总结

本文简单介绍了在u-boot中实现串口驱动的基本方法，由于很多基础子系统的代码没有ready，串口驱动的实现比较简陋，仅仅通过操作寄存器的方式，实现了UART5（或UART2）的代码，尚且不能动态切换。后续随着“[X Project](/forum/)”的进行，我们将继续完善之。

另外，由于资料的欠缺，本文的大部分篇幅，都花在了串口有关的硬件信息的获取上，这在正常的开发过程中是不存在的，因此u-boot下的串口驱动开发，还是比较简单的。

##### 6. 参考文档

[1] S900 IC Spec，<https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/SoC_bubblegum96.pdf>

[2] Bubblegum 96boards硬件手册，<https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/HardwareManual_Bubblegum96_S900_V1.1.pdf>

[3] Bubblegum 96boards原理图，<https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/HardwareDocs/Schematics_Bubblegum96.pdf>

[4] [https://github.com/96boards-bubblegum/u-boot/tree/bubblegum96-2015.07](https://github.com/96boards-bubblegum/u-boot/tree/bubblegum96-2015.07 "https://github.com/96boards-bubblegum/u-boot/tree/bubblegum96-2015.07")

[5] [u-boot启动流程分析(2)\_板级(board)部分](/u-boot/boot_flow_2.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_serial.html)。
