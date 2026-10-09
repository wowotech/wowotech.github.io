---
title: "X-006-UBOOT-pinctrl driver移植(Bubblegum-96平台)"
date: 2016-07-09T21:47:14+08:00
url: "/x_project/bubblegum_uboot_pinctrl.html"
gid: "318"
emlog_type: "blog"
summary: "wowo觉得，在linux kernel新引入的众多子系统中，pinctrl subsystem是一个特别晦涩难懂的子系统，它所解决的问题，和它所引入的困扰，不相上下。在平时工作的过程中，年轻工程师问的最多的，就是在驱动中要怎么使用pinctrl？这样配置pinctrl到底是什么意思？等等。 对一个子系统来说，如果不能让它的使用者（consumer）很容易的理解和掌握，就宣告了它的失败。更不用说让"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["subsystem", "u-boot", "porting", "pinctrl"]
views: 13412
comment_count: 8
aliases:
  - "/x_project/318.html"
  - "/318.html"
---

#### 1. 前言

wowo觉得，在linux kernel新引入的众多子系统中，pinctrl subsystem是一个特别晦涩难懂的子系统，它所解决的问题，和它所引入的困扰，不相上下。在平时工作的过程中，年轻工程师问的最多的，就是在驱动中要怎么使用pinctrl？这样配置pinctrl到底是什么意思？等等。

对一个子系统来说，如果不能让它的使用者（consumer）很容易的理解和掌握，就宣告了它的失败。更不用说让它的提供者（provider）简单、快速地编写驱动程序了。

为什么会这样呢？通俗一点讲，就是“大炮打蚊子”。从技术的角度看，pinctrl是一个非常优秀的子系统，有着复杂而巧妙的封装和抽象，但它所要解决的问题，实际上非常简单、直白。这就造成了一个落差，从而带来了各种理解上的困惑。

正因为此，u-boot在照搬linux kernel pinctrl的同时，额外提供了一种简洁的方法。本文将借助“[X Project](/forum/)” u-boot中pin control driver的移植过程，介绍、分析这种方法，并以此理解pinctrl的本质。

与此同时，我们会基于“[X-005-UBOOT-device tree移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_device_tree.html)”，扩展对device tree的使用，以加深对device tree的理解和掌握。

#### 2. pinctrl要解决的问题

有关pinctrl的基本概念，可参考本站的三篇文章（本文不再赘述了）：

> [linux内核中的GPIO系统之（1）：软件框架](/gpio_subsystem/io-port-control.html)
>
> [linux内核中的GPIO系统之（2）：pin control subsystem](/gpio_subsystem/pin-control-subsystem.html)
>
> [Linux内核中的GPIO系统之（3）：pin controller driver代码分析](/gpio_subsystem/pin-controller-driver.html)

基于上面三篇文章，我们可以总结出如下要点：

> 1）CPU中有些管脚的功能和参数，是可配置的。例如D5和A8两个管脚（名称是随便写的），即可以配置成具有上拉功能的I2C2的SCL/SDA，也可以配置为UART5的RX/TX，又可以配置为两个正常的GPIO，等等。
>
> 2）这些可配置参数的组合，受限于具体CPU的功能，个数是有限的。这一点很重要。
>
> 3）某个产品的硬件设计确定下来之后，这些可配置的功能和参数，基本上都确定了下来了，很少会在运行时修改。例如，连接3G modem的UART2，由于物理连接的限制，它所在对应的管脚，以及这些管脚的参数，都已经固定了。这一点同样很重要。

因此，pinctrl的本质功能，可总结为：

> 产品（或平台）的硬件设计确定后，在某些运行状态下，某些管脚的功能和参数也已经确定。软件需要根据这些确定的信息，在需要的时候（通常是对应的driver初始化的时候），将这些管脚配置成所需的功能和参数（通常是通过寄存器配置）。
>
> 而本着抽象和封装的原则，我们不希望每个驱动工程师，在为各自负责的硬件模块编写驱动的时候，都要研究一下本平台的硬件设计，确定和该硬件模块有关的管脚分配情况（这在复杂的SOC系统中，是一项非常繁琐的事情）。因此希望pinctrl driver，能否将这些繁琐的事情，封装起来，以比较友好的方式，向各个设备驱动提供服务。

听着有点拗口（但我相信大家都理解），下面我以Bubblegum-96平台调试用的UART5（可参考“[X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)”）为例，做进一步的说明：

> 由“[X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)”的描述可知，Bubblegum-96平台中，UART5是一个很明确的功能，它的RX/TX两个信号，分别连接到S900的A7和D8两个管脚上。这两个管脚和GPIOA25、GPIOA27、SENS0\_VSYNC、SENS0\_HSYNC、PWM2等功能复用。
>
> 想要UART5正常工作，就需要把A7和D8两个管脚配置为UART\_RX和UART\_TX功能（通过MFP\_CTL1寄存器的bit28:23）。如果没有pinctrl driver，这个配置的工作，就需要serial driver负责（就像“[X-004-UBOOT-串口驱动移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_serial.html)”中所描述的那样）。但这显然不符合模块化的设计理念，因此需要pinctrl driver代劳。

pinctrl driver要做什么事情呢？

> 它要抽象出来一个UART5功能（function，例如“pinctrl\_serial5”），并允许serial driver使用这个function。具体的配置工作，由pinctrl driver负责，serial driver只需要“拿来主义”即可。具体可参考后面章节的介绍。

#### 3. 设计思路

基于上面的描述，我们将设计一个最简的pinctrl driver，思路如下：

1）基于具体的版型（这里是Bubblegum-96），以该版型所对应的硬件功能为单位，将管脚配置抽象出来。借助device tree描述，有如下的架构：

> /\* arch/arm/dts/s900-bubblegum.dts \*/
>
> #include "s900-bubblegum-pinctrl.dtsi"

“s900-bubblegum.dts”是Bubblegum-96的硬件描述，包含了描述该版型下所有的管脚配置的“s900-bubblegum-pinctrl.dtsi”文件：

> /\* arch/arm/dts/s900-bubblegum-pinctrl.dtsi \*/
>
> #include "s900.dtsi"
>
> / {   
> [pinctrl@e01b0000](mailto:pinctrl@e01b0000) {   
> /\* actions,pins = , ...\*/   
> pinctrl\_serial5: serial5 {   
> actions,pins = <0x0044 23="" 0x3f="" 0xc="">;   
>  };   
> …   
> };   
> };

其中黄色背景所描述的dts节点，就是对应的硬件功能，本例为用于控制台的UART5。

2）每一个硬件功能，所对应的管脚配置，都由一系列的寄存器配置值表示，这些值最终会写入到pinctrl的寄存器中，使对应的硬件功能生效，如上面例子中红色背景的部分，格式说明如下。

> actions,pins = , ...
>
> reg，所要操作的寄存器值，是相对pinctrl寄存器（e01b0000）的一个偏移偏移；
>
> offset，所要配置的value在寄存器中的偏移量（位置）；
>
> mask，所需要配置的value的mask。
>
> value，所要配置的value。
>
> 例如，需要使能S900 SOC A7和D8管脚的UART5功能，需要将0xe01b0044（MFP\_CTL1）的bit28:23配置为0xc，只需如下的配置即可：actions,pins = <0x0044 23="" 0x3f="" 0xc="">;
>
> 当然，如果需要多组寄存器配置，也是okay的，只要：actions,pins = <0x0044 23="" 0x3f="" 0xc="">, <0x00xx xx="" 0xxx="">, …;即可。

3）对应的硬件功能的driver，需要在自己的dts节点中，引用“管脚配置”（pinctrl\_serial5），这样就可以在u-boot启动的时候，由设备模型调用pinctrl的接口，自动将寄存器配置生效。或者，在需要的时候，手动调用pinctrl的接口，将某个pinctrl配置项生效，如下：

> /\* arch/arm/dts/s900-bubblegum.dts \*/
>
> / {
>
> …
>
> serial5: serial@e012a000 {   
> u-boot,dm-pre-reloc;   
> pinctrl-names = "default";   
> pinctrl-0 = <&pinctrl\_serial5>;  
> };   
> };

u-boot的设备模型，配合pinctrl core，会在设备枚举的时候，将设备中pinctrl-name为“default”或者pinctrl句柄为“pinctrl-0”的pinctrl配置项生效。

另外，我们可以指定多个pinctrl功能，并在driver中随意的使能/禁止相应的功能，这里不再详细介绍，需要使用的同学可自行揣摩。

4）基于该设计思路，pinctrl有关的开发任务可总结为：

> a）硬件设计确定后，负责pinctrl driver的工程师，需要将各个硬件功能以及对应的寄存器配置，抽象出来，保存在“xxx-pinctrl.dtsi ”中。
>
> b）其它设备驱动，在需要的时候，引用并使用“xxx-pinctrl.dtsi ”所抽象的功能。

#### 4. 移植过程及说明

##### 4.1 u-boot pinctrl子系统介绍

u-boot的pinctrl子系统和linux kernel的非常类似，因此也比较复杂，这里只列出一些要点（具体细节不再详细介绍）：

> 1）基于PINCTRL uclass。
>
> 2）根据复杂度、代码量、标准fdt的支持等不同，提供全功能（CONFIG\_PINCTRL\_FULL）、通用功能（CONFIG\_PINCTRL\_GENERIC）等不同类型的功能。我们只使用全功能（CONFIG\_PINCTRL\_FULL），并且只使用其中的简单接口（set\_state\_simple）。

##### 4.2 新建一个pinctrl驱动，并添加到u-boot的编译框架中

1）新建s900 soc的pinctrl驱动----pinctrl-owl.c（OWL可能是S900 soc所在的系列的代码，copy自Actions代码，大家不用太纠结）。

> touch drivers/pinctrl/pinctrl-owl.c

2）修改u-boot pinctrl driver的Kconfig和Makefile文件，将该驱动添加进去

> /\* drivers/pinctrl/Kconfig \*/
>
> @@ -141,6 +141,11 @@ config PIC32\_PINCTRL   
> by a device tree node which contains both GPIO defintion and pin control   
> functions.   
>   
> +config OWL\_PINCTRL   
> + bool "Actions pin control driver for OWL soc"   
> + depends on DM   
> + help   
> + Support pin multiplexing control on Actions OWL SoCs.  
>   
> endif   
>   
> source "drivers/pinctrl/nxp/Kconfig"
>
> /\* drivers/pinctrl/Makefile \*/
>
> @@ -11,3 +11,5 @@ obj-$(CONFIG\_PINCTRL\_SANDBOX) += pinctrl-sandbox.o   
> obj-$(CONFIG\_PINCTRL\_UNIPHIER) += uniphier/   
> obj-$(CONFIG\_PIC32\_PINCTRL) += pinctrl\_pic32.o   
> +   
> +obj-$(CONFIG\_OWL\_PINCTRL) += pinctrl-owl.o

##### 4.3 配置u-boot，使能pinctrl有关的配置项

> /\* configs/bubblegum\_defconfig \*/
>
> #   
> # Pin controllers   
> #   
> -# CONFIG\_PINCTRL is not set   
> +CONFIG\_PINCTRL=y   
> +CONFIG\_PINCTRL\_FULL=y   
> +# CONFIG\_PINCTRL\_GENERIC is not set   
> +# CONFIG\_ROCKCHIP\_PINCTRL is not set   
> +# CONFIG\_ROCKCHIP\_3036\_PINCTRL is not set   
> +CONFIG\_OWL\_PINCTRL=y  
> #   
> # Power

其中CONFIG\_PINCTRL为pinctrl总开关。CONFIG\_PINCTRL\_FULL可以提供比较全面的pinctrl功能，暂时不用深究。CONFIG\_OWL\_PINCTRL使我们新加的pinctrl driver。

##### 4.4 添加pinctrl device有关的device tree描述

在这里，我们将DTS文件拆分为三个：

> s900.dtsi，SOC级别的文件，存放该SOC共同的内容，如serial controller、pinctrl controller等通用的配置。
>
> s900-bubblegum-pinctrl.dtsi，Bubblegum-96平台所对应的pinctrl配置，具体可参考第3章的介绍。
>
> s900-bubblegum.dts，Bubblegum-96平台的dts文件，存放该平台特有的内容。

对于pinctrl device来说，需要在s900.dtsi中定义基本的controller信息，如下：

> + pinctrl@e01b0000 {   
> + compatible = "actions,s900-pinctrl";   
> + reg = <0 0="" 0xe01b0000="" 0x1000="">;   
> + };

然后在s900-bubblegum-pinctrl.dtsi中定义所有的pinctrl功能，以及相应的寄存器配置信息，如下：

> + pinctrl@e01b0000 {   
> + /\* actions,pins = , ...\*/   
> + pinctrl\_serial5: serial5 {   
> + actions,pins = <0x0044 23="" 0x3f="" 0xc="">;   
> + };   
> …   
> + };

最后，在中定义版型特有的配置：

> + pinctrl@e01b0000 {   
> + u-boot,dm-pre-reloc;   
> + };

##### 4.5 编写pinctrl driver

要点包括（具体可参考“[https://github.com/wowotechX/u-boot/blob/7340ec6450f5cfa8076dac59811ef2e459dc92b4/drivers/pinctrl/pinctrl-owl.c](https://github.com/wowotechX/u-boot/blob/7340ec6450f5cfa8076dac59811ef2e459dc92b4/drivers/pinctrl/pinctrl-owl.c "https://github.com/wowotechX/u-boot/blob/7340ec6450f5cfa8076dac59811ef2e459dc92b4/drivers/pinctrl/pinctrl-owl.c")”）：

1）基于pinctrl uclass，注册owl\_pinctrl driver，并结合dts文件，添加对应的of\_match table

> static const struct udevice\_id owl\_pinctrl\_match[] = {   
> { .compatible = "actions,s900-pinctrl" },   
> { /\* sentinel \*/ }   
> };
>
> U\_BOOT\_DRIVER(owl\_pinctrl) = {   
> .name = "owl\_pinctrl",   
> .id = UCLASS\_PINCTRL,   
> .of\_match = owl\_pinctrl\_match,   
> .probe = owl\_pinctrl\_probe,   
> .ops = &owl\_pinctrl\_ops,   
> .flags = DM\_FLAG\_PRE\_RELOC,   
> .priv\_auto\_alloc\_size = sizeof(struct owl\_pinctrl\_priv),   
> };

2）提供probe（owl\_pinctrl\_probe）接口，以便获取pinctrl device的寄存器基地址，并保存在priv\_auto\_alloc\_size 中（struct owl\_pinctrl\_priv）。

3）pinctrl uclass要求实现对应的struct pinctrl\_ops结构，我们只实现其中最简单的一个----set\_state\_simple：

> static const struct pinctrl\_ops owl\_pinctrl\_ops = {   
> .set\_state\_simple = owl\_pinctrl\_set\_state\_simple,   
> };

4）set\_state\_simple的原型如下：

> static int owl\_pinctrl\_set\_state\_simple(struct udevice \*dev,   
> struct udevice \*periph)

其中dev代表pinctrl device，periph代表引用了相应pinctrl功能的device（如本文中的serial device）。我们需要

在这个接口中，通过“pinctrl-0”关键字，找到该设备所引用的所有pinctrl节点的句柄，并以此获得对应的寄存器配置信息（通过"actions,pins"关键字），然后将配置信息写入到具体的寄存器即可，如下：

> {   
> int entry, count, i;   
> uint32\_t cell[20];   
> struct owl\_pinctrl\_priv \*priv = dev\_get\_priv(dev);
>
> entry = fdtdec\_lookup\_phandle(gd->fdt\_blob, periph->of\_offset,   
> "pinctrl-0");   
> if (entry < 0)   
> return -1;
>
> count = fdtdec\_get\_int\_array\_count(gd->fdt\_blob, entry, "actions,pins",   
> cell, ARRAY\_SIZE(cell));   
> if (count < 4)   
> return -1;
>
> for (i = 0; i < count / 4; i += 4)   
> clrsetbits\_le32(priv->base + cell[i],   
> cell[i + 2] << cell[i + 1],   
> cell[i + 3] << cell[i + 1]);
>
> return 0;   
> }

注1：当前的实现，只处理了pinctrl-0中第一个字段，后续可以增加多个字段的处理。

#### 5. pinctrl的生效过程

正常情况下（如第4章中serial driver的例子），设备驱动在dts文件中引用对应的pinctrl配置后，设备模型会在设备枚举的时候，自动调用pinctrl提供的接口，将配置生效，具体过程可参考如下的流程（比较简单，因此不再详细分析，感兴趣的同学可以自己阅读源代码）：

> serial\_init—>serial\_find\_console\_or\_panic([drivers/serial/serial-uclass.c](https://github.com/wowotechX/u-boot/blob/ee8b25fa354da7cfaafe0e6781e873c74c29bbad/drivers/serial/serial-uclass.c))   
> device\_probe([drivers/core/device.c](https://github.com/wowotechX/u-boot/blob/ee8b25fa354da7cfaafe0e6781e873c74c29bbad/drivers/core/device.c))   
> pinctrl\_select\_state(dev, "default")   
> pinctrl\_select\_state\_full—>pinctrl\_select\_state\_simple([drivers/pinctrl/pinctrl-uclass.c](https://github.com/wowotechX/u-boot/blob/ee8b25fa354da7cfaafe0e6781e873c74c29bbad/drivers/pinctrl/pinctrl-uclass.c))   
> ops->set\_state\_simple(pctldev, dev);([drivers/pinctrl/pinctrl-owl.c](https://github.com/wowotechX/u-boot/blob/x_integration/drivers/pinctrl/pinctrl-owl.c))

#### 6. 总结

本文通过一个简单的实例，介绍了在u-boot中实现一个简单的pinctrl driver的步骤，以加深对pinctrl subsystem理解。与此同时，通过引入更多的device tree操作（例如分离出不同的DTS文件、通过DTS解析pinctrl配置信息等），也进一步加深了我们对device tree的理解。

最后，本文涉及到的示例代码，可以从如下链接获取：

> [https://github.com/wowotechX/u-boot/commit/7340ec6450f5cfa8076dac59811ef2e459dc92b4](https://github.com/wowotechX/u-boot/commit/7340ec6450f5cfa8076dac59811ef2e459dc92b4 "https://github.com/wowotechX/u-boot/commit/7340ec6450f5cfa8076dac59811ef2e459dc92b4")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/bubblegum_uboot_pinctrl.html)。
