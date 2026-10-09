---
title: "X-014-KERNEL-ARM GIC driver的移植"
date: 2016-10-31T22:23:41+08:00
url: "/x_project/gic_driver_porting.html"
gid: "347"
emlog_type: "blog"
summary: "“ X Project ”完成“ X-012-KERNEL-serial early console的移植 ”之后，终止在如下的kernel panic中： NR_IRQS:64 nr_irqs:64 0 Kernel panic - not syncing: No interrupt controller found. ---[ end Kernel panic - not syncing: N"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["Linux", "Kernel", "内核", "driver", "porting", "移植"]
views: 9770
comment_count: 1
aliases:
  - "/x_project/347.html"
  - "/347.html"
---

## 1. 前言

“[X Project](/sort/x_project)”完成“[X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)”之后，终止在如下的kernel panic中：

> NR\_IRQS:64 nr\_irqs:64 0   
> Kernel panic - not syncing: No interrupt controller found.   
> ---[ end Kernel panic - not syncing: No interrupt controller found.

结果很明显，系统中没有注册中断控制器。因此，本文将以“Bubbugum-96”平台为例，介绍ARM GIC驱动的移植步骤，顺便继续加深对device tree的理解和认识。

注1：由于“Bubbugum-96”的GIC符合ARM标准，Linux kernel中相关的驱动是现成的，因此GIC驱动的移植就非常简单了，只要配置一下device tree即可。

## 2. GIC硬件说明

由[1]中的关键字可知，bubblegum-96所使用的SOC（S900）符合GIC\_400规范。根据[3]中GIC driver的分析可知，配置GIC驱动需要知道如下的信息：

> Distributor address range   
> CPU interface address range   
> Virtual interface control block   
> Virtual CPU interfaces

不过S900的公开资料却没有这方面的信息，没关系，我们可以从它们开放出来的源代码反推，如下[4]：

> gic: interrupt-controller@e00f1000 {   
> compatible = "arm,cortex-a15-gic", "arm,cortex-a9-gic";   
> #interrupt-cells = <3>;   
> #address-cells = <0>;   
> interrupt-controller;   
> reg = <0 0="" 0xe00f1000="" 0x1000="">,   
> <0 0="" 0xe00f2000="" 0x1000="">,   
> <0 0="" 0xe00f4000="" 0x2000="">,   
> <0 0="" 0xe00f6000="" 0x2000="">;   
> interrupts = ;   
> };

即：

> Distributor address range：0xe00f1000 ~ 0xe00f1000 + 0x1000   
> CPU interface address range：0xe00f2000 ~ 0xe00f1000 + 0x1000   
> Virtual interface control block：0xe00f4000 ~ 0xe00f4000 + 0x2000   
> Virtual CPU interfaces：0xe00f6000 ~ 0xe00f6000 + 0x2000

## 3. GIC driver移植

移植过程很简单，修改dts文件，加入gic的节点即可（可以抄上面的~~）：

> diff --git a/arch/arm64/boot/dts/actions/s900-bubblegum.dts b/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> index fb1351a..a3af064 100644   
> --- a/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> +++ b/arch/arm64/boot/dts/actions/s900-bubblegum.dts   
> @@ -10,4 +10,16 @@   
> / {   
> model = "Bubblegum-96 Development Board";   
> compatible = "actions,s900-bubblegum", "actions,s900";   
> +   
> + #address-cells = <2>;   
> + #size-cells = <2>;  
> +   
> + gic: interrupt-controller@e00f1000 {   
> + compatible = "arm,gic-400";   
> + #interrupt-cells = <3>;   
> + #address-cells = <0>;   
> + interrupt-controller;   
> + reg = <0 0="" 0xe00f1000="" 0x1000="">, /\* dist\_base \*/   
> + <0 0="" 0xe00f2000="" 0x1000="">; /\* cpu\_base \*/  
> + };   
> };

简单说明如下：

1）#address-cells和#size-cells

目前为止，我们的dts文件已经裸奔了很久了（因为没有任何的节点），不过现在就不行了。因为有了第一个节点[----interrupt-controller@e00f1000](mailto:----interrupt-controller@e00f1000)，该节点下面有“reg”关键字需要解析，解析的依据是什么呢？也就是说：

> reg关键字中，地址信息有多长？size信息又有多长呢？

这两个信息需要由#address-cells和#size-cells告诉kernel，这里都设置为2，含义是：

> address信息占用两个word的长度，即“0 0xe00f1000”组合成0x00000000e00f1000(Distributor address)，“0 0x1000”组合成0x0000000000001000（Distributor length）。

2）compatible名称为“arm,gic-400”，具体可参考“drivers/irqchip/irq-gic.c”中有关的定义。

3）interrupt-controller用于指示该节点是一个中断控制器。

4）#interrupt-cells用于指明该中断控制器怎么编码某一个中断源，这里的3是ARM GIC driver定义的，意义如下：

> 例如：interrupts = ;
>
> 第一个cell用于指示中断的类型，0是SPI，1是PPI；
>
> 第二个cell用于指示中断号；
>
> 第三个cell用于指示中断的flag，包括： bits[3:0]指示中断的触发类型，1 edge triggered、4 level triggered。

5）reg字段我没有写完全，剩下的后续真正用的时候再说了。

## 4. 编译验证

根据“[X Project](/sort/x_project)”的开发指南，编译并运行新的kernel：

> make kernel uImage
>
> make spl-run
>
> make kernel-run

出现如下的打印：

> clocksource\_probe: no matching clocksources found   
> Kernel panic - not syncing: Unable to initialise architected timer.
>
> ---[ end Kernel panic - not syncing: Unable to initialise architected timer.

panic的对象换了，看来GIC成功了，简单吧？

## 5. GIC的debug和使用

虽然编译、运行通过了，但能否正确使用呢？我们需要一个测试对象，因此，留到下一篇Generic Timer的移植里面，一起介绍吧。

## 6. 参考文档

[1] [bubblegum-96/SoC\_bubblegum96.pdf](https://github.com/96boards/documentation/blob/master/ConsumerEdition/Bubblegum-96/AdditionalDocs/SoC_bubblegum96.pdf)

[2] [bubblegum-96/HardwareManual\_Bubblegum96.pdf](https://github.com/uCRDev/documentation/blob/master/ConsumerEdition/Bubblegum-96/AdditionalDocs/HardwareManual_Bubblegum96_S900_V1.1.pdf)

[3] [/irq_subsystem/gic_driver.html](/irq_subsystem/gic_driver.html)

[4] [https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi](https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi "https://github.com/96boards-bubblegum/linux/blob/bubblegum96-3.10/arch/arm64/boot/dts/s900.dtsi")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/gic_driver_porting.html)。
