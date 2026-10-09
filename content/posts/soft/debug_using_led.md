---
title: "通过点亮LED的方法调试嵌入式代码"
date: 2016-06-12T22:10:43+08:00
url: "/soft/debug_using_led.html"
gid: "308"
emlog_type: "blog"
summary: "在软件开发的过程中，debug（调试）是一个很重要的事情，因为没有百分之百正确的代码，一旦结果不符合预期，我们需要知道问题出在哪里了。 在PC环境下开发应用程序，我们不需要太操心，因为有各式各样的模拟器、调试器可供使用，我们可以追踪到每一行代码的执行过程和执行结果，找出问题只是时间问题而已。但在嵌入式环境下，就有些麻烦了，能用的手段，无外乎两种： 1）使用硬件仿真器定位问题。 2）使用日志输出定位"
author: "wowo"
category: "软件开发"
category_alias: "soft"
tags: ["debug", "LED"]
views: 13609
comment_count: 6
aliases:
  - "/soft/308.html"
  - "/308.html"
---

#### 1. 前言

在软件开发的过程中，debug（调试）是一个很重要的事情，因为没有百分之百正确的代码，一旦结果不符合预期，我们需要知道问题出在哪里了。

在PC环境下开发应用程序，我们不需要太操心，因为有各式各样的模拟器、调试器可供使用，我们可以追踪到每一行代码的执行过程和执行结果，找出问题只是时间问题而已。但在嵌入式环境下，就有些麻烦了，能用的手段，无外乎两种：

> 1）使用硬件仿真器定位问题。
>
> 2）使用日志输出定位问题。

对嵌入式工程师（特别是linux工程师）而言，鉴于使用硬件仿真器的诸多不便（成本高，无法保证人手一个；硬件连接复杂，需要预留特定接口；使用不方便；等等），日志输出几乎成为必备且唯一的debug手段。但是，总会有例外：

> 系统刚刚启动，在日志输出的通道（通常是UART接口）ready之前，怎么debug？

在不得不使用仿真器之前，我们还有一个简单的方法，就是点LED灯，本文将结合“[X Project](/forum/)”“[【任务2】启动到u-boot command line](/forum/28.html)”实现的过程，对这个方法进行简单的介绍和总结。

#### 2. 思路

从本质上讲，软件debug最高效的手段，是良好的设计、优秀的编码、细致的代码检查，当然，百密总有一疏。但大多数时候，我们只要能找到出现问题的大概位置，再辅以代码的检查，就可以百分之九十九的解决问题，这也是通过日志输出的方法定位问题的基本逻辑。

因此，在日志输出通道ready之前，我们也可以使用同样的思路，借助LED灯，实现问题的定位。大致思路如下：

1）如果系统只有一个LED灯，可以在代码中，正确执行某一个步骤之后，点亮LED，以此类推，一步一步检查代码执行的正确与否（其实“[X Project](/forum/)”“[【任务1】启动过程-Boot from USB](/forum/15.html)”就是借用了这个思路）。

2）当然，如果系统有多个LED，例如四个，我们可以将这四个LED编码成一个4bit的数字（0~15），这样就可以表示更多的状态，下面是“[X Project](/forum/)”基于bubblegum-96平台，实现的一个简单的接口（代码逻辑很简单，我就不解释了）：

> /\* [https://github.com/wowotechX/u-boot/blob/x\_integration/board/actions/bubblegum/board.c](https://github.com/wowotechX/u-boot/blob/x_integration/board/actions/bubblegum/board.c "https://github.com/wowotechX/u-boot/blob/x_integration/board/actions/bubblegum/board.c") \*/
>
> ```
> /*
>  * A simple debug function for early debug, in which,
>  * we use four LEDs to display sixteen debug codes, from 0 to 15.
>  * Using it, we can know, at least roughly, at where out code is run.
>  */
> void bubblegum_early_debug(int debug_code)
> {
> 	uint8_t val;
>
> 	val = debug_code & 0x1;
> 	setbits_le32(GPIOA_OUTEN, 1 << DEBUG_LED0_GPIO);
> 	clrsetbits_le32(GPIOA_OUTDAT, 1 << DEBUG_LED0_GPIO,
> 			val << DEBUG_LED0_GPIO);
>
> 	val = (debug_code >> 1) & 0x1;
> 	setbits_le32(GPIOA_OUTEN, 1 << DEBUG_LED1_GPIO);
> 	clrsetbits_le32(GPIOA_OUTDAT, 1 << DEBUG_LED1_GPIO,
> 			val << DEBUG_LED1_GPIO);
>
> 	val = (debug_code >> 2) & 0x1;
> 	setbits_le32(GPIOF_OUTEN, 1 << DEBUG_LED2_GPIO);
> 	clrsetbits_le32(GPIOF_OUTDAT, 1 << DEBUG_LED2_GPIO,
> 			val << DEBUG_LED2_GPIO);
>
> 	val = (debug_code >> 3) & 0x1;
> 	setbits_le32(GPIOF_OUTEN, 1 << DEBUG_LED3_GPIO);
> 	clrsetbits_le32(GPIOF_OUTDAT, 1 << DEBUG_LED3_GPIO,
> 			val << DEBUG_LED3_GPIO);
> }
> ```

#### 3. 一个例子

利用上面的debug接口，在调试串口驱动的时候，发挥了很大的作用，如下：

> /\* [https://github.com/wowotechX/u-boot/blob/x\_integration/drivers/serial/serial\_owl.c](https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c "https://github.com/wowotechX/u-boot/blob/x_integration/drivers/serial/serial_owl.c") \*/
>
> ```
> extern void bubblegum_early_debug(int debug_code);
> static int owl_serial_probe(struct udevice *dev)
> {
> 	/* only for UART2, TODO */
> 	bubblegum_early_debug(4);
>
> 	/* pinmux */
> 	setbits_le32(MFP_CTL2, 1 << 22);
>
> 	bubblegum_early_debug(5);
>
> 	/* device clock enable */
> 	setbits_le32(CMU_DEVCLKEN1, 1 << 8);
>
> 	bubblegum_early_debug(6);
>
> 	/* reset de-assert */
> 	setbits_le32(CMU_DEVRST1, 1 << 7);
>
> 	bubblegum_early_debug(7);
>
> 	/* set default baudrate and enable UART */
> 	owl_serial_setbrg(dev, 115200);
> 	
> 	/* enable uart */
> 	setbits_le32(UART2_BASE + UART_CTL, UART_CTL_EN);
>
> 	bubblegum_early_debug(8);
> 	return 0;
> }
> ```

串口驱动编写好之后，发现系统会死在owl\_serial\_probe中，于是添加了一系列的"点灯"操作，发现最后停留在“bubblegum\_early\_debug(5); ”上面（LED2和LED0亮），于是就可以确定这条语句出了问题：

> setbits\_le32(CMU\_DEVCLKEN1, 1 << 8);

经过仔细检查，发现CMU\_DEVCLKEN1寄存器定义错了（可能是抄Action的代码笔误了）。

#### 4. 总结

步骤很简单，之所以要写一篇文章，是想告诉大家，嵌入式开发其实挺简单的，只要有足够的细心和耐心，一切皆有可能。

原创文章，转发请注明出处。蜗窝科技，[/](/soft/debug_using_led.html)
