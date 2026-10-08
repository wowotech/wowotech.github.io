---
title: "X-026-KERNEL-Linux gpio driver的移植之gpio range"
date: 2017-09-27T22:27:43+08:00
url: "/x_project/kernel_gpio_driver_porting_2.html"
gid: "412"
emlog_type: "blog"
summary: "\r\n\t我们在[1][2]中提到过，鉴于gpio的特殊性，pinctrl subsystem特意留了一个后门（gpio range），gpio driver可以通过这个后门直接向pinctrl subsystem申请将某个pin用作gpio功能。本文将根据一个简单的示例，介绍这个后门的使用方法，以加深对相关机制的理解。\r\n\r\n\r\n\t注1：本文的测试方法和[3]中的一致，即：通过gpiolib sys"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["driver", "GPIO", "porting", "pinctrl", "range"]
views: 21447
comment_count: 1
aliases:
  - "/x_project/412.html"
  - "/412.html"
---

## 1. 前言

我们在[1][2]中提到过，鉴于gpio的特殊性，pinctrl subsystem特意留了一个后门（gpio range），gpio driver可以通过这个后门直接向pinctrl subsystem申请将某个pin用作gpio功能。本文将根据一个简单的示例，介绍这个后门的使用方法，以加深对相关机制的理解。

注1：本文的测试方法和[3]中的一致，即：通过gpiolib sysfs api控制LED0（GPIOA19）的亮灭，因而不再罗列详细步骤。

## 2. 移植步骤

由[2]可知，gpio range的主要目的就是将gpio命名空间（gpio）转换为pinctrl命名空间（pin），并由pinctrl subsystem访问硬件实现gpio有关的功能控制。因此gpio range的移植步骤注要包括：

#### 2.1 pinctrl命名空间和gpio命名空间的定义

参考”[X-025-KERNEL-Linux gpio driver的移植之基本功能](/x_project/kernel_gpio_driver_porting_1.html)[3]”中有关gpiochip的实现，本例中的GPIOA19的gpio命名空间为：

> gpiochip：gpioa   
> 编号：19

同理，按照“[X-023-KERNEL-Linux pinctrl driver的移植](/x_project/kernel_pinctrl_driver_porting.html)[4]”中的方法，结合bubblegum-96的原理图，我们可以把GPIOA19所在的管脚编号为"F3"，它对应的pinctrl命名空间为：

> pin controller：pinctrl@0xe01b0000   
> 编号：52
>
> @@ -68,6 +68,7 @@ static const struct pinctrl\_pin\_desc s900\_pins[] = {   
> PINCTRL\_PIN(15, "B6"),   
> PINCTRL\_PIN(24, "C5"),   
> PINCTRL\_PIN(37, "D8"),   
> + PINCTRL\_PIN(52, "F3"),  
> PINCTRL\_PIN(60, "G1"),   
> PINCTRL\_PIN(61, "G2"),   
> };

#### 2.2 将gpio number转换为pin number

命名空间定义完成后，可以按照[2]中的步骤，在dts中定义一个gpio range，将gpio number转换为pin number，如下：

> @@ -39,7 +39,7 @@   
> clock-frequency = <24000000>;   
> };
>
> - pinctrl@0xe01b0000 {   
> + pinctrl1: pinctrl@0xe01b0000 {   
> compatible = "actions,s900-pinctrl";   
> reg = <0 0="" 0xe01b0000="" 0x550="">;
>
> @@ -56,6 +56,7 @@   
> gpioa: gpio@0xe01b0000 {   
> compatible = "actions,s900-gpio";   
> reg = <0 0="" 12="" 0xe01b0000="">;   
> base = <0>;   
> + gpio-ranges = <&pinctrl1 19 52 1>;  
> };

其中黄色背景那一行的含义是：将gpioa中的19号gpio，和pinctrl1中的52号pin，对应。

#### 2.3 修改gpio driver和pinctrl driver，二者配合，完成gpio的request、free、direction\_input以及direction\_output等操作

1）修改pinctrl driver，实现pinmux\_ops中gpio\_request\_enable、gpio\_disable\_free、gpio\_set\_direction等回调函数

这三个API的输入参数都是range指针和offset（如下所示），通过它们可以找到这个GPIO所在的gpiochip、GPIO bank、GPIO number、对应pin所在的pin controller、pin number等信息。基于这些信息，可以获得相应的硬件信息（寄存器、bit偏移等）。

> int (\*gpio\_request\_enable) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset);   
> void (\*gpio\_disable\_free) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset);   
> int (\*gpio\_set\_direction) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset,   
> bool input);

2）修改gpio chip的.request、.free、.direction\_input、.direction\_output等回调函数，让它们调用pinctrl subsystem提供的相关API，如下：

> int pinctrl\_request\_gpio(unsigned gpio) ;   
> void pinctrl\_free\_gpio(unsigned gpio) ;   
> int pinctrl\_gpio\_direction\_input(unsigned gpio);   
> int pinctrl\_gpio\_direction\_output(unsigned gpio);

注2：有些硬件平台，在完成上面步骤1）的时候，可能会遇到一些困扰，例如怎么根据gpio和pin的信息，找到对应的硬件控制信息（寄存器、bit偏移等），这时我们可以灵活处理。例如在本文例子所使用的bubblegum-96平台上，gpio的pinmux功能并没有单独的寄存器控制，而是通过gpio的in或者out功能的使能，覆盖其它的pinmux功能。此时我们可以把硬件配置的操作交给gpio driver，而pinctrl driver只处理管脚的互斥。具体可参考下面patch的改动。

patch：[https://github.com/wowotechX/linux/commit/cf4d492855d0619772876bc8494b7e180c6a4232](https://github.com/wowotechX/linux/commit/cf4d492855d0619772876bc8494b7e180c6a4232 "https://github.com/wowotechX/linux/commit/cf4d492855d0619772876bc8494b7e180c6a4232")

## 3. 测试步骤

请参考[3]中的测试。测试结果如下（看到s900\_gpio\_request\_enable中的打印，就说明我们的移植成功了）：

> / # mkdir /sys   
> / # mount -t sysfs /sys /sys
>
> / # echo 19 > /sys/class/gpio/export   
> [ 55.136218] owl\_pinctrl e01b0000.pinctrl: s900\_gpio\_request\_enable, range(19/52/1), offset 52
>
> / # echo out > /sys/class/gpio/gpio19/direction   
> [ 86.886343] owl\_gpio e01b0000.gpio: offset 19, value 0   
>   
> / # echo 1 > /sys/class/gpio/gpio19/value   
> [ 100.223812] owl\_gpio e01b0000.gpio: offset 19, value 1   
>   
> / # echo 0 > /sys/class/gpio/gpio19/value   
> [ 120.467468] owl\_gpio e01b0000.gpio: offset 19, value 0

## 4. 参考文档

[1] [linux内核中的GPIO系统之（4）：pinctrl驱动的理解和总结](/gpio_subsystem/pinctrl-driver-summary.html)

[2] [linux内核中的GPIO系统之（5）：gpio subsysem和pinctrl subsystem之间的耦合](/gpio_subsystem/pinctrl-and-gpio.html)

[3] [X-025-KERNEL-Linux gpio driver的移植之基本功能](/x_project/kernel_gpio_driver_porting_1.html)

[4] [X-023-KERNEL-Linux pinctrl driver的移植](/x_project/kernel_pinctrl_driver_porting.html)

[5] Schematics\_Bubblegum96.pdf

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/kernel_gpio_driver_porting_2.html)。
